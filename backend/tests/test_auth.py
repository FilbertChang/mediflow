"""Tests for the authentication endpoints (/auth/*)."""
from app.models.models import User


def test_login_success(client, admin_user):
    res = client.post(
        "/auth/login",
        data={"username": "admin", "password": "Password123"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["username"] == "admin"
    assert body["role"] == "admin"


def test_login_wrong_password(client, admin_user):
    res = client.post(
        "/auth/login",
        data={"username": "admin", "password": "WrongPassword"},
    )
    assert res.status_code == 401


def test_login_unknown_user(client):
    res = client.post(
        "/auth/login",
        data={"username": "ghost", "password": "Password123"},
    )
    assert res.status_code == 401


def test_me_with_token(client, doctor_user, auth_header):
    res = client.get("/auth/me", headers=auth_header("doctor"))
    assert res.status_code == 200
    body = res.json()
    assert body["username"] == "doctor"
    assert body["role"] == "doctor"


def test_me_without_token(client):
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_register_as_admin(client, admin_user, auth_header, db_session):
    res = client.post(
        "/auth/register",
        json={"username": "newnurse", "password": "Password123", "role": "nurse"},
        headers=auth_header("admin"),
    )
    assert res.status_code == 200
    assert db_session.query(User).filter(User.username == "newnurse").first() is not None


def test_register_requires_admin(client, nurse_user, auth_header):
    res = client.post(
        "/auth/register",
        json={"username": "someone", "password": "Password123", "role": "nurse"},
        headers=auth_header("nurse"),
    )
    assert res.status_code == 403


def test_register_duplicate_username(client, admin_user, auth_header):
    res = client.post(
        "/auth/register",
        json={"username": "admin", "password": "Password123", "role": "doctor"},
        headers=auth_header("admin"),
    )
    assert res.status_code == 400


def test_register_invalid_role(client, admin_user, auth_header):
    res = client.post(
        "/auth/register",
        json={"username": "wizard", "password": "Password123", "role": "wizard"},
        headers=auth_header("admin"),
    )
    assert res.status_code == 400
