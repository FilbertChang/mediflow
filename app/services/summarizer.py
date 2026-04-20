from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from app.services.rag import load_document

import os
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)

prompt_template = PromptTemplate(
    input_variables=["text"],
    template="""
You are a medical document summarization assistant.
Summarize the following medical document clearly and concisely.
Focus on: patient info, key findings, diagnoses, treatments, and follow-up actions.
If it is not a medical document, summarize it generally.

Document:
{text}

Summary:
"""
)

def summarize_document(filename: str) -> dict:
    import os
    file_path = os.path.join("uploads", filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found.")

    docs = load_document(file_path)
    full_text = "\n\n".join([doc.page_content for doc in docs])

    # Trim to avoid overwhelming the model
    if len(full_text) > 4000:
        full_text = full_text[:4000] + "\n\n[Document trimmed for summarization]"

    chain = prompt_template | llm
    summary = chain.invoke({"text": full_text})
    return {"filename": filename, "summary": summary}