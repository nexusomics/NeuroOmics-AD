"""Tests: projects & membership."""
from __future__ import annotations


def test_project_crud(client, auth_headers):
    # create
    r = client.post("/api/v1/projects", headers=auth_headers, json={
        "name": "CRUD project", "description": "d", "disease": "Alzheimer's disease"})
    assert r.status_code == 201
    pid = r.json()["id"]
    # list
    r = client.get("/api/v1/projects", headers=auth_headers)
    assert r.status_code == 200
    assert any(p["id"] == pid for p in r.json())
    # get
    r = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert r.status_code == 200 and r.json()["name"] == "CRUD project"
    # patch
    r = client.patch(f"/api/v1/projects/{pid}", headers=auth_headers, json={"description": "updated"})
    assert r.status_code == 200 and r.json()["description"] == "updated"
    # summary
    r = client.get(f"/api/v1/projects/{pid}/summary", headers=auth_headers)
    assert r.status_code == 200 and r.json()["analyses"] == 0


def test_project_access_control(client, auth_headers):
    pid = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Private"}).json()["id"]
    # second user cannot access
    client.post("/api/v1/auth/register", json={"email": "other@test.org", "password": "password123", "full_name": "Other"})
    other = client.post("/api/v1/auth/login", json={"email": "other@test.org", "password": "password123"}).json()["access_token"]
    r = client.get(f"/api/v1/projects/{pid}", headers={"Authorization": f"Bearer {other}"})
    assert r.status_code == 403
    r = client.get(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert r.status_code == 200


def test_membership(client, auth_headers):
    pid = client.post("/api/v1/projects", headers=auth_headers, json={"name": "Shared"}).json()["id"]
    client.post("/api/v1/auth/register", json={"email": "m1@test.org", "password": "password123", "full_name": "M1"})
    r = client.post(f"/api/v1/projects/{pid}/members", headers=auth_headers, json={"email": "m1@test.org", "role": "member"})
    assert r.status_code == 200
    r = client.get(f"/api/v1/projects/{pid}/members", headers=auth_headers)
    assert any(m["email"] == "m1@test.org" for m in r.json())


def test_delete_project(client, auth_headers):
    pid = client.post("/api/v1/projects", headers=auth_headers, json={"name": "ToDelete"}).json()["id"]
    r = client.delete(f"/api/v1/projects/{pid}", headers=auth_headers)
    assert r.status_code == 200
    assert client.get(f"/api/v1/projects/{pid}", headers=auth_headers).status_code == 404
