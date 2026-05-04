from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_doctor_or_above, require_admin
from app.models.models import ExtractionHistory
from app.services.integrations import (
    push_to_google_sheets,
    push_to_powerbi,
    push_to_slack,
    dispatch_integrations,
    GOOGLE_SHEET_ID,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    POWERBI_PUSH_URL,
    SLACK_INTEGRATION_WEBHOOK,
)
import json
import asyncio

router = APIRouter(prefix="/integrations", tags=["Integrations"])


@router.get("/status")
def get_integration_status(current_user=Depends(require_doctor_or_above)):
    """Return which integrations are configured."""
    return {
        "google_sheets": bool(GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON),
        "powerbi": bool(POWERBI_PUSH_URL),
        "slack": bool(SLACK_INTEGRATION_WEBHOOK),
    }


class ManualSyncInput(BaseModel):
    extraction_id: int
    targets: list[str]  # ["google_sheets", "powerbi", "slack"]


@router.post("/sync")
def manual_sync(
    input: ManualSyncInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    """Manually push a specific extraction to selected integrations."""
    record = db.query(ExtractionHistory).filter(
        ExtractionHistory.id == input.extraction_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    extraction_result = json.loads(record.result_json)
    results = {}

    async def _run():
        tasks = []
        if "google_sheets" in input.targets:
            tasks.append(("google_sheets", push_to_google_sheets(extraction_result, input.extraction_id)))
        if "powerbi" in input.targets:
            tasks.append(("powerbi", push_to_powerbi(extraction_result, input.extraction_id)))
        if "slack" in input.targets:
            tasks.append(("slack", push_to_slack(extraction_result, input.extraction_id)))

        if not tasks:
            return {}
        names, coros = zip(*tasks)
        outcomes = await asyncio.gather(*coros, return_exceptions=True)
        return {name: (outcome if not isinstance(outcome, Exception) else False)
                for name, outcome in zip(names, outcomes)}

    results = asyncio.run(_run())

    success = [k for k, v in results.items() if v]
    failed = [k for k, v in results.items() if not v]

    return {
        "extraction_id": input.extraction_id,
        "success": success,
        "failed": failed,
        "message": f"Synced to: {', '.join(success) or 'none'}. Failed: {', '.join(failed) or 'none'}."
    }


@router.post("/sync-all")
def sync_all_to_sheets(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """
    Bulk push last 100 extractions to all configured integrations.
    Admin only — use with caution.
    """
    records = db.query(ExtractionHistory).order_by(
        ExtractionHistory.created_at.desc()
    ).limit(100).all()

    if not records:
        return {"message": "No extractions found.", "pushed": 0}

    async def _run_all():
        tasks = [
            dispatch_integrations(json.loads(r.result_json), r.id)
            for r in records
        ]
        await asyncio.gather(*tasks, return_exceptions=True)

    asyncio.run(_run_all())
    return {"message": f"Bulk sync triggered for {len(records)} extractions.", "pushed": len(records)}