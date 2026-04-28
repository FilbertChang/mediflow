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
    db.refresh(record)  # ← harus di sini, sebelum apapun yang butuh record.id

    # Run alert engine
    alerts = analyze_extraction(result)
    for alert in alerts:
        db.add(Alert(
            extraction_id=record.id,
            severity=alert.severity,
            alert_type=alert.alert_type,
            message=alert.message,
        ))
    db.commit()

    # Auto compliance check
    compliance_result = None
    try:
        from app.services.compliance import run_compliance_check
        from app.models.models import ComplianceHistory
        compliance_result = run_compliance_check(result, db)
        db.add(ComplianceHistory(
            extraction_id=record.id,
            status=compliance_result.status,
            summary=compliance_result.summary,
            deviations_json=json.dumps(compliance_result.deviations),
            rules_checked=compliance_result.rules_checked,
            policy_docs_used=json.dumps(compliance_result.policy_docs_used),
        ))
        if compliance_result.status == "deviation":
            for dev in compliance_result.deviations:
                db.add(Alert(
                    extraction_id=record.id,
                    severity=dev.get("severity", "warning"),
                    alert_type="policy_violation",
                    message=f"[Policy] {dev.get('rule', '')}: {dev.get('detail', '')}",
                ))
        db.commit()
    except Exception:
        pass  # compliance check never crashes extraction

    # Dispatch notifications (fire-and-forget)
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
        "compliance": compliance_result.to_dict() if compliance_result else None,
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