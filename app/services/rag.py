from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
import docx2txt
import pandas as pd
import re
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
embeddings = OllamaEmbeddings(model="llama3.2", base_url=OLLAMA_BASE_URL)

UPLOAD_DIR = "uploads"
VECTORSTORE_DIR = "vectorstore"
os.makedirs(VECTORSTORE_DIR, exist_ok=True)

CLINICAL_HEADERS = [
    "CHIEF COMPLAINT", "HISTORY OF PRESENT ILLNESS", "HPI",
    "PAST MEDICAL HISTORY", "PMH", "MEDICATIONS", "ALLERGIES",
    "REVIEW OF SYSTEMS", "ROS", "PHYSICAL EXAMINATION", "VITALS",
    "ASSESSMENT", "PLAN", "DIAGNOSIS", "PROCEDURES", "LABS",
    "IMAGING", "FOLLOW UP", "DISCHARGE SUMMARY", "NOTES",
    "LABORATORY DATA", "IMPRESSION", "DISCHARGE INSTRUCTIONS"
]

prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template="""
You are a helpful medical assistant. Use the context below to answer the question.
If the answer is not in the context, say "I don't have enough information to answer that."

Context:
{context}

Question:
{question}

Answer:
"""
)

def load_document(file_path: str) -> list:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        loader = PyPDFLoader(file_path)
        return loader.load()
    elif ext == ".txt":
        loader = TextLoader(file_path, encoding="utf-8")
        return loader.load()
    elif ext == ".docx":
        text = docx2txt.process(file_path)
        return [Document(page_content=text, metadata={"source": file_path})]
    elif ext in [".csv", ".xlsx"]:
        df = pd.read_csv(file_path) if ext == ".csv" else pd.read_excel(file_path)
        text = df.to_string()
        return [Document(page_content=text, metadata={"source": file_path})]
    else:
        raise ValueError(f"Unsupported file type: {ext}")

def detect_sections(text: str) -> list:
    """Split text by clinical headers if found, otherwise return as single section."""
    pattern = r'(?i)(?:^|\n)(' + '|'.join(CLINICAL_HEADERS) + r')\s*[:\n]'
    matches = list(re.finditer(pattern, text))

    if len(matches) < 2:
        return [{"section": "GENERAL", "content": text}]

    sections = []
    for i, match in enumerate(matches):
        section_name = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections.append({"section": section_name, "content": content})

    return sections

def chunk_document(docs: list, filename: str) -> list:
    """Section-aware chunking with SemanticChunker fallback for unstructured text."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    semantic_splitter = SemanticChunker(embeddings)
    all_chunks = []

    for doc in docs:
        text = doc.page_content
        sections = detect_sections(text)

        if len(sections) == 1 and sections[0]["section"] == "GENERAL":
            # No clinical headers found — use SemanticChunker
            try:
                chunks = semantic_splitter.split_documents([doc])
                for chunk in chunks:
                    chunk.metadata["section"] = "SEMANTIC"
                    chunk.metadata["source"] = filename
                all_chunks.extend(chunks)
            except Exception:
                # Last resort fallback
                chunks = splitter.split_documents([doc])
                for chunk in chunks:
                    chunk.metadata["section"] = "GENERAL"
                    chunk.metadata["source"] = filename
                all_chunks.extend(chunks)
        else:
            # Clinical headers found — chunk per section
            for section in sections:
                section_doc = Document(
                    page_content=f"[{section['section']}]\n{section['content']}",
                    metadata={
                        "source": filename,
                        "section": section["section"]
                    }
                )
                sub_chunks = splitter.split_documents([section_doc])
                all_chunks.extend(sub_chunks)

    return all_chunks

def ingest_document(filename: str, db=None) -> dict:
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename.")

    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in uploads.")

    docs = load_document(file_path)
    current_char_count = sum(len(doc.page_content) for doc in docs)

    if db:
        from app.models.models import IngestedDocument
        from sqlalchemy.sql import func
        existing = db.query(IngestedDocument).filter(
            IngestedDocument.filename == filename
        ).first()

        if existing:
            if current_char_count <= existing.char_count:
                return {
                    "status": "skipped",
                    "message": f"'{filename}' is already up to date. Skipping.",
                    "chunks": existing.chunk_count
                }
            else:
                action = "updated"
        else:
            action = "added"
    else:
        action = "added"

    # Use section-aware chunking
    chunks = chunk_document(docs, filename)
    sections_found = set(c.metadata.get("section", "GENERAL") for c in chunks)

    vectorstore_path = os.path.join(VECTORSTORE_DIR, filename)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(vectorstore_path)

    if db:
        from app.models.models import IngestedDocument
        from sqlalchemy.sql import func
        existing = db.query(IngestedDocument).filter(
            IngestedDocument.filename == filename
        ).first()
        if existing:
            existing.chunk_count = len(chunks)
            existing.char_count = current_char_count
            existing.updated_at = func.now()
        else:
            record = IngestedDocument(
                filename=filename,
                chunk_count=len(chunks),
                char_count=current_char_count
            )
            db.add(record)
        db.commit()

    messages = {
        "added": f"'{filename}' ingested. {len(chunks)} chunks from {len(sections_found)} section(s): {', '.join(sections_found)}",
        "updated": f"'{filename}' re-ingested. {len(chunks)} chunks from {len(sections_found)} section(s): {', '.join(sections_found)}"
    }

    return {
        "status": action,
        "message": messages[action],
        "chunks": len(chunks),
        "sections": list(sections_found)
    }

def chat_with_document(filename: str, question: str) -> dict:
    # Prevent path traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid filename.")

    vectorstore_path = os.path.join(VECTORSTORE_DIR, filename)
    if not os.path.exists(vectorstore_path):
        raise FileNotFoundError(f"Document '{filename}' has not been ingested yet.")

    vectorstore = FAISS.load_local(
        vectorstore_path, embeddings, allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    relevant_docs = retriever.invoke(question)
    context = "\n\n".join([
        f"[{doc.metadata.get('section', 'GENERAL')}]\n{doc.page_content}"
        for doc in relevant_docs
    ])

    chain = prompt_template | llm
    answer = chain.invoke({"context": context, "question": question})

    # Build source list
    sources = []
    seen = set()
    for doc in relevant_docs:
        source = doc.metadata.get("source", filename)
        section = doc.metadata.get("section", "GENERAL")
        key = f"{source}|{section}"
        if key not in seen:
            seen.add(key)
            sources.append({
                "file": source,
                "section": section
            })

    return {
        "answer": answer,
        "sources": sources
    }