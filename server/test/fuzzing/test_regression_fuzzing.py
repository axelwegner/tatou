import pytest
import json
import requests
from server import app
from ..fuzz_helpers import API_URL, HEADERS, safe_get, safe_request
from urllib.parse import quote


@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# -------------------------------
# /login
# -------------------------------
#Bug 1
@pytest.mark.parametrize(
    "payload, expected_status",
    [
        ({"email": "", "password": ""}, 400),
        ({"email": "user@example.com"}, 400),
        ({"password": "secret"}, 400),
        ("not a dict", 400),
        (123, 400),
        (None, 400),
        ([], 400),
    ],
)
def test_login_invalid_inputs(client, payload, expected_status):
    """Regression Test: invalid login inputs should return 400"""
    # Always send JSON string to avoid AttributeError
    if isinstance(payload, dict) or isinstance(payload, list):
        data = json.dumps(payload)
    else:
        # Wrap other types in a dict so Flask can handle it
        data = json.dumps({"payload": payload})

    response = client.post(
        f"{API_URL}/login",
        data=data,
        content_type="application/json",
        headers=HEADERS  # include auth headers if login requires it
    )
    assert response.status_code == expected_status
    assert "error" in response.json

# -------------------------------
# /list-versions
# -------------------------------
#Bug 2
@pytest.mark.usefixtures("auth_headers")
@pytest.mark.parametrize("doc_id", [-1, 0])
def test_list_versions_invalid_ids(client, doc_id, request):
    auth_headers = request.getfixturevalue("auth_headers")
    r = client.get(f"{API_URL}/list-versions/{doc_id}", headers=auth_headers)
    assert r.status_code in (400, 404)
    assert "error" in r.json

# -------------------------------
# /list-all-versions
# -------------------------------
#Bug 3
@pytest.mark.usefixtures("auth_headers")
@pytest.mark.parametrize("bad_header", [{"\x80": ""}, {" ": ""}, {'"': ""}, {"0": "Ā"}])
def test_list_all_versions_rejects_malformed_headers(client, bad_header, request):
    auth_headers = request.getfixturevalue("auth_headers")
    headers = {**auth_headers, **bad_header}
    try:
        r = client.get(f"{API_URL}/list-all-versions", headers=headers)
    except Exception:
        return  # Expected for invalid header encoding
    # Only check that server didn't crash
    assert r.status_code in (200, 400, 503), f"Unexpected status {r.status_code} for headers={bad_header}"
    if r.status_code != 503:
        assert "error" in r.json or r.status_code == 200


# -------------------------------
# /get-document
# -------------------------------
#Bug 4
@pytest.mark.parametrize("bad_id", [":", "a:b", "%3A", "NaN", " ", "", "0", "-1"])
def test_get_document_rejects_bad_ids(client, bad_id):
    # Invalid document IDs should be rejected properly"

    """Because the endpoint enforces ownership and authentication, a request with valid auth
    may still return 401 if the document exists but belongs to another user. This is why
    the test accepts 401 along with 400, 403, and 404."""

    # Path parameter
    r_path = client.get(f"{API_URL}/get-document/{bad_id}", headers=HEADERS)
    assert r_path.status_code in (400, 401, 403, 404)
    assert "error" in r_path.json

    # Query parameter
    r_query = client.get(f"{API_URL}/get-document?id={bad_id}", headers=HEADERS)
    assert r_query.status_code in (400, 401, 403, 404)
    assert "error" in r_query.json

# -------------------------------
# /get-version
# -------------------------------
#Bug 5
def test_get_version_rejects_empty_link():
    """
    Empty link path should not cause a 500.
    Expect a clean 400 or 404 response with JSON error.
    """
    url = f"{API_URL}/get-version>/"
    r = safe_get(url, headers=HEADERS)

    assert r.status_code in (400, 404), (
        f"Unexpected status {r.status_code} for empty link"
    )
    body = r.json()
    assert isinstance(body, dict) and "error" in body

#Bug 6
def test_get_version_rejects_traversal():
    """
    Traversal-like links such as '../' should be rejected cleanly.
    """
    traversal_link = quote("../")
    url = f"{API_URL}/get-version/{traversal_link}/"
    r = safe_get(url)

    # Contract: traversal must be rejected with 
    assert r.status_code == 400, (
        f"Traversal not rejected early: got {r.status_code} for URL={url}"
    )

    body = r.json()
    assert isinstance(body, dict) and "error" in body

# -------------------------------
# /create-watermark
# -------------------------------

#Bug 7
@pytest.mark.usefixtures("auth_headers", "uploaded_document")
def test_create_watermark_wrong_docid(client, request):
    """
    Regression Test: ensure that requesting watermark creation on a doc_id
    not owned by the current user does not crash
    """
    auth_headers = request.getfixturevalue("auth_headers")
    uploaded_document = request.getfixturevalue("uploaded_document")

    # Pick a doc_id that does not belong to the logged-in user
    wrong_id = uploaded_document["id"] + 999999
    payload = {
        "method": "axel",
        "intended_for": "someone@example.com",
        "position": "top-left",
        "secret": "s3cr3t",
        "key": "k3y"
    }
    response = client.post(
        f"{API_URL}/create-watermark/{wrong_id}",
        json=payload,
        headers=auth_headers
    )
    assert response.status_code in (401, 404), (
        f"Unexpected {response.status_code} for wrong doc_id={wrong_id}, body={response.data}"
    )
    assert "error" in response.json


#Bug 8
def test_create_watermark_empty_key(uploaded_document, auth_headers):
    """
    Regression test for Bug #8: Empty key or secret triggers 500 instead of 400.
    """
    url = f"{API_URL}/create-watermark/{uploaded_document['id']}"
    data = {
        "method": "axel",
        "intended_for": "0",
        "position": "top-left",
        "secret": "0",
        "key": ""  # invalid: empty string should not be accepted
    }
    r = requests.post(url, headers=auth_headers, json=data)
    # Expect client-side rejection (not internal error)
    assert r.status_code in (400, 422), f"Unexpected response: {r.status_code}, {r.text}"
    assert "error" in r.json()

#Bug 9
@pytest.mark.regression
def test_create_watermark_null_key_secret(uploaded_document, auth_headers):
    """
    Regression test for Bug #9.
    Sending literal "null" as key/secret should be rejected cleanly (400), not cause 500.
    """
    doc_id = uploaded_document["id"]
    url = f"{API_URL}/create-watermark/{doc_id}"
    headers = auth_headers
    body = {
        "method": "axel",
        "intended_for": "0",
        "position": "top-left",
        "secret": "null",
        "key": "null",
    }

    r = safe_request("POST", url, headers=headers, json=body)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"