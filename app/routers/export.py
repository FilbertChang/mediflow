from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import ExtractionHistory, ChatHistory, SummaryHistory
import csv
import json
import io

router = APIRouter(prefix="/export", tags=["Export"])

@router.get("/extractions")
def export_extractions(db: Session = Depends(get_db)):
    records = db.query(ExtractionHistory).order_by(
        ExtractionHistory.created_at.desc()
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id", "patient_name", "age", "gender",
        "diagnosis", "medications", "icd10_codes",
        "symptoms", "notes", "created_at"
    ])

    for r in records:
        result = json.loads(r.result_json)
        writer.writerow([
            r.id,
            result.get("patient_name", ""),
            result.get("age", ""),
            result.get("gender", ""),
            ", ".join(result.get("diagnosis", []) or []),
            ", ".join(result.get("medications", []) or []),
            ", ".join(result.get("icd10_codes", []) or []),
            ", ".join(result.get("symptoms", []) or []),
            result.get("notes", ""),
            str(r.created_at)
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=extractions.csv"}
    )

@router.get("/chats")
def export_chats(db: Session = Depends(get_db)):
    records = db.query(ChatHistory).order_by(
        ChatHistory.created_at.desc()
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "filename", "question", "answer", "created_at"])

    for r in records:
        writer.writerow([r.id, r.filename, r.question, r.answer, str(r.created_at)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=chat_history.csv"}
    )

@router.get("/summaries")
def export_summaries(db: Session = Depends(get_db)):
    records = db.query(SummaryHistory).order_by(
        SummaryHistory.created_at.desc()
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "filename", "summary", "created_at"])

    for r in records:
        writer.writerow([r.id, r.filename, r.summary, str(r.created_at)])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=summaries.csv"}
    )