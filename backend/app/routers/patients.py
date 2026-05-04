from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Patient, PatientDocument, ExtractionHistory
from typing import Optional
import json

router = APIRouter(prefix="/patients", tags=["Patients"])

class PatientCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    notes: Optional[str] = None

class LinkDocument(BaseModel):
    patient_id: int
    filename: str

@router.post("/create")
def create_patient(data: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(
        name=data.name,
        age=data.age,
        gender=data.gender,
        notes=data.notes
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {"message": f"Patient '{data.name}' created.", "id": patient.id}

@router.get("/list")
def list_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).order_by(Patient.created_at.desc()).all()
    return [{"id": p.id, "name": p.name, "age": p.age, "gender": p.gender, "notes": p.notes, "created_at": str(p.created_at)} for p in patients]

@router.get("/{patient_id}")
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Get linked documents
    docs = db.query(PatientDocument).filter(
        PatientDocument.patient_id == patient_id
    ).all()
    filenames = [d.filename for d in docs]

    # Get extractions linked to those documents
    extractions = []
    for filename in filenames:
        records = db.query(ExtractionHistory).all()
        for r in records:
            result = json.loads(r.result_json)
            if result.get("patient_name", "").lower() in patient.name.lower():
                extractions.append({
                    "id": r.id,
                    "note": r.note_input[:100],
                    "result": result,
                    "created_at": str(r.created_at)
                })

    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "notes": patient.notes,
        "created_at": str(patient.created_at),
        "documents": filenames,
        "extractions": extractions[:10]
    }

@router.post("/link-document")
def link_document(data: LinkDocument, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")

    # Validate filename
    if ".." in data.filename or "/" in data.filename or "\\" in data.filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")

    existing = db.query(PatientDocument).filter(
        PatientDocument.patient_id == data.patient_id,
        PatientDocument.filename == data.filename
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Document already linked.")

    link = PatientDocument(patient_id=data.patient_id, filename=data.filename)
    db.add(link)
    db.commit()
    return {"message": f"'{data.filename}' linked to patient '{patient.name}'."}

@router.delete("/{patient_id}")
def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found.")
    db.query(PatientDocument).filter(PatientDocument.patient_id == patient_id).delete()
    db.delete(patient)
    db.commit()
    return {"message": f"Patient deleted."}