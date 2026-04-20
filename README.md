# MediFlow 🏥

A production-ready local healthcare AI platform built with FastAPI, LangChain, and Ollama.
No cloud required — runs entirely on your machine.

## Features

- 📄 **Document Ingestion** — Upload PDF, DOCX, TXT, CSV, XLSX
- 🧠 **Clinical Data Extraction** — Extract patient name, diagnosis, medications, ICD-10 codes from doctor notes
- 💬 **RAG Chat** — Ask questions about any uploaded medical document
- 📝 **Auto Summarization** — Generate AI summaries of medical documents
- 🗄️ **PostgreSQL** — Persistent storage for extraction and chat history
- 🐳 **Docker** — One-command deployment

## Tech Stack

- **Backend:** Python, FastAPI, LangChain, SQLAlchemy
- **AI:** Ollama + Llama 3.2 (local, free, no API key)
- **Vector Store:** FAISS
- **Database:** PostgreSQL
- **Frontend:** HTML, CSS, JavaScript
- **DevOps:** Docker, Docker Compose

## Quick Start

### Without Docker
```bash
git clone https://github.com/FilbertChang/mediflow.git
cd mediflow
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### With Docker
```bash
git clone https://github.com/FilbertChang/mediflow.git
cd mediflow
# Create .env file with your PostgreSQL password
docker-compose up --build
```

Then open http://localhost:8000

## Requirements

- Python 3.11+
- Ollama with Llama 3.2 (`ollama pull llama3.2`)
- PostgreSQL (or Docker)

## Project Structure
mediflow/
├── app/
│   ├── routers/        # API endpoints
│   ├── services/       # AI logic (RAG, extraction, summarization)
│   ├── models/         # Database models
│   ├── database.py     # PostgreSQL connection
│   └── main.py         # FastAPI app
├── static/             # Frontend (HTML/CSS/JS)
├── uploads/            # Uploaded documents
├── vectorstore/        # FAISS embeddings
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

## Author

Filbert Chang — AI Engineer