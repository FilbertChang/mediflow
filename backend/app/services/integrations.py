"""
MediFlow Integration Service
Handles Google Sheets, Power BI Push API, and Slack integrations.

Required env vars per integration:

Google Sheets:
  GOOGLE_SERVICE_ACCOUNT_JSON  — path to service account JSON file
  GOOGLE_SHEET_ID              — spreadsheet ID from URL

Power BI:
  POWERBI_PUSH_URL             — streaming dataset push URL from Power BI

Slack:
  SLACK_INTEGRATION_WEBHOOK    — incoming webhook URL for the target channel
"""

from __future__ import annotations
import os
import json
import logging
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
POWERBI_PUSH_URL = os.getenv("POWERBI_PUSH_URL", "")
SLACK_INTEGRATION_WEBHOOK = os.getenv("SLACK_INTEGRATION_WEBHOOK", "")


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extraction_to_flat(extraction_result: dict, extraction_id: int) -> dict:
    """Flatten extraction result into a single-row dict for Sheets / Power BI."""
    diagnosis = extraction_result.get("diagnosis") or []
    medications = extraction_result.get("medications") or []
    icd10 = extraction_result.get("icd10_codes") or []
    symptoms = extraction_result.get("symptoms") or []
    return {
        "extraction_id": extraction_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "patient_name": extraction_result.get("patient_name") or "",
        "age": extraction_result.get("age") or "",
        "gender": extraction_result.get("gender") or "",
        "diagnosis": ", ".join(diagnosis),
        "medications": ", ".join(medications),
        "icd10_codes": ", ".join(icd10),
        "symptoms": ", ".join(symptoms),
        "notes": extraction_result.get("notes") or "",
    }


# ─────────────────────────────────────────────
# Google Sheets
# ─────────────────────────────────────────────

def _get_google_access_token() -> str | None:
    """Get a short-lived access token using the service account JSON."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON or not os.path.exists(GOOGLE_SERVICE_ACCOUNT_JSON):
        logger.warning("Google service account JSON not found.")
        return None
    try:
        import google.oauth2.service_account as sa
        import google.auth.transport.requests as ga_requests

        credentials = sa.Credentials.from_service_account_file(
            GOOGLE_SERVICE_ACCOUNT_JSON,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        credentials.refresh(ga_requests.Request())
        return credentials.token
    except Exception as e:
        logger.error(f"Google auth error: {e}")
        return None


async def push_to_google_sheets(extraction_result: dict, extraction_id: int) -> bool:
    """Append a row to the configured Google Sheet."""
    if not GOOGLE_SHEET_ID:
        logger.warning("GOOGLE_SHEET_ID not configured — skipping Sheets push.")
        return False

    token = _get_google_access_token()
    if not token:
        return False

    row = _extraction_to_flat(extraction_result, extraction_id)
    # Append in column order matching the sheet header
    values = [[
        row["extraction_id"],
        row["timestamp"],
        row["patient_name"],
        row["age"],
        row["gender"],
        row["diagnosis"],
        row["medications"],
        row["icd10_codes"],
        row["symptoms"],
        row["notes"],
    ]]

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{GOOGLE_SHEET_ID}/values/Sheet1!A1:append"
    params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"values": values},
                params=params,
                timeout=10.0,
            )
            if res.status_code == 200:
                logger.info(f"Google Sheets: appended row for extraction #{extraction_id}")
                return True
            else:
                logger.error(f"Google Sheets error {res.status_code}: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Google Sheets push failed: {e}")
        return False


# ─────────────────────────────────────────────
# Power BI Push API
# ─────────────────────────────────────────────

async def push_to_powerbi(extraction_result: dict, extraction_id: int) -> bool:
    """Push a row to a Power BI streaming dataset."""
    if not POWERBI_PUSH_URL:
        logger.warning("POWERBI_PUSH_URL not configured — skipping Power BI push.")
        return False

    row = _extraction_to_flat(extraction_result, extraction_id)
    payload = [row]  # Power BI Push API expects an array of rows

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                POWERBI_PUSH_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10.0,
            )
            if res.status_code in (200, 201):
                logger.info(f"Power BI: pushed row for extraction #{extraction_id}")
                return True
            else:
                logger.error(f"Power BI error {res.status_code}: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Power BI push failed: {e}")
        return False


# ─────────────────────────────────────────────
# Slack Integration
# ─────────────────────────────────────────────

async def push_to_slack(extraction_result: dict, extraction_id: int, alert_count: int = 0) -> bool:
    """Post an extraction summary to a Slack channel."""
    if not SLACK_INTEGRATION_WEBHOOK:
        logger.warning("SLACK_INTEGRATION_WEBHOOK not configured — skipping Slack push.")
        return False

    patient = extraction_result.get("patient_name") or "Unknown"
    diagnosis = ", ".join(extraction_result.get("diagnosis") or []) or "—"
    medications = ", ".join(extraction_result.get("medications") or []) or "—"
    icd10 = ", ".join(extraction_result.get("icd10_codes") or []) or "—"
    alert_text = f"⚠️ {alert_count} alert(s) generated" if alert_count > 0 else "✅ No alerts"

    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚕️ MediFlow — New Extraction"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Extraction ID:*\n#{extraction_id}"},
                    {"type": "mrkdwn", "text": f"*Patient:*\n{patient}"},
                    {"type": "mrkdwn", "text": f"*Diagnosis:*\n{diagnosis}"},
                    {"type": "mrkdwn", "text": f"*ICD-10:*\n{icd10}"},
                    {"type": "mrkdwn", "text": f"*Medications:*\n{medications}"},
                    {"type": "mrkdwn", "text": f"*Alerts:*\n{alert_text}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"Sent from MediFlow · {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"}
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                SLACK_INTEGRATION_WEBHOOK,
                json=payload,
                timeout=10.0,
            )
            if res.status_code == 200:
                logger.info(f"Slack: posted extraction #{extraction_id}")
                return True
            else:
                logger.error(f"Slack error {res.status_code}: {res.text}")
                return False
    except Exception as e:
        logger.error(f"Slack push failed: {e}")
        return False


# ─────────────────────────────────────────────
# Master dispatcher
# ─────────────────────────────────────────────

async def dispatch_integrations(
    extraction_result: dict,
    extraction_id: int,
    alert_count: int = 0,
) -> dict:
    """
    Fire all configured integrations concurrently.
    Never raises — integration failures must not crash the extraction pipeline.
    Returns a dict of results for logging.
    """
    import asyncio
    results = {}
    tasks = []

    if GOOGLE_SHEET_ID and GOOGLE_SERVICE_ACCOUNT_JSON:
        tasks.append(("google_sheets", push_to_google_sheets(extraction_result, extraction_id)))
    if POWERBI_PUSH_URL:
        tasks.append(("powerbi", push_to_powerbi(extraction_result, extraction_id)))
    if SLACK_INTEGRATION_WEBHOOK:
        tasks.append(("slack", push_to_slack(extraction_result, extraction_id, alert_count)))

    if not tasks:
        return {}

    names, coros = zip(*tasks)
    outcomes = await asyncio.gather(*coros, return_exceptions=True)
    for name, outcome in zip(names, outcomes):
        results[name] = outcome if not isinstance(outcome, Exception) else False

    return results