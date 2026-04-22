from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.rag import ingest_document, chat_with_document
from app.database import get_db
from app.models.models import ChatHistory
from app.auth import get_current_user
from app.limiter import limiter

router = APIRouter(prefix="/rag", tags=["RAG Chat"])

class IngestRequest(BaseModel):
    filename: str

class ChatRequest(BaseModel):
    filename: str
    question: str

@router.post("/ingest")
@limiter.limit("20/minute")
def ingest(request: Request, data: IngestRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        result = ingest_document(data.filename, db=db)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
@limiter.limit("20/minute")
def chat(request: Request, data: ChatRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        result = chat_with_document(data.filename, data.question)
        record = ChatHistory(
            filename=data.filename,
            question=data.question,
            answer=result["answer"]
        )
        db.add(record)
        db.commit()
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history")
def get_chat_history(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    records = db.query(ChatHistory).order_by(
        ChatHistory.created_at.desc()
    ).limit(20).all()
    return [{"id": r.id, "filename": r.filename, "question": r.question, "answer": r.answer, "created_at": str(r.created_at)} for r in records]