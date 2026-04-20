from langchain_ollama import OllamaLLM, OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import docx2txt
import pandas as pd
from langchain_core.documents import Document
import os

import os
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
llm = OllamaLLM(model="llama3.2", base_url=OLLAMA_BASE_URL)
embeddings = OllamaEmbeddings(model="llama3.2", base_url=OLLAMA_BASE_URL)

UPLOAD_DIR = "uploads"
VECTORSTORE_DIR = "vectorstore"
os.makedirs(VECTORSTORE_DIR, exist_ok=True)

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

def ingest_document(filename: str) -> str:
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in uploads.")

    docs = load_document(file_path)

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    vectorstore_path = os.path.join(VECTORSTORE_DIR, filename)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(vectorstore_path)

    return f"'{filename}' ingested successfully. {len(chunks)} chunks created."

def chat_with_document(filename: str, question: str) -> str:
    vectorstore_path = os.path.join(VECTORSTORE_DIR, filename)
    if not os.path.exists(vectorstore_path):
        raise FileNotFoundError(f"Document '{filename}' has not been ingested yet.")

    vectorstore = FAISS.load_local(
        vectorstore_path, embeddings, allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    relevant_docs = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in relevant_docs])

    chain = prompt_template | llm
    answer = chain.invoke({"context": context, "question": question})
    return answer