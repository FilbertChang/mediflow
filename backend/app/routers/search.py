from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.services.search import semantic_search
from app.database import get_db

router = APIRouter(prefix="/search", tags=["Semantic Search"])

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

@router.post("/query")
def search(request: SearchRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
    try:
        results = semantic_search(request.query, request.top_k)
        return {"query": request.query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))