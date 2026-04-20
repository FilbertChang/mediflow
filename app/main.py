from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from app.routers import documents, extraction, rag, summarization, search, patients, export, health
from app.database import engine
from app.models import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MediFlow",
    version="1.0.0",
    description="Production-ready healthcare AI platform with RAG, clinical extraction, and auto summarization."
)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred.", "error": str(exc)}
    )

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(rag.router)
app.include_router(summarization.router)
app.include_router(search.router)
app.include_router(patients.router)
app.include_router(export.router)
app.include_router(health.router)

@app.get("/")
def root():
    return FileResponse("static/index.html")

@app.get("/api/info")
def api_info():
    return {
        "name": "MediFlow API",
        "version": "1.0.0",
        "features": [
            "document_ingestion",
            "clinical_extraction",
            "rag_chat",
            "auto_summarization",
            "semantic_search",
            "patient_profiles",
            "csv_export",
            "langsmith_observability"
        ]
    }