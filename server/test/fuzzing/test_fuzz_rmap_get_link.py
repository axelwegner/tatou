# test/fuzzing/test_fuzz_rmap_get_link.py
from hypothesis import given, settings
from ..fuzz_helpers import API_URL, HYP_SETTINGS, safe_request, RMAP_GET_LINK_STRATEGY

@given(payload=RMAP_GET_LINK_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_rmap_get_link(payload, auth_headers):
    """
    Fuzz /api/rmap-get-link endpoint with strict auth handling.

    payload fields:
      - payload: JSON payload for RMAP
      - use_auth: whether to include auth_headers
      - extra_headers: additional HTTP headers
    """

    url = f"{API_URL}/rmap-get-link"

    # Build headers
    headers = payload.get("extra_headers", {}).copy()
    if payload.get("use_auth", True):
        headers.update(auth_headers)

    # Wrap payload in the expected key
    request_json = {"payload": payload.get("payload")}

    # Dispatch request
    r = safe_request("POST", url, headers=headers, json=request_json)

    # Fail on unhandled server errors
    assert r.status_code not in {500, 503}, (
        f"Server error {r.status_code} for payload={payload!r}; response text: {r.text}"
    )

    # If payload is missing/empty => expect 400
    if not payload.get("payload"):
        assert r.status_code == 400, (
            f"Expected 400 for missing/empty payload; got {r.status_code}: {r.text}"
        )
        return

    # Otherwise payload is present — either handler returns 200 (success) or 400 (handler-level error)
    assert r.status_code in {200, 400}, (
        f"Unexpected {r.status_code} for payload present payload={payload!r}: {r.text}"
    )

    # If 200, response JSON should not contain "error"
    if r.status_code == 200:
        try:
            j = r.json()
        except Exception:
            assert False, f"200 response not JSON for payload={payload!r}; raw: {r.text}"
        assert "error" not in j, f"200 response contained error field: {j}"
