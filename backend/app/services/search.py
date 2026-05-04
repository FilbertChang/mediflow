from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
embeddings = OllamaEmbeddings(model="llama3.2", base_url=OLLAMA_BASE_URL)

VECTORSTORE_DIR = "vectorstore"
UPLOAD_DIR = "uploads"

def get_all_ingested_files() -> list:
    """Return list of all files that have a vectorstore."""
    if not os.path.exists(VECTORSTORE_DIR):
        return []
    return [
        f for f in os.listdir(VECTORSTORE_DIR)
        if os.path.isdir(os.path.join(VECTORSTORE_DIR, f))
    ]

def semantic_search(query: str, top_k: int = 5) -> list:
    """Search across all ingested documents for the most relevant chunks."""
    ingested_files = get_all_ingested_files()

    if not ingested_files:
        return []

    all_results = []

    for filename in ingested_files:
        vectorstore_path = os.path.join(VECTORSTORE_DIR, filename)
        try:
            vectorstore = FAISS.load_local(
                vectorstore_path,
                embeddings,
                allow_dangerous_deserialization=True
            )
            # Search within this document
            docs_with_scores = vectorstore.similarity_search_with_score(
                query, k=min(top_k, 3)
            )
            for doc, score in docs_with_scores:
                all_results.append({
                    "file": filename,
                    "section": doc.metadata.get("section", "GENERAL"),
                    "content": doc.page_content[:300],
                    "score": round(float(score), 4)
                })
        except Exception:
            continue

    # Sort by score — lower score = more similar in FAISS
    all_results.sort(key=lambda x: x["score"])

    return all_results[:top_k]