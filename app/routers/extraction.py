from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.extractor import extract_clinical_data
from app.services.alert_engine import analyze_extraction
from app.services.notifier import dispatch_alerts
from app.database import get_db
from app.models.models import ExtractionHistory, Alert
from app.auth import require_doctor_or_above
from app.limiter import limiter
import json
import asyncio

router = APIRouter(prefix="/extract", tags=["Clinical Extraction"])

class NoteInput(BaseModel):
    note: str

@router.post("/clinical")
@limiter.limit("10/minute")
def extract_from_note(
    request: Request,
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
    db.refresh(record)

    # Run alert engine
    alerts = analyze_extraction(result)

    # Persist alerts to DB
    for alert in alerts:
        db.add(Alert(
            extraction_id=record.id,
            severity=alert.severity,
            alert_type=alert.alert_type,
            message=alert.message,
        ))
    db.commit()

# Dispatch notifications (fire-and-forget, never blocks response)
    if alerts:
        patient_name = result.get("patient_name")
        import threading
        threading.Thread(
            target=lambda: asyncio.run(dispatch_alerts(alerts, record.id, patient_name)),
            daemon=True
        ).start()

    return {
        **result,
        "alerts": [a.to_dict() for a in alerts],
        "alert_count": len(alerts),
    }

@router.get("/history")
def get_history(
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    records = db.query(ExtractionHistory).order_by(
        ExtractionHistory.created_at.desc()
    ).limit(20).all()
    return [
        {
            "id": r.id,
            "note": r.note_input[:100],
            "result": json.loads(r.result_json),
            "created_at": str(r.created_at)
        }
        for r in records
    ]