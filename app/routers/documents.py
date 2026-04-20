from fastapi import APIRouter, UploadFile, File, HTTPException
import aiofiles
import os

router = APIRouter(prefix="/documents", tags=["Documents"])

UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv", ".xlsx"}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Check file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed.")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save file
    async with aiofiles.open(file_path, "wb") as out_file:
        content = await file.read()
        await out_file.write(content)

    return {"message": f"'{file.filename}' uploaded successfully.", "path": file_path}


@router.get("/list")
def list_documents():
    files = os.listdir(UPLOAD_DIR)
    if not files:
        return {"files": [], "message": "No documents uploaded yet."}
    return {"files": files, "total": len(files)}


@router.delete("/delete/{filename}")
def delete_document(filename: str):
    file_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    os.remove(file_path)
    return {"message": f"'{filename}' deleted successfully."}