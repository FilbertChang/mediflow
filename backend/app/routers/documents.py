from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
import aiofiles
import os
import magic
from app.auth import get_current_user, require_doctor_or_above

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}

# Map allowed MIME types to extensions
ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/csv": ".csv",
    "application/csv": ".csv",
    "application/vnd.ms-excel": ".xlsx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user)
):
    # Check extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed.")

    # Check file size
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size is 10MB.")

    # Check actual file content using magic bytes
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File content does not match allowed types. Detected: {mime_type}"
        )

    # Check extension matches actual content
    expected_ext = ALLOWED_MIME_TYPES[mime_type]
    if ext != expected_ext and not (ext == ".csv" and mime_type in ["text/plain", "text/csv", "application/csv"]):
        raise HTTPException(
            status_code=400,
            detail=f"File extension '{ext}' does not match actual content type '{mime_type}'."
        )

    # Check for existing file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    if os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"File '{file.filename}' already exists.")

    # Save file
    async with aiofiles.open(file_path, "wb") as out_file:
        await out_file.write(content)

    return {"message": f"'{file.filename}' uploaded successfully.", "path": file_path}

@router.get("/list")
def list_documents(current_user=Depends(get_current_user)):
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return {"files": [], "message": "No documents uploaded yet."}
    return {"files": files, "total": len(files)}

@router.delete("/delete/{filename}")
def delete_document(
    filename: str,
    current_user=Depends(require_doctor_or_above)
):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    os.remove(file_path)
    return {"message": f"'{filename}' deleted successfully."}