from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.extractor import extract_clinical_data

router = APIRouter(prefix="/extract", tags=["Clinical Extraction"])

class NoteInput(BaseModel):
    note: str

@router.post("/clinical")
def extract_from_note(input: NoteInput):
    if not input.note.strip():
        raise HTTPException(status_code=400, detail="Note cannot be empty.")
    result = extract_clinical_data(input.note)
    return result