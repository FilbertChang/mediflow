from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_any_role, require_doctor_or_above
from app.models.models import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Badge count for the navbar — returns number of unread alerts."""
    count = db.query(Alert).filter(Alert.is_read == 0).count()
    return {"unread": count}


@router.get("/list")
def list_alerts(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Return recent alerts, newest first."""
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": a.id,
            "extraction_id": a.extraction_id,
            "severity": a.severity,
            "alert_type": a.alert_type,
            "message": a.message,
            "is_read": a.is_read,
            "created_at": str(a.created_at),
        }
        for a in alerts
    ]


@router.patch("/{alert_id}/read")
def mark_as_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Mark a single alert as read."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        alert.is_read = 1
        db.commit()
    return {"ok": True}


@router.patch("/mark-all-read")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Mark all alerts as read."""
    db.query(Alert).filter(Alert.is_read == 0).update({"is_read": 1})
    db.commit()
    return {"ok": True}


@router.delete("/{alert_id}")
def delete_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    """Delete a single alert (doctor and above)."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if alert:
        db.delete(alert)
        db.commit()
    return {"ok": True}