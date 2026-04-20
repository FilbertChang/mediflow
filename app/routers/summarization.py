from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.summarizer import summarize_document
from app.database import get_db
from app.models.models import SummaryHistory

router = APIRouter(prefix="/summarize", tags=["Summarization"])

class SummarizeRequest(BaseModel):
    filename: str

@router.post("/document")
def summarize(request: SummarizeRequest, db: Session = Depends(get_db)):
    if not request.filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
    try:
        result = summarize_document(request.filename)
        record = SummaryHistory(
            filename=request.filename,
            summary=result["summary"]
        )
        db.add(record)
        db.commit()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_summary_history(db: Session = Depends(get_db)):
    records = db.query(SummaryHistory).order_by(SummaryHistory.created_at.desc()).limit(20).all()
    return [{"id": r.id, "filename": r.filename, "summary": r.summary[:200], "created_at": str(r.created_at)} for r in records]