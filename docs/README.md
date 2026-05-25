<img width="1919" height="916" alt="Screenshot 2026-05-25 194713" src="https://github.com/user-attachments/assets/f647e9bc-b9e2-45aa-a300-bb91a305be14" />
<img width="1919" height="916" alt="Screenshot 2026-05-25 194725" src="https://github.com/user-attachments/assets/2a0cb20e-892d-4984-93d9-83e1cc909087" />
<img width="1919" height="915" alt="Screenshot 2026-05-25 194755" src="https://github.com/user-attachments/assets/8b303ac7-6306-4533-b7ff-99983524ac6b" />
<img width="1919" height="917" alt="Screenshot 2026-05-25 194759" src="https://github.com/user-attachments/assets/97bb9023-a8e6-452c-b54e-a1fe28cbbba9" />
<img width="1919" height="915" alt="Screenshot 2026-05-25 194804" src="https://github.com/user-attachments/assets/8e3b852e-8613-4fd0-a7f6-b67c630e9bf0" />
<img width="1919" height="915" alt="Screenshot 2026-05-25 194808" src="https://github.com/user-attachments/assets/4cbe86f6-3e59-48ad-92d7-03bf69d25d9e" />
<img width="1919" height="915" alt="Screenshot 2026-05-25 194812" src="https://github.com/user-attachments/assets/0cdca3ca-1fd2-49e0-a7d5-5417347b4c48" />
<img width="1919" height="913" alt="Screenshot 2026-05-25 194816" src="https://github.com/user-attachments/assets/ac17893d-362c-4ff5-97e9-40f52e820b16" />
<img width="1919" height="918" alt="Screenshot 2026-05-25 194820" src="https://github.com/user-attachments/assets/cc128108-284f-49b9-bc9f-acfa9ba99be9" />
<img width="1919" height="919" alt="Screenshot 2026-05-25 194824" src="https://github.com/user-attachments/assets/b5cb0f9f-5262-42a0-a732-f15fc3701ef8" />
<img width="1919" height="915" alt="Screenshot 2026-05-25 194829" src="https://github.com/user-attachments/assets/b3f40925-5dba-40dc-a404-88c7b35e5509" />
<img width="1919" height="917" alt="Screenshot 2026-05-25 194834" src="https://github.com/user-attachments/assets/a3f0e9c0-a148-4422-8800-1c6a4da3e8c0" />
<img width="1919" height="917" alt="Screenshot 2026-05-25 194839" src="https://github.com/user-attachments/assets/49a608b3-af01-4251-b6bc-abea83b7b4b7" />
<img width="1915" height="914" alt="Screenshot 2026-05-25 194843" src="https://github.com/user-attachments/assets/9485546f-a7ce-443b-a654-31437228aa26" />

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
| 🚨 Proactive Alerting | Auto-detect drug interactions, high-risk ICD-10 codes, dangerous medications, and missing fields — with email and Slack notifications |
| 🛡️ Policy Compliance | Check extractions against hospital policy documents (RAG-based) and manual rules — deviations flagged automatically |
| 🔗 External Integrations | Push extraction data to Google Sheets, Power BI, and Slack automatically or on demand |
| 🗄️ PostgreSQL | Persistent storage for all history, patient records, alerts, and compliance logs |
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
| Notifications | SendGrid (email), Slack Webhooks |
| Integrations | Google Sheets API, Power BI Push API, Slack |
| Frontend | HTML, CSS, JavaScript, Chart.js |
| DevOps | Docker, Docker Compose |

## Quick Start

### Without Docker

```bash
git clone https://github.com/FilbertChang/mediflow.git
cd mediflow

python -m venv venv
venv\Scripts\activate

pip install -r backend/requirements.txt
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

# Alert email notifications (optional)
SENDGRID_API_KEY=your_sendgrid_api_key
ALERT_EMAIL_FROM=you@yourdomain.com
ALERT_EMAIL_TO=doctor@hospital.com

# Slack alert notifications (optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/xxx

# Google Sheets integration (optional)
GOOGLE_SERVICE_ACCOUNT_JSON=service_account.json
GOOGLE_SHEET_ID=your_spreadsheet_id

# Power BI integration (optional — requires Power BI Premium)
POWERBI_PUSH_URL=https://api.powerbi.com/beta/xxx/datasets/xxx/rows

# Slack integration — extraction summaries (optional)
SLACK_INTEGRATION_WEBHOOK=https://hooks.slack.com/services/xxx
```

Then run:
```bash
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
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

## Alert System

MediFlow automatically analyzes every extraction result through a multi-layer detection pipeline:

| Check | Method | Severity |
|---|---|---|
| Missing critical fields (diagnosis, medications, patient name) | Rule-based | Warning |
| High-risk ICD-10 codes (MI, sepsis, stroke, PE, etc.) | Hardcoded list (~25 codes) | Critical |
| Narrow therapeutic index medications (Warfarin, Digoxin, Lithium, etc.) | Hardcoded list | Warning |
| Known drug-drug interactions (30+ pairs) | Hardcoded ruleset | Critical |
| Unknown drug-drug interactions | Llama 3.2 LLM fallback | Critical |

When alerts are detected the user is automatically navigated to the Alerts page, an unread badge appears on the sidebar, an email digest is sent via SendGrid, and a Slack message is posted if configured.

## Policy Compliance System

Admins can configure hospital protocols that are automatically checked after every extraction:

| Component | Description |
|---|---|
| Policy Documents | Upload PDF/DOCX/TXT hospital SOPs — ingested into a dedicated FAISS vectorstore |
| Manual Rules | Add structured IF/THEN rules via UI (e.g. "If Pneumonia → must prescribe Amoxicillin") |
| Auto Check | Every extraction triggers a RAG-based compliance check against all active policies |
| Deviation Alerts | Non-compliant extractions are flagged with `policy_violation` alerts |
| Compliance History | All checks are logged with status (compliant / deviation / unknown) and deviation details |

## External Integrations

MediFlow can push extraction data to external services automatically after each extraction or on demand:

| Integration | Trigger | Description |
|---|---|---|
| Google Sheets | Auto + Manual | Appends each extraction as a new row to a configured spreadsheet |
| Power BI | Auto + Manual | Pushes to a streaming dataset via Push API (requires Power BI Premium) |
| Slack | Auto + Manual | Posts a rich extraction summary card to a configured channel |

All integrations are optional — if not configured in `.env`, they are silently skipped without affecting the extraction pipeline. Admins can also trigger a bulk sync of the last 100 extractions from the Integrations page.

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
| Manage policies & rules | ✅ | ❌ | ❌ |
| View compliance history | ✅ | ✅ | ❌ |
| Manual integration sync | ✅ | ✅ | ❌ |
| Bulk integration sync | ✅ | ❌ | ❌ |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check all service statuses |
| GET | `/api/info` | List all features |
| POST | `/documents/upload` | Upload a document |
| GET | `/documents/list` | List uploaded documents |
| DELETE | `/documents/delete/{filename}` | Delete a document |
| POST | `/extract/clinical` | Extract EHR fields, run alerts, compliance check, and integrations |
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
| POST | `/compliance/policy-documents/upload` | Upload and ingest a policy document |
| GET | `/compliance/policy-documents/list` | List all policy documents |
| DELETE | `/compliance/policy-documents/{id}` | Delete a policy document |
| POST | `/compliance/rules/create` | Create a manual policy rule |
| GET | `/compliance/rules/list` | List all policy rules |
| PATCH | `/compliance/rules/{id}/toggle` | Enable or disable a rule |
| DELETE | `/compliance/rules/{id}` | Delete a rule |
| POST | `/compliance/check` | Run compliance check on an extraction |
| GET | `/compliance/history` | Get compliance check history |
| GET | `/integrations/status` | Check which integrations are configured |
| POST | `/integrations/sync` | Manually sync an extraction to selected integrations |
| POST | `/integrations/sync-all` | Bulk sync last 100 extractions (admin only) |
| POST | `/auth/register` | Create a new user (admin only) |
| POST | `/auth/login` | Login and receive JWT token |
| GET | `/auth/me` | Get current user info |
| GET | `/auth/users` | List all users (admin only) |
| PUT | `/auth/users/{id}/deactivate` | Deactivate a user (admin only) |
| PUT | `/auth/users/{id}/activate` | Activate a user (admin only) |

## API Examples

Every endpoint except `/health` and `/auth/login` requires a Bearer token. Log in
first, then send the token as an `Authorization: Bearer <token>` header.

### Log in

`POST /auth/login` — form-encoded credentials (OAuth2 password flow).

```bash
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=YOUR_PASSWORD"
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "username": "admin",
  "full_name": "System Admin",
  "role": "admin"
}
```

### Upload a document

`POST /documents/upload` — multipart upload (PDF, TXT, DOCX, CSV, XLSX; max 10MB).

```bash
curl -X POST http://localhost:8000/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@discharge_note.pdf"
```

```json
{
  "message": "'discharge_note.pdf' uploaded successfully.",
  "path": "uploads/discharge_note.pdf"
}
```

### Clinical extraction

`POST /extract/clinical` — extracts structured EHR fields from a free-text note,
then runs the alert engine and policy compliance check in the same request.
Requires the `doctor` or `admin` role.

Request:
```json
{
  "note": "Patient Budi, 45 years old, male. History of atrial fibrillation. Currently on Warfarin 5mg daily and Aspirin 81mg daily. ICD-10: I48."
}
```

Response:
```json
{
  "patient_name": "Budi",
  "age": 45,
  "gender": "male",
  "diagnosis": ["Atrial fibrillation"],
  "medications": ["Warfarin 5mg", "Aspirin 81mg"],
  "icd10_codes": ["I48"],
  "symptoms": [],
  "notes": null,
  "alerts": [
    {
      "severity": "critical",
      "alert_type": "drug_interaction",
      "message": "🚨 Drug interaction detected: Warfarin + Aspirin significantly increases bleeding risk."
    }
  ],
  "alert_count": 1,
  "compliance": {
    "status": "unknown",
    "summary": "No policies or rules configured yet. Upload a policy document or add manual rules in the Policy page.",
    "deviations": [],
    "rules_checked": 0,
    "policy_docs_used": []
  }
}
```

### Ingest a document for RAG

`POST /rag/ingest` — chunks and embeds an uploaded document into the vector store.

Request:
```json
{ "filename": "discharge_note.pdf" }
```

Response:
```json
{
  "status": "added",
  "message": "'discharge_note.pdf' ingested. 14 chunks from 3 section(s): ASSESSMENT, PLAN, MEDICATIONS",
  "chunks": 14,
  "sections": ["ASSESSMENT", "PLAN", "MEDICATIONS"]
}
```

### RAG chat

`POST /rag/chat` — asks a question about an ingested document.

Request:
```json
{
  "filename": "discharge_note.pdf",
  "question": "What medications was the patient prescribed?"
}
```

Response:
```json
{
  "answer": "The patient was prescribed Warfarin 5mg and Aspirin 81mg daily.",
  "sources": [
    { "file": "discharge_note.pdf", "section": "MEDICATIONS" }
  ]
}
```

### Semantic search

`POST /search/query` — searches across all ingested documents by meaning.

Request:
```json
{ "query": "patients with atrial fibrillation", "top_k": 5 }
```

Response:
```json
{
  "query": "patients with atrial fibrillation",
  "results": [
    {
      "file": "discharge_note.pdf",
      "section": "ASSESSMENT",
      "content": "History of atrial fibrillation, currently anticoagulated...",
      "score": 0.4127
    }
  ]
}
```

## Testing

```bash
pip install -r backend/requirements-dev.txt
cd backend
pytest
```

Tests run fully offline — the database is in-memory SQLite and all LLM / vector-store
calls are mocked, so neither PostgreSQL nor Ollama is required.

## Project Structure
```
mediflow/
├── backend/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── alerts.py          # Clinical alert endpoints
│   │   │   ├── analytics.py       # Analytics dashboard endpoints
│   │   │   ├── compliance.py      # Policy compliance endpoints
│   │   │   ├── integrations.py    # External integration endpoints
│   │   │   ├── documents.py       # File upload and management
│   │   │   ├── extraction.py      # Clinical NLP extraction + alert + compliance + integrations
│   │   │   ├── rag.py             # RAG chat endpoints
│   │   │   ├── summarization.py   # Auto summarization
│   │   │   ├── search.py          # Semantic search
│   │   │   ├── patients.py        # Patient profiles
│   │   │   ├── export.py          # CSV export
│   │   │   ├── health.py          # Health check
│   │   │   └── auth.py            # JWT authentication & user management
│   │   ├── auth.py                # JWT logic, password hashing, role checkers
│   │   ├── services/
│   │   │   ├── alert_engine.py    # Multi-layer clinical alert detection
│   │   │   ├── compliance.py      # RAG-based policy compliance checker
│   │   │   ├── integrations.py    # Google Sheets, Power BI, Slack dispatcher
│   │   │   ├── notifier.py        # SendGrid email + Slack alert dispatcher
│   │   │   ├── extractor.py       # LangChain extraction logic
│   │   │   ├── rag.py             # RAG + section-aware chunking
│   │   │   ├── summarizer.py      # Summarization logic
│   │   │   └── search.py          # Semantic search logic
│   │   ├── models/
│   │   │   └── models.py          # SQLAlchemy database models
│   │   ├── database.py            # PostgreSQL connection
│   │   └── main.py                # FastAPI app entry point
│   ├── tests/                     # pytest suite (auth, documents, extraction, RAG)
│   ├── requirements.txt
│   ├── requirements-dev.txt       # Runtime deps + pytest
│   └── pytest.ini
├── frontend/
│   └── static/
│       └── index.html             # Frontend (Chart.js, alerts, compliance, integrations pages)
├── docs/
│   └── README.md
├── .github/
│   └── workflows/
│       └── ci.yml                 # CI: run tests + build Docker image
├── uploads/                       # Uploaded medical documents
├── policy_uploads/                # Uploaded policy documents
├── vectorstore/                   # FAISS embeddings (medical documents)
├── policy_vectorstore/            # FAISS embeddings (policy documents)
├── CLAUDE.md                      # AI coding guidelines
├── Dockerfile
├── docker-compose.yml
└── .env                           # Environment variables (not committed)
```

## Author

Filbert Chang — AI Engineer
[LinkedIn](https://linkedin.com/in/filbertchang) · [X/Twitter](https://x.com/FilbertAI)
