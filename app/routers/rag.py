from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.rag import ingest_document, chat_with_document
from app.database import get_db
from app.models.models import ChatHistory

router = APIRouter(prefix="/rag", tags=["RAG Chat"])

class IngestRequest(BaseModel):
    filename: str

class ChatRequest(BaseModel):
    filename: str
    question: str

@router.post("/ingest")
def ingest(request: IngestRequest, db: Session = Depends(get_db)):
    try:
        result = ingest_document(request.filename, db=db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        answer = chat_with_document(request.filename, request.question)
        record = ChatHistory(
            filename=request.filename,
            question=request.question,
            answer=answer
        )
        db.add(record)
        db.commit()
        return {"answer": answer}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_chat_history(db: Session = Depends(get_db)):
    records = db.query(ChatHistory).order_by(
        ChatHistory.created_at.desc()
    ).limit(20).all()
    return [{"id": r.id, "filename": r.filename, "question": r.question, "answer": r.answer, "created_at": str(r.created_at)} for r in records]