"""Tests for the RAG ingest / chat endpoints (/rag/*).

The vector-store ingest and LLM chat calls are mocked so the tests run
offline without Ollama or FAISS.
"""
import pytest
from unittest.mock import Mock
from app.models.models import ChatHistory

INGEST_RESULT = {
    "status": "added",
    "message": "'note.txt' ingested. 12 chunks from 2 section(s): ASSESSMENT, PLAN",
    "chunks": 12,
    "sections": ["ASSESSMENT", "PLAN"],
}

CHAT_RESULT = {
    "answer": "The patient was prescribed Amlodipine 5mg.",
    "sources": [{"file": "note.txt", "section": "MEDICATIONS"}],
}


def test_ingest_success(client, nurse_user, auth_header, monkeypatch):
    monkeypatch.setattr(
        "app.routers.rag.ingest_document", lambda *a, **k: dict(INGEST_RESULT)
    )
    res = client.post(
        "/rag/ingest",
        json={"filename": "note.txt"},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 200
    assert res.json()["status"] == "added"


def test_ingest_file_not_found(client, nurse_user, auth_header, monkeypatch):
    monkeypatch.setattr(
        "app.routers.rag.ingest_document",
        Mock(side_effect=FileNotFoundError("File 'note.txt' not found in uploads.")),
    )
    res = client.post(
        "/rag/ingest",
        json={"filename": "note.txt"},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 404


def test_chat_success(client, nurse_user, auth_header, db_session, monkeypatch):
    monkeypatch.setattr(
        "app.routers.rag.chat_with_document", lambda *a, **k: dict(CHAT_RESULT)
    )
    res = client.post(
        "/rag/chat",
        json={"filename": "note.txt", "question": "What was prescribed?"},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 200
    assert res.json()["answer"] == CHAT_RESULT["answer"]
    saved = db_session.query(ChatHistory).all()
    assert len(saved) == 1
    assert saved[0].answer == CHAT_RESULT["answer"]


def test_chat_file_not_found(client, nurse_user, auth_header, monkeypatch):
    monkeypatch.setattr(
        "app.routers.rag.chat_with_document",
        Mock(side_effect=FileNotFoundError("Document 'note.txt' has not been ingested yet.")),
    )
    res = client.post(
        "/rag/chat",
        json={"filename": "note.txt", "question": "What was prescribed?"},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 404


def test_rag_requires_auth(client):
    res = client.post("/rag/ingest", json={"filename": "note.txt"})
    assert res.status_code == 401
