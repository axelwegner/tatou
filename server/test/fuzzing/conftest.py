import io
import pytest
import requests
import uuid
from reportlab.pdfgen import canvas

API_URL = "http://server:5000/api"

@pytest.fixture(scope="session")
def user1():
    unique = uuid.uuid4().hex[:8]
    user = {
        "login": f"user1_{unique}",
        "password": "testpass123",
        "email": f"user1_{unique}@example.com"
    }
    requests.post(f"{API_URL}/create-user", json=user)
    return user

@pytest.fixture(scope="session")
def user2():
    unique = uuid.uuid4().hex[:8]
    user = {
        "login": f"user2_{unique}",
        "password": "testpass123",
        "email": f"user2_{unique}@example.com"
    }
    requests.post(f"{API_URL}/create-user", json=user)
    return user

@pytest.fixture(scope="session")
def auth_headers(user1):
    r = requests.post(f"{API_URL}/login", json={"email": user1["email"], "password": user1["password"]})
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="session")
def uploaded_document(auth_headers):
    # Create a real multi-page PDF using reportlab
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer)
    c.drawString(100, 750, "This is a test PDF.")
    c.showPage()
    c.drawString(100, 750, "Second page.")
    c.showPage()
    c.save()
    pdf_buffer.seek(0)

    files = {
        "file": ("test.pdf", pdf_buffer, "application/pdf"),
        "name": (None, "test.pdf")
    }
    r = requests.post(f"{API_URL}/upload-document", files=files, headers=auth_headers)
    assert r.status_code == 201
    return r.json()

@pytest.fixture(scope="session")
def watermarked_document(auth_headers, uploaded_document):
    import uuid
    unique = uuid.uuid4().hex[:8]
    watermark_payload = {
        "method": "axel",  # or another valid method
        "position": "top-left",
        "key": "testkey123",
        "secret": f"mysecret_{unique}",
        "intended_for": f"recipient_{unique}@example.com",
        "id": uploaded_document["id"]
    }
    r2 = requests.post(f"{API_URL}/create-watermark", json=watermark_payload, headers=auth_headers)
    assert r2.status_code in (200, 201)
    watermark_response = r2.json()
    # Download the watermarked PDF using the link
    link = watermark_response["link"]
    if link.startswith("http"):
        download_url = link
    else:
        download_url = f"{API_URL}/get-version/{link}"
    r3 = requests.get(download_url)
    assert r3.status_code == 200
    watermarked_pdf_bytes = r3.content

    result = uploaded_document.copy()
    result["watermark"] = watermark_payload
    result["watermark_response"] = watermark_response
    result["watermarked_pdf_bytes"] = watermarked_pdf_bytes
    return result
