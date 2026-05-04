from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.summarizer import summarize_document
from app.database import get_db
from app.models.models import SummaryHistory
from app.auth import require_doctor_or_above
from app.limiter import limiter

router = APIRouter(prefix="/summarize", tags=["Summarization"])

class SummarizeRequest(BaseModel):
    filename: str

@router.post("/document")
@limiter.limit("10/minute")
def summarize(
    request: Request,
    data: SummarizeRequest,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    if not data.filename.strip():
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")
    try:
        result = summarize_document(data.filename)
        record = SummaryHistory(
            filename=data.filename,
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
def get_summary_history(db: Session = Depends(get_db), current_user=Depends(require_doctor_or_above)):
    records = db.query(SummaryHistory).order_by(
        SummaryHistory.created_at.desc()
    ).limit(20).all()
    return [{"id": r.id, "filename": r.filename, "summary": r.summary[:200], "created_at": str(r.created_at)} for r in records]