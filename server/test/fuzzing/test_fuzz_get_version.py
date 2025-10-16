from hypothesis import given, settings
from ..fuzz_helpers import API_URL, HYP_SETTINGS, GET_VERSION_STRATEGY, safe_get
from urllib.parse import quote

@given(payload=GET_VERSION_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_get_version(payload):
    """
    Fuzzes /api/get-version/<link>.
    Covers malformed links, traversal attempts, and header variations.
    Applies a refined assertion matrix so unexpected 200s or 500s are caught.
    """

    base_link = payload["link"]
    traversal = payload["traversal"]
    extra_headers = payload["extra_headers"]

    headers = {**extra_headers}

    if traversal:
        raw_candidates = [
            "../" + base_link,
            "..\\..\\" + base_link,
            "%2e%2e%2f" + base_link,
            "/etc/passwd",
            "C:\\Windows\\system32",
        ]
        for raw in raw_candidates:
            cand = quote(raw, safe="")  # encode everything so server sees the literal bytes
            url = f"{API_URL}/get-version/{cand}"
            r = safe_get(url, headers=headers)

            # traversal must be rejected by input validation (400)
            assert r.status_code == 400, (
                f"Unexpected status {r.status_code} for traversal URL={url}, headers={headers}"
            )
            body = r.json()
            assert isinstance(body, dict) and "error" in body
        return

    # Non-traversal case
    url = f"{API_URL}/get-version/{base_link}"
    r = safe_get(url, headers=headers)

    # Treat "." and ".." as invalid too
    if base_link in (".", ".."):
        assert r.status_code == 400
        body = r.json()
        assert isinstance(body, dict) and "error" in body
        return

    # Otherwise must be a valid link
    assert r.status_code in (200, 400, 404, 410)

    if r.status_code == 200:
        assert r.headers.get("Content-Type") == "application/pdf"
    else:
        assert r.headers.get("Content-Type", "").startswith("application/json")
        body = r.json()
        assert isinstance(body, dict) and "error" in body