import pytest
import uuid

@pytest.mark.usefixtures("auth_headers", "watermarked_document")
def test_read_watermark(client, auth_headers, watermarked_document):
    """Test that owner can read watermark and others cannot."""

    payload = watermarked_document["watermark"]
    doc_id = watermarked_document["id"]

    # Owner retrieves the secret using read-watermark
    read_payload = {
        "method": payload["method"],
        "key": payload["key"],
        "id": doc_id
    }
    r2 = client.post("/api/read-watermark", json=read_payload, headers=auth_headers)
    assert r2.status_code in (200, 201), f"Read watermark failed: {r2.status_code} {r2.data}"
    result = r2.get_json()
    assert result["secret"] == payload["secret"]
    assert result["method"] == payload["method"]

    # Another user should NOT be able to retrieve the secret
    other_unique = uuid.uuid4().hex[:8]
    other_user = {
        "login": f"otheruser_{other_unique}",
        "password": "otherpass123",
        "email": f"otheruser_{other_unique}@example.com"
    }

    # Create other user
    r_create = client.post("/api/create-user", json=other_user)
    assert r_create.status_code == 201

    # Login as other user
    r_login = client.post("/api/login", json={
        "email": other_user["email"],
        "password": other_user["password"]
    })
    assert r_login.status_code == 200
    other_token = r_login.get_json()["token"]
    other_headers = {"Authorization": f"Bearer {other_token}"}

    # Attempt to read watermark as other user
    r3 = client.post("/api/read-watermark", json=read_payload, headers=other_headers)
    # Should be forbidden or not found
    assert r3.status_code in (401, 403, 404), f"Metadata leak: {r3.status_code}, {r3.data}"
