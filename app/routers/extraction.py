from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.extractor import extract_clinical_data
from app.database import get_db
from app.models.models import ExtractionHistory
from app.auth import require_doctor_or_above, get_current_user
import json

router = APIRouter(prefix="/extract", tags=["Clinical Extraction"])

class NoteInput(BaseModel):
    note: str

@router.post("/clinical")
def extract_from_note(
    input: NoteInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    if not input.note.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty.")
    result = extract_clinical_data(input.note)
    record = ExtractionHistory(
        note_input=input.note,
        result_json=json.dumps(result)
    )
    db.add(record)
    db.commit()
    return result

@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    records = db.query(ExtractionHistory).order_by(
        ExtractionHistory.created_at.desc()
    ).limit(20).all()
    return [{"id": r.id, "note": r.note_input[:100], "result": json.loads(r.result_json), "created_at": str(r.created_at)} for r in records]