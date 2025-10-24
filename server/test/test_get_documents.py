import requests
import pytest
import uuid

API_URL = "http://server:5000/api"

def test_get_document_owner_access(auth_client, uploaded_document):
 
    #Verifies owner can access document via both query and path params.
    doc_id = uploaded_document["id"]

    r_query = auth_client.get(f"/api/get-document?id={doc_id}")
    assert r_query.status_code == 200
    assert r_query.headers.get("Content-Type", "").startswith("application/pdf")
    assert len(r_query.data) > 0

    r_path = auth_client.get(f"/api/get-document/{doc_id}")
    assert r_path.status_code == 200
    assert r_path.headers.get("Content-Type", "").startswith("application/pdf")
    assert len(r_path.data) > 0


def test_get_document_other_user_restricted(client, uploaded_document):

    # Verifies that other users cannot access the owner's document.
    doc_id = uploaded_document["id"]

    unique = uuid.uuid4().hex[:8]
    other = {"login": f"other_{unique}", "password": "otherpass123", "email": f"other_{unique}@example.com"}
    r_create = client.post("/api/create-user", json=other)
    assert r_create.status_code in (200, 201)
    r_login = client.post("/api/login", json={"email": other["email"], "password": other["password"]})
    assert r_login.status_code == 200
    other_token = r_login.get_json().get("token")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    r = client.get(f"/api/get-document/{doc_id}", headers=other_headers)
    assert r.status_code in (401, 403, 404)


def test_get_document_watermark_owner(auth_client, uploaded_document):
    doc_id = uploaded_document["id"]
    r = auth_client.get(f"/api/get-document/{doc_id}")
    assert r.status_code == 200
    assert r.headers.get("Content-Type", "").startswith("application/pdf")
    assert len(r.data) > 0