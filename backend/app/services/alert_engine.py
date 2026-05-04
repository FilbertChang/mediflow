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
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)

# ─────────────────────────────────────────────
# Reference data
# ─────────────────────────────────────────────

HIGH_RISK_ICD10 = {
    "I21", "I22",
    "I26",
    "I46",
    "I50",
    "I60", "I61", "I62", "I63", "I64",
    "A41",
    "A40",
    "R65",
    "J96",
    "J18",
    "N17",
    "E11.65", "E10.65",
    "E86",
    "C34", "C50", "C61", "C18",
}

DANGEROUS_MEDS = {
    "warfarin", "heparin", "enoxaparin",
    "digoxin", "lithium",
    "methotrexate",
    "amiodarone",
    "phenytoin", "carbamazepine",
    "clozapine",
    "cyclosporine", "tacrolimus",
    "insulin",
    "morphine", "fentanyl", "oxycodone", "tramadol",
    "vancomycin", "gentamicin", "tobramycin",
}

INTERACTION_RULES: dict[frozenset, str] = {
    frozenset({"warfarin", "aspirin"}): "Warfarin + Aspirin significantly increases bleeding risk.",
    frozenset({"warfarin", "ibuprofen"}): "Warfarin + Ibuprofen increases bleeding risk.",
    frozenset({"warfarin", "naproxen"}): "Warfarin + Naproxen increases bleeding risk.",
    frozenset({"warfarin", "metronidazole"}): "Warfarin + Metronidazole significantly potentiates anticoagulant effect.",
    frozenset({"warfarin", "fluconazole"}): "Warfarin + Fluconazole significantly increases INR.",
    frozenset({"warfarin", "amiodarone"}): "Warfarin + Amiodarone potentiates anticoagulant effect.",
    frozenset({"metformin", "contrast"}): "Metformin + IV Contrast — hold metformin 48 hours before procedure.",
    frozenset({"ssri", "tramadol"}): "SSRI + Tramadol increases risk of serotonin syndrome.",
    frozenset({"ssri", "linezolid"}): "SSRI + Linezolid — high risk of serotonin syndrome.",
    frozenset({"maoi", "ssri"}): "MAOI + SSRI — absolute contraindication, risk of fatal serotonin syndrome.",
    frozenset({"maoi", "tramadol"}): "MAOI + Tramadol — risk of fatal serotonin syndrome.",
    frozenset({"digoxin", "amiodarone"}): "Digoxin + Amiodarone elevates digoxin levels, risk of toxicity.",
    frozenset({"digoxin", "clarithromycin"}): "Digoxin + Clarithromycin elevates digoxin levels.",
    frozenset({"simvastatin", "amiodarone"}): "Simvastatin + Amiodarone increases risk of myopathy.",
    frozenset({"clopidogrel", "omeprazole"}): "Clopidogrel + Omeprazole reduces antiplatelet effect.",
    frozenset({"methotrexate", "nsaid"}): "Methotrexate + NSAID increases methotrexate toxicity.",
    frozenset({"lithium", "ibuprofen"}): "Lithium + Ibuprofen elevates lithium levels, risk of toxicity.",
    frozenset({"lithium", "ace inhibitor"}): "Lithium + ACE Inhibitor elevates lithium levels.",
    frozenset({"lithium", "thiazide"}): "Lithium + Thiazide elevates lithium levels.",
    frozenset({"carbamazepine", "erythromycin"}): "Carbamazepine + Erythromycin elevates carbamazepine levels.",
    frozenset({"phenytoin", "fluconazole"}): "Phenytoin + Fluconazole elevates phenytoin levels.",
    frozenset({"insulin", "alcohol"}): "Insulin + Alcohol increases risk of severe hypoglycemia.",
    frozenset({"morphine", "benzodiazepine"}): "Opioid + Benzodiazepine — risk of fatal respiratory depression.",
    frozenset({"fentanyl", "benzodiazepine"}): "Opioid + Benzodiazepine — risk of fatal respiratory depression.",
    frozenset({"oxycodone", "benzodiazepine"}): "Opioid + Benzodiazepine — risk of fatal respiratory depression.",
    frozenset({"tramadol", "benzodiazepine"}): "Opioid + Benzodiazepine — risk of fatal respiratory depression.",
    frozenset({"sildenafil", "nitrate"}): "Sildenafil + Nitrate — severe hypotension, absolute contraindication.",
    frozenset({"tadalafil", "nitrate"}): "Tadalafil + Nitrate — severe hypotension, absolute contraindication.",
    frozenset({"vancomycin", "gentamicin"}): "Vancomycin + Gentamicin increases risk of nephrotoxicity.",
    frozenset({"vancomycin", "tobramycin"}): "Vancomycin + Tobramycin increases risk of nephrotoxicity.",
    frozenset({"tacrolimus", "fluconazole"}): "Tacrolimus + Fluconazole elevates tacrolimus levels, risk of toxicity.",
    frozenset({"cyclosporine", "simvastatin"}): "Cyclosporine + Simvastatin increases risk of severe myopathy.",
}

MED_ALIASES: dict[str, str] = {
    "sertraline": "ssri", "fluoxetine": "ssri", "paroxetine": "ssri",
    "escitalopram": "ssri", "citalopram": "ssri", "fluvoxamine": "ssri",
    "phenelzine": "maoi", "tranylcypromine": "maoi", "selegiline": "maoi",
    "isocarboxazid": "maoi",
    "ibuprofen": "nsaid", "naproxen": "nsaid", "diclofenac": "nsaid",
    "celecoxib": "nsaid", "meloxicam": "nsaid", "indomethacin": "nsaid",
    "ketorolac": "nsaid",
    "nitroglycerin": "nitrate", "isosorbide": "nitrate",
    "diazepam": "benzodiazepine", "lorazepam": "benzodiazepine",
    "alprazolam": "benzodiazepine", "clonazepam": "benzodiazepine",
    "midazolam": "benzodiazepine",
    "lisinopril": "ace inhibitor", "enalapril": "ace inhibitor",
    "ramipril": "ace inhibitor", "captopril": "ace inhibitor",
    "hydrochlorothiazide": "thiazide", "chlorthalidone": "thiazide",
    "atorvastatin": "statin", "rosuvastatin": "statin",
    "lovastatin": "statin", "pravastatin": "statin",
    "codeine": "tramadol",
}


def _normalize(med: str) -> list[str]:
    raw = med.lower().strip()
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
        self.severity = severity
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
            message=f"Critical fields missing from doctor note: {', '.join(missing)}. Please verify manually."
        ))
    return alerts


def _check_high_risk_icd10(data: dict) -> list[AlertItem]:
    alerts = []
    codes: list[str] = data.get("icd10_codes") or []
    flagged = []
    for code in codes:
        code_upper = code.strip().upper()
        for risk_code in HIGH_RISK_ICD10:
            if code_upper == risk_code or code_upper.startswith(risk_code):
                flagged.append(code_upper)
                break
    if flagged:
        alerts.append(AlertItem(
            severity="critical",
            alert_type="high_risk_icd10",
            message=f"⚠️ High-risk ICD-10 code(s) detected: {', '.join(flagged)}. Immediate clinical attention required."
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
            message=f"Narrow therapeutic index or high-risk medication(s) detected: {', '.join(flagged)}. Dose verification and close monitoring required."
        ))
    return alerts


def _check_interactions_hardcoded(medications: list[str]) -> list[AlertItem]:
    alerts = []
    normalized_sets = [_normalize(m) for m in medications]
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
                            message=f"🚨 Drug interaction detected: {INTERACTION_RULES[pair]}"
                        ))
    return alerts


def _check_interactions_llm(medications: list[str], already_flagged_pairs: set[frozenset]) -> list[AlertItem]:
    if len(medications) < 2:
        return []

    prompt = PromptTemplate(
        input_variables=["medications"],
        template="""You are an expert clinical pharmacist.
Given the following list of medications: {medications}

Identify ONLY clinically significant dangerous drug interactions (not minor interactions).
For each dangerous interaction found, respond in the following JSON array format:
[
  {{"drugs": ["drug_a", "drug_b"], "description": "brief explanation of the danger in English"}}
]

If no dangerous interactions are found, return an empty array: []
Return ONLY the JSON, no additional explanation, no markdown.
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
                if pair not in already_flagged_pairs:
                    alerts.append(AlertItem(
                        severity="critical",
                        alert_type="drug_interaction",
                        message=f"🚨 Drug interaction (AI): {desc} ({', '.join(drugs)})"
                    ))
        return alerts
    except Exception:
        return []


# ─────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────

def analyze_extraction(extraction_result: dict) -> list[AlertItem]:
    all_alerts: list[AlertItem] = []

    all_alerts.extend(_check_missing_fields(extraction_result))
    all_alerts.extend(_check_high_risk_icd10(extraction_result))
    all_alerts.extend(_check_dangerous_meds(extraction_result))

    medications: list[str] = extraction_result.get("medications") or []
    hardcoded_alerts = _check_interactions_hardcoded(medications)
    all_alerts.extend(hardcoded_alerts)

    flagged_pairs: set[frozenset] = set()
    llm_alerts = _check_interactions_llm(medications, flagged_pairs)
    all_alerts.extend(llm_alerts)

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    all_alerts.sort(key=lambda a: severity_order.get(a.severity, 3))

    return all_alerts