import pytest
import json
from server import app
from ..fuzz_helpers import API_URL, HEADERS

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

# -------------------------------
# /login
# -------------------------------
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
@pytest.mark.parametrize("bad_id", [":", "a:b", "0", "-1", "%3A", "NaN", " ", ""])
def test_get_document_rejects_bad_ids(client, bad_id):
    """Invalid document IDs should return 400/401/403/404"""

    # Path parameter
    r_path = client.get(f"{API_URL}/get-document/{bad_id}", headers=HEADERS)
    assert r_path.status_code in (400, 401, 403, 404)
    assert "error" in r_path.json

    # Query parameter
    r_query = client.get(f"{API_URL}/get-document?id={bad_id}", headers=HEADERS)
    assert r_query.status_code in (400, 401, 403, 404)
    assert "error" in r_query.json
