from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_any_role
from app.models.models import ExtractionHistory
from collections import Counter
from datetime import datetime, timezone
import json

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _parse_extraction_rows(rows: list[ExtractionHistory]) -> tuple[list, list, list]:
    """
    Parse all extraction history rows and return flat lists of
    diagnoses, medications, and icd10_codes.
    Silently skips rows with malformed JSON.
    """
    all_diagnoses = []
    all_medications = []
    all_icd10 = []

    for row in rows:
        try:
            data = json.loads(row.result_json)
        except (json.JSONDecodeError, TypeError):
            continue

        diagnoses = data.get("diagnosis", [])
        if isinstance(diagnoses, list):
            all_diagnoses.extend([d.strip() for d in diagnoses if isinstance(d, str) and d.strip()])

        medications = data.get("medications", [])
        if isinstance(medications, list):
            all_medications.extend([m.strip() for m in medications if isinstance(m, str) and m.strip()])

        icd10 = data.get("icd10_codes", [])
        if isinstance(icd10, list):
            all_icd10.extend([c.strip() for c in icd10 if isinstance(c, str) and c.strip()])

    return all_diagnoses, all_medications, all_icd10


@router.get("/top-diagnoses")
def get_top_diagnoses(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Top N most common diagnoses across all extraction history."""
    rows = db.query(ExtractionHistory).all()
    all_diagnoses, _, _ = _parse_extraction_rows(rows)

    if not all_diagnoses:
        return {"labels": [], "values": []}

    counter = Counter(all_diagnoses)
    top = counter.most_common(limit)
    labels, values = zip(*top)
    return {"labels": list(labels), "values": list(values)}


@router.get("/top-medications")
def get_top_medications(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Top N most common medications across all extraction history."""
    rows = db.query(ExtractionHistory).all()
    _, all_medications, _ = _parse_extraction_rows(rows)

    if not all_medications:
        return {"labels": [], "values": []}

    counter = Counter(all_medications)
    top = counter.most_common(limit)
    labels, values = zip(*top)
    return {"labels": list(labels), "values": list(values)}


@router.get("/top-icd10")
def get_top_icd10(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """Top N most frequent ICD-10 codes across all extraction history."""
    rows = db.query(ExtractionHistory).all()
    _, _, all_icd10 = _parse_extraction_rows(rows)

    if not all_icd10:
        return {"labels": [], "values": []}

    counter = Counter(all_icd10)
    top = counter.most_common(limit)
    labels, values = zip(*top)
    return {"labels": list(labels), "values": list(values)}


@router.get("/extraction-volume")
def get_extraction_volume(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """
    Extraction count grouped by date (YYYY-MM-DD).
    Returns chronologically sorted labels and values for a line chart.
    """
    rows = db.query(ExtractionHistory.created_at).all()

    if not rows:
        return {"labels": [], "values": []}

    date_counter: Counter = Counter()
    for (created_at,) in rows:
        if created_at is None:
            continue
        # Normalize to date string regardless of timezone awareness
        if isinstance(created_at, datetime):
            date_str = created_at.astimezone(timezone.utc).strftime("%Y-%m-%d")
        else:
            date_str = str(created_at)[:10]
        date_counter[date_str] += 1

    sorted_dates = sorted(date_counter.items())
    labels, values = zip(*sorted_dates)
    return {"labels": list(labels), "values": list(values)}


@router.get("/summary")
def get_analytics_summary(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """
    High-level summary stats: total extractions, unique diagnoses,
    unique medications, unique ICD-10 codes.
    Used for the stat cards at the top of the Analytics page.
    """
    rows = db.query(ExtractionHistory).all()
    all_diagnoses, all_medications, all_icd10 = _parse_extraction_rows(rows)

    return {
        "total_extractions": len(rows),
        "unique_diagnoses": len(set(all_diagnoses)),
        "unique_medications": len(set(all_medications)),
        "unique_icd10_codes": len(set(all_icd10)),
    }