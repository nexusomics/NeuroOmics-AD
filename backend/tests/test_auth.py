"""Tests: authentication & authorization."""
from __future__ import annotations


def test_register_login_me(client):
    r = client.post("/api/v1/auth/register", json={
        "email": "u1@test.org", "password": "password123", "full_name": "U One"})
    assert r.status_code == 201
    assert r.json()["email"] == "u1@test.org"

    r = client.post("/api/v1/auth/login", json={"email": "u1@test.org", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]

    r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == "u1@test.org"

    r = client.post("/api/v1/auth/login", json={"email": "u1@test.org", "password": "wrong-pass"})
    assert r.status_code == 401


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@test.org", "password": "password123", "full_name": "Dup"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_refresh_token_flow(client):
    client.post("/api/v1/auth/register", json={"email": "rf@test.org", "password": "password123", "full_name": "RF"})
    login = client.post("/api/v1/auth/login", json={"email": "rf@test.org", "password": "password123"}).json()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]
    # bad refresh
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": "garbage"})
    assert r.status_code == 401


def test_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/projects").status_code == 401
    assert client.get("/api/v1/analyses?project_id=x").status_code == 401


def test_change_password(client, auth_headers):
    r = client.post("/api/v1/auth/me/change-password", headers=auth_headers,
                    json={"old_password": "password123", "new_password": "newpassword456"})
    assert r.status_code == 200
    r = client.post("/api/v1/auth/login", json={"email": "researcher@test.org", "password": "newpassword456"})
    assert r.status_code == 200


def test_admin_rbac(client, auth_headers, admin_headers):
    # non-admin forbidden
    assert client.get("/api/v1/admin/users", headers=auth_headers).status_code == 403
    assert client.get("/api/v1/admin/stats", headers=auth_headers).status_code == 403
    # admin allowed
    assert client.get("/api/v1/admin/users", headers=admin_headers).status_code == 200
    stats = client.get("/api/v1/admin/stats", headers=admin_headers).json()
    assert "users" in stats and "projects" in stats
