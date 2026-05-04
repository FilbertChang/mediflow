"""
MediFlow Notifier
Dispatches alerts via SendGrid email and optionally Slack.

Required env vars:
  SENDGRID_API_KEY     — SendGrid API key
  ALERT_EMAIL_FROM     — sender address (verified in SendGrid)
  ALERT_EMAIL_TO       — recipient address (doctor / admin)

Optional env vars:
  SLACK_WEBHOOK_URL    — if set, alerts are also posted to Slack
"""

from __future__ import annotations
import os
import json
import logging
import httpx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.alert_engine import AlertItem

logger = logging.getLogger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

SEVERITY_EMOJI = {
    "critical": "🚨",
    "warning": "⚠️",
    "info": "ℹ️",
}

SEVERITY_COLOR = {
    "critical": "#ff6b6b",
    "warning": "#f0a500",
    "info": "#00c9a7",
}


def _build_email_html(alerts: list["AlertItem"], extraction_id: int, patient_name: str | None) -> str:
    patient_label = patient_name or "Tidak diketahui"
    rows = ""
    for alert in alerts:
        emoji = SEVERITY_EMOJI.get(alert.severity, "")
        color = SEVERITY_COLOR.get(alert.severity, "#333")
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #eee">
            <span style="color:{color};font-weight:bold">{emoji} {alert.severity.upper()}</span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #eee;font-size:13px;color:#333">
            {alert.message}
          </td>
        </tr>
        """
    return f"""
    <div style="font-family:monospace;max-width:600px;margin:0 auto;background:#f9f9f9;padding:24px;border-radius:8px">
      <h2 style="color:#0a0e14;margin-bottom:4px">⚕️ MediFlow Clinical Alert</h2>
      <p style="color:#666;font-size:13px;margin-bottom:20px">
        Extraction ID: <strong>#{extraction_id}</strong> &nbsp;|&nbsp;
        Pasien: <strong>{patient_label}</strong>
      </p>
      <table style="width:100%;border-collapse:collapse;background:#fff;border-radius:6px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08)">
        <thead>
          <tr style="background:#0a0e14">
            <th style="padding:10px 12px;color:#00c9a7;text-align:left;font-size:11px;letter-spacing:1px">SEVERITY</th>
            <th style="padding:10px 12px;color:#00c9a7;text-align:left;font-size:11px;letter-spacing:1px">DETAIL</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="font-size:11px;color:#999;margin-top:20px">
        Pesan ini dikirim otomatis oleh MediFlow. Login ke dashboard untuk melihat detail dan menandai alert sebagai sudah ditinjau.
      </p>
    </div>
    """


def _build_slack_payload(alerts: list["AlertItem"], extraction_id: int, patient_name: str | None) -> dict:
    patient_label = patient_name or "Tidak diketahui"
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "⚕️ MediFlow Clinical Alert"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Extraction ID:* #{extraction_id}   |   *Pasien:* {patient_label}"
            }
        },
        {"type": "divider"},
    ]
    for alert in alerts:
        emoji = SEVERITY_EMOJI.get(alert.severity, "")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{emoji} {alert.severity.upper()}*\n{alert.message}"
            }
        })
    return {"blocks": blocks}


async def send_email_alert(alerts: list["AlertItem"], extraction_id: int, patient_name: str | None = None) -> bool:
    """Send alert digest via SendGrid. Returns True on success."""
    if not SENDGRID_API_KEY or not ALERT_EMAIL_FROM or not ALERT_EMAIL_TO:
        logger.warning("SendGrid not configured — skipping email alert.")
        return False

    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")
    subject = f"[MediFlow] {critical_count} Critical, {warning_count} Warning — Extraction #{extraction_id}"

    payload = {
        "personalizations": [{"to": [{"email": ALERT_EMAIL_TO}]}],
        "from": {"email": ALERT_EMAIL_FROM, "name": "MediFlow Alerts"},
        "subject": subject,
        "content": [
            {
                "type": "text/html",
                "value": _build_email_html(alerts, extraction_id, patient_name)
            }
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=10.0,
            )
            if response.status_code in (200, 202):
                logger.info(f"Alert email sent for extraction #{extraction_id}")
                return True
            else:
                logger.error(f"SendGrid error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Email send failed: {e}")
        return False


async def send_slack_alert(alerts: list["AlertItem"], extraction_id: int, patient_name: str | None = None) -> bool:
    """Send alert to Slack via webhook. Returns True on success."""
    if not SLACK_WEBHOOK_URL:
        return False

    payload = _build_slack_payload(alerts, extraction_id, patient_name)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                SLACK_WEBHOOK_URL,
                json=payload,
                timeout=10.0,
            )
            if response.status_code == 200:
                logger.info(f"Slack alert sent for extraction #{extraction_id}")
                return True
            else:
                logger.error(f"Slack webhook error {response.status_code}: {response.text}")
                return False
    except Exception as e:
        logger.error(f"Slack send failed: {e}")
        return False


async def dispatch_alerts(alerts: list["AlertItem"], extraction_id: int, patient_name: str | None = None) -> None:
    """
    Fire-and-forget dispatcher. Sends email + Slack (if configured).
    Never raises — notification failures must not break the extraction pipeline.
    """
    if not alerts:
        return
    try:
        await send_email_alert(alerts, extraction_id, patient_name)
    except Exception as e:
        logger.error(f"dispatch_alerts email error: {e}")
    try:
        await send_slack_alert(alerts, extraction_id, patient_name)
    except Exception as e:
        logger.error(f"dispatch_alerts slack error: {e}")