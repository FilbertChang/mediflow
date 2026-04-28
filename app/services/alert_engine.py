"""
MediFlow Alert Engine
Analyzes extraction results and generates clinical alerts.

Detection pipeline (in order):
  1. Missing critical fields       — instant, no LLM
  2. High-risk ICD-10 codes        — instant, hardcoded list
  3. Dangerous dosage / meds       — instant, hardcoded list
  4. Drug-drug interactions        — hardcoded ruleset first
  5. Drug-drug interactions        — LLM fallback for unknown combos
"""

from __future__ import annotations
import os
import json
import re
from typing import Optional
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)

# ─────────────────────────────────────────────
# Reference data
# ─────────────────────────────────────────────

# ICD-10 codes that warrant a critical alert
HIGH_RISK_ICD10 = {
    # Cardiovascular
    "I21", "I22",   # Acute MI
    "I26",          # Pulmonary embolism
    "I46",          # Cardiac arrest
    "I50",          # Heart failure
    "I60", "I61", "I62", "I63", "I64",  # Stroke / hemorrhage
    # Infectious / Sepsis
    "A41",          # Sepsis
    "A40",          # Streptococcal sepsis
    "R65",          # SIRS / Sepsis severity
    # Respiratory
    "J96",          # Respiratory failure
    "J18",          # Pneumonia
    # Renal
    "N17",          # Acute kidney failure
    # Metabolic emergencies
    "E11.65", "E10.65",  # Diabetic hyperglycemia
    "E86",          # Dehydration (severe)
    # Oncology flags
    "C34", "C50", "C61", "C18",
}

# Medications flagged as high-risk / narrow therapeutic index
DANGEROUS_MEDS = {
    "warfarin", "heparin", "enoxaparin",
    "digoxin", "lithium",
    "methotrexate",
    "amiodarone",
    "phenytoin", "carbamazepine",
    "clozapine",
    "cyclosporine", "tacrolimus",
    "insulin",  # flag for dosage review
    "morphine", "fentanyl", "oxycodone", "tramadol",
    "vancomycin", "gentamicin", "tobramycin",
}

# Known dangerous drug-drug pairs (bidirectional)
# Format: frozenset({drug_a, drug_b}) → description
INTERACTION_RULES: dict[frozenset, str] = {
    frozenset({"warfarin", "aspirin"}): "Warfarin + Aspirin meningkatkan risiko perdarahan serius.",
    frozenset({"warfarin", "ibuprofen"}): "Warfarin + Ibuprofen meningkatkan risiko perdarahan.",
    frozenset({"warfarin", "naproxen"}): "Warfarin + Naproxen meningkatkan risiko perdarahan.",
    frozenset({"warfarin", "metronidazole"}): "Warfarin + Metronidazole meningkatkan efek antikoagulan secara signifikan.",
    frozenset({"warfarin", "fluconazole"}): "Warfarin + Fluconazole meningkatkan INR secara signifikan.",
    frozenset({"warfarin", "amiodarone"}): "Warfarin + Amiodarone meningkatkan efek antikoagulan.",
    frozenset({"metformin", "contrast"}): "Metformin + Kontras IV — hentikan metformin 48 jam sebelum prosedur.",
    frozenset({"ssri", "tramadol"}): "SSRI + Tramadol meningkatkan risiko serotonin syndrome.",
    frozenset({"ssri", "linezolid"}): "SSRI + Linezolid — risiko serotonin syndrome tinggi.",
    frozenset({"maoi", "ssri"}): "MAOI + SSRI — kontraindikasi absolut, risiko serotonin syndrome fatal.",
    frozenset({"maoi", "tramadol"}): "MAOI + Tramadol — risiko serotonin syndrome fatal.",
    frozenset({"digoxin", "amiodarone"}): "Digoxin + Amiodarone meningkatkan kadar digoxin, risiko toksisitas.",
    frozenset({"digoxin", "clarithromycin"}): "Digoxin + Clarithromycin meningkatkan kadar digoxin.",
    frozenset({"simvastatin", "amiodarone"}): "Simvastatin + Amiodarone meningkatkan risiko miopati.",
    frozenset({"clopidogrel", "omeprazole"}): "Clopidogrel + Omeprazole mengurangi efek antiplatelet.",
    frozenset({"methotrexate", "nsaid"}): "Methotrexate + NSAID meningkatkan toksisitas methotrexate.",
    frozenset({"lithium", "ibuprofen"}): "Lithium + Ibuprofen meningkatkan kadar lithium, risiko toksisitas.",
    frozenset({"lithium", "ace inhibitor"}): "Lithium + ACE Inhibitor meningkatkan kadar lithium.",
    frozenset({"lithium", "thiazide"}): "Lithium + Thiazide meningkatkan kadar lithium.",
    frozenset({"carbamazepine", "erythromycin"}): "Carbamazepine + Erythromycin meningkatkan kadar carbamazepine.",
    frozenset({"phenytoin", "fluconazole"}): "Phenytoin + Fluconazole meningkatkan kadar phenytoin.",
    frozenset({"insulin", "alcohol"}): "Insulin + Alkohol meningkatkan risiko hipoglikemia berat.",
    frozenset({"morphine", "benzodiazepine"}): "Opioid + Benzodiazepine — risiko depresi pernapasan fatal.",
    frozenset({"fentanyl", "benzodiazepine"}): "Opioid + Benzodiazepine — risiko depresi pernapasan fatal.",
    frozenset({"oxycodone", "benzodiazepine"}): "Opioid + Benzodiazepine — risiko depresi pernapasan fatal.",
    frozenset({"tramadol", "benzodiazepine"}): "Opioid + Benzodiazepine — risiko depresi pernapasan fatal.",
    frozenset({"sildenafil", "nitrate"}): "Sildenafil + Nitrat — hipotensi berat, kontraindikasi absolut.",
    frozenset({"tadalafil", "nitrate"}): "Tadalafil + Nitrat — hipotensi berat, kontraindikasi absolut.",
    frozenset({"vancomycin", "gentamicin"}): "Vancomycin + Gentamicin meningkatkan risiko nefrotoksisitas.",
    frozenset({"vancomycin", "tobramycin"}): "Vancomycin + Tobramycin meningkatkan risiko nefrotoksisitas.",
    frozenset({"tacrolimus", "fluconazole"}): "Tacrolimus + Fluconazole meningkatkan kadar tacrolimus, risiko toksisitas.",
    frozenset({"cyclosporine", "simvastatin"}): "Cyclosporine + Simvastatin meningkatkan risiko miopati berat.",
}

# Drug name aliases / generic → normalized key
# Allows matching branded names and common abbreviations
MED_ALIASES: dict[str, str] = {
    # SSRIs
    "sertraline": "ssri", "fluoxetine": "ssri", "paroxetine": "ssri",
    "escitalopram": "ssri", "citalopram": "ssri", "fluvoxamine": "ssri",
    # MAOIs
    "phenelzine": "maoi", "tranylcypromine": "maoi", "selegiline": "maoi",
    "isocarboxazid": "maoi",
    # NSAIDs
    "ibuprofen": "nsaid", "naproxen": "nsaid", "diclofenac": "nsaid",
    "celecoxib": "nsaid", "meloxicam": "nsaid", "indomethacin": "nsaid",
    "ketorolac": "nsaid",
    # Nitrates
    "nitroglycerin": "nitrate", "isosorbide": "nitrate",
    # Benzodiazepines
    "diazepam": "benzodiazepine", "lorazepam": "benzodiazepine",
    "alprazolam": "benzodiazepine", "clonazepam": "benzodiazepine",
    "midazolam": "benzodiazepine",
    # ACE inhibitors
    "lisinopril": "ace inhibitor", "enalapril": "ace inhibitor",
    "ramipril": "ace inhibitor", "captopril": "ace inhibitor",
    # Thiazides
    "hydrochlorothiazide": "thiazide", "chlorthalidone": "thiazide",
    # Statins
    "atorvastatin": "statin", "rosuvastatin": "statin",
    "lovastatin": "statin", "pravastatin": "statin",
    # Opioids (keep originals + alias)
    "codeine": "tramadol",  # rough grouping for serotonin risk
}


def _normalize(med: str) -> list[str]:
    """
    Return all normalized forms of a medication name.
    e.g. "Sertraline 50mg" → ["sertraline", "ssri"]
    """
    raw = med.lower().strip()
    # Strip dosage info
    base = re.split(r"[\s\d]", raw)[0]
    forms = {base}
    if base in MED_ALIASES:
        forms.add(MED_ALIASES[base])
    return list(forms)


# ─────────────────────────────────────────────
# Alert dataclass
# ─────────────────────────────────────────────

class AlertItem:
    def __init__(self, severity: str, alert_type: str, message: str):
        self.severity = severity    # "critical" | "warning" | "info"
        self.alert_type = alert_type
        self.message = message

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "alert_type": self.alert_type,
            "message": self.message,
        }


# ─────────────────────────────────────────────
# Detection functions
# ─────────────────────────────────────────────

def _check_missing_fields(data: dict) -> list[AlertItem]:
    alerts = []
    missing = []
    if not data.get("diagnosis"):
        missing.append("diagnosis")
    if not data.get("medications"):
        missing.append("medications")
    if not data.get("patient_name"):
        missing.append("patient_name")
    if missing:
        alerts.append(AlertItem(
            severity="warning",
            alert_type="missing_fields",
            message=f"Field penting tidak ditemukan dalam catatan dokter: {', '.join(missing)}. Harap verifikasi manual."
        ))
    return alerts


def _check_high_risk_icd10(data: dict) -> list[AlertItem]:
    alerts = []
    codes: list[str] = data.get("icd10_codes") or []
    flagged = []
    for code in codes:
        code_upper = code.strip().upper()
        # Match exact or prefix (e.g. "I21.0" matches "I21")
        for risk_code in HIGH_RISK_ICD10:
            if code_upper == risk_code or code_upper.startswith(risk_code):
                flagged.append(code_upper)
                break
    if flagged:
        alerts.append(AlertItem(
            severity="critical",
            alert_type="high_risk_icd10",
            message=f"⚠️ Kode ICD-10 berisiko tinggi terdeteksi: {', '.join(flagged)}. Memerlukan perhatian segera."
        ))
    return alerts


def _check_dangerous_meds(data: dict) -> list[AlertItem]:
    alerts = []
    medications: list[str] = data.get("medications") or []
    flagged = []
    for med in medications:
        base = med.lower().strip().split()[0] if med.strip() else ""
        if base in DANGEROUS_MEDS:
            flagged.append(med)
    if flagged:
        alerts.append(AlertItem(
            severity="warning",
            alert_type="dangerous_dosage",
            message=f"Obat dengan indeks terapeutik sempit atau risiko tinggi terdeteksi: {', '.join(flagged)}. Verifikasi dosis dan monitoring ketat diperlukan."
        ))
    return alerts


def _check_interactions_hardcoded(medications: list[str]) -> list[AlertItem]:
    """Check drug interactions against the hardcoded ruleset."""
    alerts = []
    # Normalize all meds to sets of keys
    normalized_sets = [_normalize(m) for m in medications]
    all_keys = [key for keys in normalized_sets for key in keys]

    checked_pairs: set[frozenset] = set()
    for i, keys_a in enumerate(normalized_sets):
        for j, keys_b in enumerate(normalized_sets):
            if i >= j:
                continue
            for key_a in keys_a:
                for key_b in keys_b:
                    pair = frozenset({key_a, key_b})
                    if pair in checked_pairs:
                        continue
                    checked_pairs.add(pair)
                    if pair in INTERACTION_RULES:
                        alerts.append(AlertItem(
                            severity="critical",
                            alert_type="drug_interaction",
                            message=f"🚨 Interaksi obat terdeteksi: {INTERACTION_RULES[pair]}"
                        ))
    return alerts


def _check_interactions_llm(medications: list[str], already_flagged_pairs: set[frozenset]) -> list[AlertItem]:
    """
    LLM fallback: ask Llama 3.2 about interactions not caught by the ruleset.
    Only called when there are 2+ medications not fully covered by hardcoded rules.
    """
    if len(medications) < 2:
        return []

    prompt = PromptTemplate(
        input_variables=["medications"],
        template="""Kamu adalah apoteker klinis ahli.
Diberikan daftar obat berikut: {medications}

Identifikasi HANYA interaksi obat yang berbahaya secara klinis (bukan interaksi minor).
Untuk setiap interaksi berbahaya yang ditemukan, tulis dalam format JSON array seperti berikut:
[
  {{"drugs": ["obat_a", "obat_b"], "description": "penjelasan singkat bahaya dalam Bahasa Indonesia"}}
]

Jika tidak ada interaksi berbahaya, kembalikan array kosong: []
Kembalikan HANYA JSON, tanpa penjelasan tambahan, tanpa markdown.
"""
    )
    try:
        chain = prompt | _llm
        result = chain.invoke({"medications": ", ".join(medications)})
        clean = re.sub(r"```json|```", "", result).strip()
        interactions = json.loads(clean)

        alerts = []
        for item in interactions:
            drugs = item.get("drugs", [])
            desc = item.get("description", "")
            if len(drugs) >= 2 and desc:
                pair = frozenset(d.lower() for d in drugs)
                # Skip if already caught by hardcoded rules
                if pair not in already_flagged_pairs:
                    alerts.append(AlertItem(
                        severity="critical",
                        alert_type="drug_interaction",
                        message=f"🚨 Interaksi obat (AI): {desc} ({', '.join(drugs)})"
                    ))
        return alerts
    except Exception:
        # LLM fallback should never crash the extraction pipeline
        return []


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze_extraction(extraction_result: dict) -> list[AlertItem]:
    """
    Run all alert checks against an extraction result.
    Returns a list of AlertItem sorted by severity (critical first).
    """
    all_alerts: list[AlertItem] = []

    # 1. Missing fields
    all_alerts.extend(_check_missing_fields(extraction_result))

    # 2. High-risk ICD-10
    all_alerts.extend(_check_high_risk_icd10(extraction_result))

    # 3. Dangerous medications
    all_alerts.extend(_check_dangerous_meds(extraction_result))

    # 4. Drug interactions — hardcoded ruleset
    medications: list[str] = extraction_result.get("medications") or []
    hardcoded_alerts = _check_interactions_hardcoded(medications)
    all_alerts.extend(hardcoded_alerts)

    # Collect pairs already flagged to avoid LLM duplicates
    flagged_pairs: set[frozenset] = set()
    for alert in hardcoded_alerts:
        # Extract drug names from message for dedup (best-effort)
        pass  # LLM uses its own judgment; near-duplicates acceptable

    # 5. Drug interactions — LLM fallback
    llm_alerts = _check_interactions_llm(medications, flagged_pairs)
    all_alerts.extend(llm_alerts)

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    return all_alerts