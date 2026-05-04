from dotenv import load_dotenv
from pathlib import Path
import os
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static" if (BASE_DIR / "static").exists() else BASE_DIR.parent / "frontend" / "static"

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.routers import documents, extraction, rag, summarization, search, patients, export, health, auth, analytics, alerts, compliance, integrations
from app.database import engine
from app.models import models
from app.limiter import limiter

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MediFlow",
    version="1.0.0",
    description="Production-ready healthcare AI platform."
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."}
    )

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(rag.router)
app.include_router(summarization.router)
app.include_router(search.router)
app.include_router(patients.router)
app.include_router(export.router)
app.include_router(analytics.router)
app.include_router(alerts.router)
app.include_router(compliance.router)
app.include_router(integrations.router)

@app.get("/")
def root():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/api/info")
def api_info():
    return {
        "name": "MediFlow API",
        "version": "1.0.0",
        "features": [
            "document_ingestion", "clinical_extraction",
            "rag_chat", "auto_summarization", "semantic_search",
            "patient_profiles", "csv_export", "langsmith_observability"
        ]
    }