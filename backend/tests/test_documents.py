"""Tests for the document upload / list / delete endpoints (/documents/*)."""
import pytest

TEXT_CONTENT = b"CHIEF COMPLAINT: chest pain.\nASSESSMENT: hypertension and diabetes.\n"


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    """Point the documents router at an isolated temp directory."""
    d = tmp_path / "uploads"
    d.mkdir()
    monkeypatch.setattr("app.routers.documents.UPLOAD_DIR", str(d))
    return d


def test_upload_valid_txt(client, nurse_user, auth_header, upload_dir):
    res = client.post(
        "/documents/upload",
        files={"file": ("note.txt", TEXT_CONTENT, "text/plain")},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 200
    assert (upload_dir / "note.txt").exists()


def test_upload_requires_auth(client, upload_dir):
    res = client.post(
        "/documents/upload",
        files={"file": ("note.txt", TEXT_CONTENT, "text/plain")},
    )
    assert res.status_code == 401


def test_upload_rejects_disallowed_extension(client, nurse_user, auth_header, upload_dir):
    res = client.post(
        "/documents/upload",
        files={"file": ("malware.exe", b"MZ\x90\x00binary", "application/octet-stream")},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 400


def test_upload_rejects_oversized_file(client, nurse_user, auth_header, upload_dir):
    oversized = b"a" * (10 * 1024 * 1024 + 1)
    res = client.post(
        "/documents/upload",
        files={"file": ("big.txt", oversized, "text/plain")},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 400


def test_upload_rejects_duplicate(client, nurse_user, auth_header, upload_dir):
    files = {"file": ("note.txt", TEXT_CONTENT, "text/plain")}
    first = client.post("/documents/upload", files=files, headers=auth_header("nurse"))
    assert first.status_code == 200
    second = client.post(
        "/documents/upload",
        files={"file": ("note.txt", TEXT_CONTENT, "text/plain")},
        headers=auth_header("nurse"),
    )
    assert second.status_code == 400


def test_list_documents(client, nurse_user, auth_header, upload_dir):
    (upload_dir / "existing.txt").write_text("data")
    res = client.get("/documents/list", headers=auth_header("nurse"))
    assert res.status_code == 200
    body = res.json()
    assert "existing.txt" in body["files"]
    assert body["total"] == 1


def test_delete_document(client, doctor_user, auth_header, upload_dir):
    (upload_dir / "remove.txt").write_text("data")
    res = client.delete("/documents/delete/remove.txt", headers=auth_header("doctor"))
    assert res.status_code == 200
    assert not (upload_dir / "remove.txt").exists()


def test_delete_missing_returns_404(client, doctor_user, auth_header, upload_dir):
    res = client.delete("/documents/delete/missing.txt", headers=auth_header("doctor"))
    assert res.status_code == 404


def test_delete_rejects_path_traversal(client, doctor_user, auth_header, upload_dir):
    # Any filename containing ".." must be rejected before touching the filesystem.
    res = client.delete("/documents/delete/note..txt", headers=auth_header("doctor"))
    assert res.status_code == 400
