import pytest

# -----------------------------
# GET /api/get-version tests
# -----------------------------

def test_get_version_empty(client, auth_headers):
    """Covers the /api/get-version/ route with no link."""
    r = client.get("/api/get-version/", headers=auth_headers)
    assert r.status_code == 400
    body = r.get_json()
    assert isinstance(body, dict)
    assert "error" in body
    assert body["error"] == "invalid version link"


@pytest.mark.usefixtures("auth_headers", "watermarked_document")
def test_get_version(client, auth_headers, watermarked_document):
    """Test /api/get-version/<link> using an existing watermarked document."""

    # Use the link returned when the watermark was created
    link = watermarked_document["watermark_response"]["link"]

    # Construct full route (client.get only needs relative path)
    url = f"/api/get-version/{link}"

    # Hit the route
    r = client.get(url, headers=auth_headers)
    assert r.status_code == 200
    assert r.headers.get("Content-Type") == "application/pdf"
    assert r.data.startswith(b"%PDF")

    # Optional: check that content matches what the fixture downloaded
    assert r.data == watermarked_document["watermarked_pdf_bytes"]


# -----------------------------
# Traversal / malformed link tests
# -----------------------------
@pytest.mark.usefixtures("auth_headers", "watermarked_document")
@pytest.mark.parametrize("link", [
    "../secret.pdf",          # parent directory traversal
    "/absolute/path.pdf",     # absolute path
    "subdir/../../etc/passwd",
    "////etc/passwd",
    "",                       # empty should hit get_version_empty
])
def test_get_version_traversal(client, auth_headers, link):
    """Test that directory traversal and malformed links are blocked."""

    # Special case: empty link hits /api/get-version/
    url = f"/api/get-version/{link}" if link else "/api/get-version/"
    r = client.get(url, headers=auth_headers)
    
    # Should not leak files, must block
    assert r.status_code in (400, 404)
    if link == "":
        body = r.get_json()
        assert body["error"] == "invalid version link"
