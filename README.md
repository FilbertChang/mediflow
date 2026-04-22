# MediFlow 🏥

A production-ready local healthcare AI platform built with FastAPI, LangChain, and Ollama.
100% local inference — no cloud, no API costs, no data leaves your machine.

## Features

| Feature | Description |
|---|---|
| 📄 Document Ingestion | Upload PDF, DOCX, TXT, CSV, XLSX with smart add/update/skip logic |
| 🧠 Clinical Extraction | Extract patient name, age, diagnosis, medications, ICD-10 codes from doctor notes |
| 💬 RAG Chat | Ask questions about any uploaded medical document with source tracking |
| 📝 Auto Summarization | Generate AI summaries of medical documents |
| 🔍 Semantic Search | Search across all ingested documents by meaning, not just keywords |
| 👤 Patient Profiles | Group documents and extractions by patient |
| 📊 CSV Export | Export extraction, chat, and summary history to CSV |
| 🗄️ PostgreSQL | Persistent storage for all history and patient records |
| 📡 LangSmith | Trace every LLM call across all pipelines |
| 🏥 Health Check | Monitor database, Ollama, and storage status in real time |
| 🐳 Docker | One-command deployment with Docker Compose |
| 🔐 JWT Authentication | Secure login system with bcrypt password hashing |
| 👥 Role-Based Access | Admin, Doctor, Nurse roles with different permissions |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI / LLM | Ollama + Llama 3.2 (fully local) |
| RAG | LangChain, FAISS |
| Chunking | Section-aware + SemanticChunker fallback |
| Database | PostgreSQL, SQLAlchemy |
| Observability | LangSmith |
| Frontend | HTML, CSS, JavaScript |
| DevOps | Docker, Docker Compose |

## Quick Start

### Without Docker

```bash
git clone https://github.com/FilbertChang/mediflow.git
cd mediflow

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the root directory:
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/mediflow
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=mediflow
OLLAMA_BASE_URL=http://localhost:11434
POSTGRES_PASSWORD=YOUR_PASSWORD

Then run:
```bash
uvicorn app.main:app --reload
```

### With Docker

```bash
git clone https://github.com/FilbertChang/mediflow.git
cd mediflow
# Create .env file as above
docker-compose up --build
```

Open **http://localhost:8000**

## Requirements

- Python 3.11+
- Ollama with Llama 3.2 — `ollama pull llama3.2`
- PostgreSQL (or Docker — PostgreSQL is included automatically)
- LangSmith account (free) — https://smith.langchain.com

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check all service statuses |
| GET | `/api/info` | List all features |
| POST | `/documents/upload` | Upload a document |
| GET | `/documents/list` | List uploaded documents |
| DELETE | `/documents/delete/{filename}` | Delete a document |
| POST | `/extract/clinical` | Extract EHR fields from doctor notes |
| GET | `/extract/history` | Get extraction history |
| POST | `/rag/ingest` | Ingest document into vector store |
| POST | `/rag/chat` | Ask questions about a document |
| GET | `/rag/history` | Get chat history |
| POST | `/summarize/document` | Summarize a document |
| GET | `/summarize/history` | Get summary history |
| POST | `/search/query` | Semantic search across all documents |
| POST | `/patients/create` | Create a patient profile |
| GET | `/patients/list` | List all patients |
| GET | `/patients/{id}` | Get patient with documents and extractions |
| POST | `/patients/link-document` | Link a document to a patient |
| GET | `/export/extractions` | Export extractions as CSV |
| GET | `/export/chats` | Export chat history as CSV |
| GET | `/export/summaries` | Export summaries as CSV |
| POST | `/auth/register` | Create a new user (admin only) |
| POST | `/auth/login` | Login and receive JWT token |
| GET | `/auth/me` | Get current user info |
| GET | `/auth/users` | List all users (admin only) |
| PUT | `/auth/users/{id}/deactivate` | Deactivate a user (admin only) |
| PUT | `/auth/users/{id}/activate` | Activate a user (admin only) |

## Project Structure
```
mediflow/
├── app/
│   ├── routers/
│   │   ├── documents.py       # File upload and management
│   │   ├── extraction.py      # Clinical NLP extraction
│   │   ├── rag.py             # RAG chat endpoints
│   │   ├── summarization.py   # Auto summarization
│   │   ├── search.py          # Semantic search
│   │   ├── patients.py        # Patient profiles
│   │   ├── export.py          # CSV export
│   │   └── health.py          # Health check
│   │   └── auth.py            # JWT authentication & user management
│   ├── auth.py                # JWT logic, password hashing, role checkers
│   ├── services/
│   │   ├── extractor.py       # LangChain extraction logic
│   │   ├── rag.py             # RAG + section-aware chunking
│   │   ├── summarizer.py      # Summarization logic
│   │   └── search.py          # Semantic search logic
│   ├── models/
│   │   └── models.py          # SQLAlchemy database models
│   ├── database.py            # PostgreSQL connection
│   └── main.py                # FastAPI app entry point
├── static/
│   └── index.html             # Frontend dashboard
├── uploads/                   # Uploaded documents
├── vectorstore/               # FAISS embeddings
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env                       # Environment variables (not committed)
```

## Author

Filbert Chang — AI Engineer
[LinkedIn](https://linkedin.com/in/filbertchang) · [X/Twitter](https://x.com/FilbertAI)
