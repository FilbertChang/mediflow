from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
import httpx
import os

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
async def health_check(db: Session = Depends(get_db)):
    status = {
        "status": "ok",
        "version": "1.0.0",
        "services": {}
    }

    # Check database
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        status["services"]["database"] = {"status": "ok"}
    except Exception as e:
        status["services"]["database"] = {"status": "error", "detail": str(e)}
        status["status"] = "degraded"

    # Check Ollama
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            res = await client.get(f"{ollama_url}/api/tags")
            if res.status_code == 200:
                models = [m["name"] for m in res.json().get("models", [])]
                status["services"]["ollama"] = {
                    "status": "ok",
                    "models": models
                }
            else:
                status["services"]["ollama"] = {"status": "error"}
                status["status"] = "degraded"
    except Exception:
        status["services"]["ollama"] = {"status": "error", "detail": "unreachable"}
        status["status"] = "degraded"

    # Check uploads folder
    upload_dir = "uploads"
    try:
        files = os.listdir(upload_dir)
        status["services"]["storage"] = {
            "status": "ok",
            "documents": len(files)
        }
    except Exception:
        status["services"]["storage"] = {"status": "error"}
        status["status"] = "degraded"

    return status