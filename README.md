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
| 📈 Analytics Dashboard | Visualize top diagnoses, medications, ICD-10 codes, and extraction volume over time |
| 🚨 Proactive Alerting | Auto-detect drug interactions, high-risk ICD-10 codes, dangerous medications, and missing fields after every extraction — with email and Slack notifications |
| 🗄️ PostgreSQL | Persistent storage for all history, patient records, and alerts |
| 📡 LangSmith | Trace every LLM call across all pipelines |
| 🏥 Health Check | Monitor database, Ollama, and storage status in real time |
| 🐳 Docker | One-command deployment with Docker Compose |
| 🔐 JWT Authentication | Secure login system with bcrypt password hashing |
| 👥 Role-Based Access | Admin, Doctor, Nurse roles with different permissions |
| 🛡️ XSS Protection | HTML sanitization on all user-facing output |

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI / LLM | Ollama + Llama 3.2 (fully local) |
| RAG | LangChain, FAISS |
| Chunking | Section-aware + SemanticChunker fallback |
| Database | PostgreSQL, SQLAlchemy |
| Observability | LangSmith |
| Notifications | SendGrid (email), Slack Webhooks (optional) |
| Frontend | HTML, CSS, JavaScript, Chart.js |
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
```
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/mediflow
POSTGRES_PASSWORD=YOUR_PASSWORD
SECRET_KEY=<32-byte hex string from secrets.token_hex(32)>
ACCESS_TOKEN_EXPIRE_MINUTES=480
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=mediflow
OLLAMA_BASE_URL=http://localhost:11434

# Alerting (required for email notifications)
SENDGRID_API_KEY=your_sendgrid_api_key
ALERT_EMAIL_FROM=mediflow@yourdomain.com
ALERT_EMAIL_TO=doctor@hospital.com

# Alerting (optional — only if using Slack)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

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
- SendGrid account (free tier) — https://sendgrid.com

## Alert System

MediFlow automatically analyzes every extraction result through a multi-layer detection pipeline:

| Check | Method | Severity |
|---|---|---|
| Missing critical fields (diagnosis, medications, patient name) | Rule-based | Warning |
| High-risk ICD-10 codes (MI, sepsis, stroke, PE, etc.) | Hardcoded list (~25 codes) | Critical |
| Narrow therapeutic index medications (Warfarin, Digoxin, Lithium, etc.) | Hardcoded list | Warning |
| Known drug-drug interactions (30+ pairs) | Hardcoded ruleset | Critical |
| Unknown drug-drug interactions | Llama 3.2 LLM fallback | Critical |

When alerts are detected:
- User is automatically navigated to the **Alerts page**
- Unread badge appears on the sidebar nav item
- Email digest sent via SendGrid
- Slack message posted (if `SLACK_WEBHOOK_URL` is configured)

## Security

| Protection | Implementation |
|---|---|
| Authentication | JWT tokens with 8-hour expiry |
| Password hashing | bcrypt |
| Role-based access | Admin, Doctor, Nurse with different permissions |
| XSS protection | HTML sanitization on all rendered output |
| CORS | Restricted to localhost origins |
| Path traversal | Filename validation on all file operations |
| File size limit | 10MB max upload size |
| Secrets | All credentials in `.env`, never committed |
| File validation | MIME type checking via magic bytes (not just extension) |
| SQL injection | SQLAlchemy ORM parameterized queries + filename validation |
| Rate limiting | 10 req/min on AI endpoints, 20 req/min on ingestion (slowapi) |

### Role Permissions

| Feature | Admin | Doctor | Nurse |
|---|---|---|---|
| Manage users | ✅ | ❌ | ❌ |
| Upload documents | ✅ | ✅ | ✅ |
| Delete documents | ✅ | ✅ | ❌ |
| Clinical extraction | ✅ | ✅ | ❌ |
| RAG chat | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ |
| Semantic search | ✅ | ✅ | ✅ |
| Patient profiles | ✅ | ✅ | ✅ |
| Export CSV | ✅ | ✅ | ❌ |
| View history | ✅ | ✅ | ❌ |
| Analytics dashboard | ✅ | ✅ | ✅ |
| View alerts | ✅ | ✅ | ✅ |
| Delete alerts | ✅ | ✅ | ❌ |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check all service statuses |
| GET | `/api/info` | List all features |
| POST | `/documents/upload` | Upload a document |
| GET | `/documents/list` | List uploaded documents |
| DELETE | `/documents/delete/{filename}` | Delete a document |
| POST | `/extract/clinical` | Extract EHR fields and run alert analysis |
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
| GET | `/analytics/summary` | Get high-level extraction stats |
| GET | `/analytics/top-diagnoses` | Top 10 most common diagnoses |
| GET | `/analytics/top-medications` | Top 10 most common medications |
| GET | `/analytics/top-icd10` | Top 10 most frequent ICD-10 codes |
| GET | `/analytics/extraction-volume` | Extraction count grouped by date |
| GET | `/alerts/list` | List all alerts |
| GET | `/alerts/unread-count` | Get unread alert badge count |
| PATCH | `/alerts/{id}/read` | Mark alert as read |
| PATCH | `/alerts/mark-all-read` | Mark all alerts as read |
| DELETE | `/alerts/{id}` | Delete an alert |
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
│   │   ├── alerts.py          # Clinical alert endpoints
│   │   ├── analytics.py       # Analytics dashboard endpoints
│   │   ├── documents.py       # File upload and management
│   │   ├── extraction.py      # Clinical NLP extraction + alert trigger
│   │   ├── rag.py             # RAG chat endpoints
│   │   ├── summarization.py   # Auto summarization
│   │   ├── search.py          # Semantic search
│   │   ├── patients.py        # Patient profiles
│   │   ├── export.py          # CSV export
│   │   ├── health.py          # Health check
│   │   └── auth.py            # JWT authentication & user management
│   ├── auth.py                # JWT logic, password hashing, role checkers
│   ├── services/
│   │   ├── alert_engine.py    # Multi-layer clinical alert detection
│   │   ├── notifier.py        # SendGrid email + Slack dispatcher
│   │   ├── extractor.py       # LangChain extraction logic
│   │   ├── rag.py             # RAG + section-aware chunking
│   │   ├── summarizer.py      # Summarization logic
│   │   └── search.py          # Semantic search logic
│   ├── models/
│   │   └── models.py          # SQLAlchemy database models
│   ├── database.py            # PostgreSQL connection
│   └── main.py                # FastAPI app entry point
├── static/
│   └── index.html             # Frontend (Chart.js, alert badge, alerts page)
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