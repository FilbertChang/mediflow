from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.routers import documents, extraction, rag, summarization, search
from app.database import engine
from app.models import models

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="MediFlow", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(rag.router)
app.include_router(summarization.router)
app.include_router(search.router)

@app.get("/")
def root():
    return FileResponse("static/index.html")