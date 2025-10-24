import requests
import pytest
import io
import uuid
from reportlab.pdfgen import canvas

API_URL = "http://server:5000/api"

def make_pdf_bytes():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "This is a test PDF.")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf

def create_user_and_login(client, prefix="user"):
    unique = uuid.uuid4().hex[:8]
    user = {
        "login": f"{prefix}_{unique}",
        "password": "testpass123",
        "email": f"{prefix}_{unique}@example.com"
    }
    r = client.post("/api/create-user", json=user)
    assert r.status_code in (200, 201)
    r = client.post("/api/login", json={"email": user["email"], "password": user["password"]})
    assert r.status_code == 200
    token = r.get_json().get("token")
    return user, token

def upload_document_with_token(client, token):
    buf = make_pdf_bytes()
    data = {"file": (buf, "test.pdf"), "name": "test.pdf"}
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/api/upload-document", data=data, headers=headers, content_type="multipart/form-data")
    assert resp.status_code == 201
    doc = resp.get_json()
    try:
        buf.close()
    except Exception:
        pass
    return doc

def test_delete_document_owner(client):
    owner, owner_token = create_user_and_login(client, "owner")
    uploaded = upload_document_with_token(client, owner_token)
    doc_id = uploaded["id"]

    headers = {"Authorization": f"Bearer {owner_token}"}
    r_path = client.delete(f"/api/delete-document/{doc_id}", headers=headers)
    assert r_path.status_code == 200
    resp_json = r_path.get_json()
    assert resp_json.get("deleted") is True
    assert str(resp_json.get("id")) == str(doc_id)

    r_check = client.get(f"/api/get-document/{doc_id}", headers=headers)
    assert r_check.status_code == 404

def test_delete_document_other_user_forbidden(client):
    # owner uploads
    owner, owner_token = create_user_and_login(client, "owner")
    uploaded = upload_document_with_token(client, owner_token)
    doc_id = uploaded["id"]

    # other user
    other, other_token = create_user_and_login(client, "other")
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # other user attempts to delete owner's document
    r = client.delete(f"/api/delete-document/{doc_id}", headers=other_headers)
    assert r.status_code in (401, 403, 404)