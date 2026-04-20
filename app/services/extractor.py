from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import json
import re

import os
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)

prompt_template = PromptTemplate(
    input_variables=["note"],
    template="""
You are a clinical data extraction assistant.
Extract the following fields from the doctor's note below.
Return ONLY a valid JSON object. No explanation, no markdown, no extra text.

Fields to extract:
- patient_name (string or null)
- age (integer or null)
- gender (string or null)
- diagnosis (list of strings)
- medications (list of strings)
- icd10_codes (list of strings)
- symptoms (list of strings)
- notes (string or null)

Doctor's note:
{note}

JSON output:
"""
)

def extract_clinical_data(note: str) -> dict:
    chain = prompt_template | llm
    result = chain.invoke({"note": note})

    clean = re.sub(r"```json|```", "", result).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        return {"error": "Failed to parse response", "raw": result}