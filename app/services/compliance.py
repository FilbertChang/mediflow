"""
MediFlow Compliance Service
Checks extraction results against hospital policy documents (RAG-based)
and manual policy rules stored in PostgreSQL.

Pipeline:
  1. Query policy vectorstore for relevant sections
  2. Load active manual rules from DB
  3. Send to Llama 3.2 for compliance analysis
  4. Return ComplianceResult with status + deviations
"""

from __future__ import annotations
import os
import json
import re
from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
embeddings = OllamaEmbeddings(model="llama3.2", base_url=OLLAMA_BASE_URL)

POLICY_VECTORSTORE_DIR = "policy_vectorstore"
os.makedirs(POLICY_VECTORSTORE_DIR, exist_ok=True)


# ─────────────────────────────────────────────
# Vectorstore helpers
# ─────────────────────────────────────────────

def ingest_policy_document(filename: str, docs: list) -> int:
    """
    Chunk and ingest a policy document into the policy vectorstore.
    Returns number of chunks created.
    Reuses the same chunking pattern as rag.py.
    """
    from app.services.rag import chunk_document
    chunks = chunk_document(docs, filename)
    vectorstore_path = os.path.join(POLICY_VECTORSTORE_DIR, filename)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(vectorstore_path)
    return len(chunks)


def query_policy_vectorstore(query: str, filenames: list[str], k: int = 4) -> list[Document]:
    """
    Query one or more policy vectorstores and return top-k relevant chunks.
    Merges results across all ingested policy documents.
    """
    all_docs: list[Document] = []
    for filename in filenames:
        vs_path = os.path.join(POLICY_VECTORSTORE_DIR, filename)
        if not os.path.exists(vs_path):
            continue
        try:
            vs = FAISS.load_local(vs_path, embeddings, allow_dangerous_deserialization=True)
            results = vs.as_retriever(search_kwargs={"k": k}).invoke(query)
            all_docs.extend(results)
        except Exception:
            continue
    return all_docs


# ─────────────────────────────────────────────
# Compliance prompt
# ─────────────────────────────────────────────

COMPLIANCE_PROMPT = PromptTemplate(
    input_variables=["extraction", "policy_context", "manual_rules"],
    template="""You are a clinical auditor reviewing compliance with hospital protocols.

Patient extraction data:
{extraction}

Relevant sections from hospital policy documents:
{policy_context}

Manual rules to check:
{manual_rules}

Your task:
1. Check whether the diagnoses, medications, and treatments comply with the policy.
2. Identify any specific deviations or non-compliance.
3. Return ONLY the following JSON object, no extra explanation, no markdown:

{{
  "status": "compliant" | "deviation" | "unknown",
  "summary": "brief explanation in English (1-2 sentences)",
  "deviations": [
    {{
      "rule": "name of the rule or policy section violated",
      "detail": "specific explanation of the deviation",
      "severity": "critical" | "warning"
    }}
  ]
}}

If no relevant policy exists to compare against, use status "unknown".
If everything is compliant, use status "compliant" with an empty deviations array [].
"""
)


# ─────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────

class ComplianceResult:
    def __init__(
        self,
        status: str,
        summary: str,
        deviations: list[dict],
        rules_checked: int,
        policy_docs_used: list[str],
    ):
        self.status = status            # "compliant" | "deviation" | "unknown"
        self.summary = summary
        self.deviations = deviations    # list of {rule, detail, severity}
        self.rules_checked = rules_checked
        self.policy_docs_used = policy_docs_used

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "summary": self.summary,
            "deviations": self.deviations,
            "rules_checked": self.rules_checked,
            "policy_docs_used": self.policy_docs_used,
        }


# ─────────────────────────────────────────────
# Main compliance check
# ─────────────────────────────────────────────

def run_compliance_check(extraction_result: dict, db) -> ComplianceResult:
    """
    Full compliance check against policy documents + manual rules.
    Always returns a ComplianceResult — never raises.
    """
    from app.models.models import PolicyDocument, PolicyRule

    # Build extraction summary for the prompt
    diagnosis = extraction_result.get("diagnosis") or []
    medications = extraction_result.get("medications") or []
    icd10 = extraction_result.get("icd10_codes") or []
    symptoms = extraction_result.get("symptoms") or []
    patient_name = extraction_result.get("patient_name") or "Unknown"

    extraction_text = (
        f"Pasien: {patient_name}\n"
        f"Diagnosis: {', '.join(diagnosis) if diagnosis else 'Tidak ada'}\n"
        f"Obat-obatan: {', '.join(medications) if medications else 'Tidak ada'}\n"
        f"Kode ICD-10: {', '.join(icd10) if icd10 else 'Tidak ada'}\n"
        f"Gejala: {', '.join(symptoms) if symptoms else 'Tidak ada'}"
    )

    # Build search query from extraction
    search_query = " ".join(diagnosis + medications + icd10 + symptoms)
    if not search_query.strip():
        search_query = "clinical protocol treatment guidelines"

    # Get all ingested policy document filenames
    policy_docs = db.query(PolicyDocument).all()
    policy_filenames = [p.filename for p in policy_docs]
    policy_docs_used: list[str] = []

    # Query policy vectorstore
    policy_context = "Tidak ada dokumen kebijakan yang tersedia."
    if policy_filenames:
        relevant_chunks = query_policy_vectorstore(search_query, policy_filenames, k=5)
        if relevant_chunks:
            policy_context = "\n\n".join([
                f"[{chunk.metadata.get('section', 'POLICY')} | {chunk.metadata.get('source', '')}]\n{chunk.page_content}"
                for chunk in relevant_chunks
            ])
            # Track which policy docs were actually used
            policy_docs_used = list(set(
                chunk.metadata.get("source", "") for chunk in relevant_chunks
            ))

    # Get active manual rules
    active_rules = db.query(PolicyRule).filter(PolicyRule.is_active == 1).all()
    rules_checked = len(active_rules)

    manual_rules_text = "Tidak ada aturan manual yang aktif."
    if active_rules:
        rule_lines = []
        for rule in active_rules:
            rule_lines.append(
                f"[{rule.severity.upper()}] {rule.title}\n"
                f"  Kondisi: {rule.condition}\n"
                f"  Persyaratan: {rule.requirement}"
            )
        manual_rules_text = "\n\n".join(rule_lines)

    # Skip LLM if nothing to check against
    if not policy_filenames and not active_rules:
        return ComplianceResult(
            status="unknown",
            summary="No policies or rules configured yet. Upload a policy document or add manual rules in the Policy page.",
            deviations=[],
            rules_checked=0,
            policy_docs_used=[],
        )

    # Call LLM
    try:
        chain = COMPLIANCE_PROMPT | llm
        result = chain.invoke({
            "extraction": extraction_text,
            "policy_context": policy_context,
            "manual_rules": manual_rules_text,
        })

        clean = re.sub(r"```json|```", "", result).strip()
        parsed = json.loads(clean)

        return ComplianceResult(
            status=parsed.get("status", "unknown"),
            summary=parsed.get("summary", ""),
            deviations=parsed.get("deviations", []),
            rules_checked=rules_checked,
            policy_docs_used=policy_docs_used,
        )

    except (json.JSONDecodeError, Exception):
        # LLM failed or returned malformed JSON — never crash the extraction
        return ComplianceResult(
            status="unknown",
            summary="Compliance check could not be completed. Check server logs for details.",
            deviations=[],
            rules_checked=rules_checked,
            policy_docs_used=policy_docs_used,
        )