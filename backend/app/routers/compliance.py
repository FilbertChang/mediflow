from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_admin, require_any_role, require_doctor_or_above
from app.models.models import PolicyDocument, PolicyRule, ComplianceHistory, ExtractionHistory
from app.services.compliance import ingest_policy_document, run_compliance_check
from app.services.rag import load_document
import json
import os
import shutil

router = APIRouter(prefix="/compliance", tags=["Compliance"])

POLICY_UPLOAD_DIR = "policy_uploads"
os.makedirs(POLICY_UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# ─────────────────────────────────────────────
# Policy Document endpoints (admin only)
# ─────────────────────────────────────────────

@router.post("/policy-documents/upload")
async def upload_policy_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Upload and ingest a hospital policy document."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    # Path traversal protection
    safe_filename = os.path.basename(file.filename)
    if ".." in safe_filename or "/" in safe_filename or "\\" in safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # Save to policy_uploads/
    file_path = os.path.join(POLICY_UPLOAD_DIR, safe_filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Load and ingest into policy vectorstore
    try:
        docs = load_document(file_path)
        char_count = sum(len(d.page_content) for d in docs)
        chunk_count = ingest_policy_document(safe_filename, docs)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Failed to ingest policy document: {str(e)}")

    # Upsert DB record
    existing = db.query(PolicyDocument).filter(PolicyDocument.filename == safe_filename).first()
    if existing:
        existing.title = title
        existing.description = description
        existing.chunk_count = chunk_count
        existing.char_count = char_count
        existing.uploaded_by = current_user.username
    else:
        db.add(PolicyDocument(
            filename=safe_filename,
            title=title,
            description=description,
            chunk_count=chunk_count,
            char_count=char_count,
            uploaded_by=current_user.username,
        ))
    db.commit()

    return {
        "message": f"Policy document '{title}' uploaded and ingested successfully.",
        "filename": safe_filename,
        "chunks": chunk_count,
    }


@router.get("/policy-documents/list")
def list_policy_documents(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """List all uploaded policy documents."""
    docs = db.query(PolicyDocument).order_by(PolicyDocument.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "title": d.title,
            "description": d.description,
            "chunk_count": d.chunk_count,
            "uploaded_by": d.uploaded_by,
            "created_at": str(d.created_at),
        }
        for d in docs
    ]


@router.delete("/policy-documents/{doc_id}")
def delete_policy_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Delete a policy document and its vectorstore."""
    doc = db.query(PolicyDocument).filter(PolicyDocument.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Policy document not found.")

    # Remove vectorstore
    vs_path = os.path.join("policy_vectorstore", doc.filename)
    if os.path.exists(vs_path):
        shutil.rmtree(vs_path)

    # Remove uploaded file
    file_path = os.path.join(POLICY_UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(doc)
    db.commit()
    return {"message": f"Policy document '{doc.title}' deleted."}


# ─────────────────────────────────────────────
# Policy Rules endpoints (admin only)
# ─────────────────────────────────────────────

class PolicyRuleCreate(BaseModel):
    title: str
    condition: str
    requirement: str
    severity: str = "warning"


@router.post("/rules/create")
def create_policy_rule(
    rule: PolicyRuleCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Create a manual policy rule."""
    if rule.severity not in ("critical", "warning"):
        raise HTTPException(status_code=400, detail="Severity must be 'critical' or 'warning'.")

    db.add(PolicyRule(
        title=rule.title,
        condition=rule.condition,
        requirement=rule.requirement,
        severity=rule.severity,
        created_by=current_user.username,
    ))
    db.commit()
    return {"message": f"Rule '{rule.title}' created successfully."}


@router.get("/rules/list")
def list_policy_rules(
    db: Session = Depends(get_db),
    current_user=Depends(require_any_role)
):
    """List all policy rules."""
    rules = db.query(PolicyRule).order_by(PolicyRule.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "condition": r.condition,
            "requirement": r.requirement,
            "severity": r.severity,
            "is_active": r.is_active,
            "created_by": r.created_by,
            "created_at": str(r.created_at),
        }
        for r in rules
    ]


@router.patch("/rules/{rule_id}/toggle")
def toggle_policy_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Toggle a policy rule active/inactive."""
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")
    rule.is_active = 0 if rule.is_active else 1
    db.commit()
    return {"message": f"Rule '{rule.title}' {'activated' if rule.is_active else 'deactivated'}.", "is_active": rule.is_active}


@router.delete("/rules/{rule_id}")
def delete_policy_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_admin)
):
    """Delete a policy rule."""
    rule = db.query(PolicyRule).filter(PolicyRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found.")
    db.delete(rule)
    db.commit()
    return {"message": f"Rule '{rule.title}' deleted."}


# ─────────────────────────────────────────────
# Compliance check endpoint
# ─────────────────────────────────────────────

class ComplianceCheckInput(BaseModel):
    extraction_id: int


@router.post("/check")
def check_compliance(
    input: ComplianceCheckInput,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    """
    Run compliance check on an existing extraction.
    Called manually or automatically after extraction.
    """
    record = db.query(ExtractionHistory).filter(
        ExtractionHistory.id == input.extraction_id
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Extraction not found.")

    extraction_result = json.loads(record.result_json)
    result = run_compliance_check(extraction_result, db)

    # Persist to compliance_history
    db.add(ComplianceHistory(
        extraction_id=input.extraction_id,
        status=result.status,
        summary=result.summary,
        deviations_json=json.dumps(result.deviations),
        rules_checked=result.rules_checked,
        policy_docs_used=json.dumps(result.policy_docs_used),
    ))

    # If deviation — also push to alerts table
    if result.status == "deviation" and result.deviations:
        from app.models.models import Alert
        for dev in result.deviations:
            db.add(Alert(
                extraction_id=input.extraction_id,
                severity=dev.get("severity", "warning"),
                alert_type="policy_violation",
                message=f"[Policy] {dev.get('rule', '')}: {dev.get('detail', '')}",
            ))

    db.commit()
    return result.to_dict()


@router.get("/history")
def get_compliance_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    current_user=Depends(require_doctor_or_above)
):
    """Get recent compliance check history."""
    records = db.query(ComplianceHistory).order_by(
        ComplianceHistory.created_at.desc()
    ).limit(limit).all()
    return [
        {
            "id": r.id,
            "extraction_id": r.extraction_id,
            "status": r.status,
            "summary": r.summary,
            "deviations": json.loads(r.deviations_json),
            "rules_checked": r.rules_checked,
            "policy_docs_used": json.loads(r.policy_docs_used),
            "created_at": str(r.created_at),
        }
        for r in records
    ]