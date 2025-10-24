import io
import uuid
from reportlab.pdfgen import canvas

def test_list_documents(auth_client):
    # Create and upload a PDF via the test client
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "This is a test PDF.")
    c.showPage()
    c.save()
    buf.seek(0)

    data = {
        "file": (buf, "test.pdf"),
        "name": "test.pdf"
    }
    resp = auth_client.post(
        "/api/upload-document",
        data=data,
        content_type="multipart/form-data",
    )
    assert resp.status_code == 201
    uploaded = resp.get_json()
    doc_id = uploaded["id"]

    # Owner can see their document metadata
    r = auth_client.get("/api/list-documents")
    assert r.status_code == 200
    docs = r.get_json()["documents"]

    assert any(d["id"] == doc_id for d in docs)
    found = next(d for d in docs if d["id"] == doc_id)
    assert found["name"] == "test.pdf"
    assert "creation" in found
    assert "sha256" in found
    assert "size" in found

    # Confidentiality check: another user should not see this document's metadata
    unique = uuid.uuid4().hex[:8]
    other_user = {
        "login": f"otheruser_{unique}",
        "password": "otherpass123",
        "email": f"otheruser_{unique}@example.com"
    }
    # create other user
    r_create = auth_client.post("/api/create-user", json=other_user)
    assert r_create.status_code == 201
    
    r_login = auth_client.post("/api/login", json={
        "email": other_user["email"],
        "password": other_user["password"]
    })
    assert r_login.status_code == 200
    other_token = r_login.get_json()["token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Other user should not see the document in their list
    r_other = auth_client.get("/api/list-documents", headers=other_headers)
    assert r_other.status_code == 200
    other_docs = r_other.get_json()["documents"]
    assert all(d["id"] != doc_id for d in other_docs), "Metadata leak: other user can see document info"
