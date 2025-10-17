# test/fuzzing/test_fuzz_create_watermark.py
import re
from hypothesis import given, settings
from ..fuzz_helpers import (
    API_URL,
    HYP_SETTINGS,
    CREATE_WATERMARK_STRATEGY,
    safe_request,
)

TOKEN_RE = re.compile(r"^[\w\-+=]+$")

def is_valid_token(val: str) -> bool:
    if not isinstance(val, str) or not val.strip():
        return False
    v = val.strip()
    if v.lower() in {"null", "none", "undefined"}:
        return False
    if not (3 <= len(v) <= 128):
        return False
    if not TOKEN_RE.fullmatch(v):
        return False
    return True

@given(payload=CREATE_WATERMARK_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_create_watermark(payload, uploaded_document, auth_headers):
    """
    Fuzzes /api/create-watermark across path, query, and body variants.
    Covers malformed IDs, missing IDs, auth toggles, and required JSON fields.
    Narrows expectations so valid inputs must succeed, invalid ones must fail.
    """
    base = f"{API_URL}/create-watermark"
    method = "POST"
    body = {
        "method": payload["method"],
        "intended_for": payload["intended_for"],
        "position": payload["position"],
        "secret": payload["secret"],
        "key": payload["key"],
    }

    KNOWN_DOC_ID = uploaded_document["id"]

    # Construct URL depending on location
    loc = payload["location"]
    if loc == "path":
        url = f"{base}/{payload['doc_id']}"
    elif loc == "query":
        url = f"{base}?{payload['query_key']}={payload['doc_id']}"
    elif loc == "body":
        url = base
        body["id"] = payload["doc_id"]
    else:
        url = base

    # Build headers
    headers = {**payload["extra_headers"]}
    if payload["use_auth"]:
        headers.update(auth_headers)

    r = safe_request(method, url, headers=headers, json=body)

    # Work out expected statuses
    if not payload["use_auth"]:
        expected = {401, 405}
    else:
        try:
            doc_id = int(payload["doc_id"])
        except (TypeError, ValueError):
            expected = {400}
        else:
            # Happy path: known doc_id + all required fields semantically valid
            if (
                doc_id == KNOWN_DOC_ID
                and isinstance(body["method"], str) and body["method"].strip()
                and isinstance(body["intended_for"], str) and body["intended_for"].strip() and len(body["intended_for"].strip()) <= 64
                and is_valid_token(body["secret"])
                and is_valid_token(body["key"])
            ):
                expected = {201}
            else:
                expected = {400, 401, 404, 405, 410}

    # Assert: never accept 500/503
    assert r.status_code in expected, (
        f"Unexpected {r.status_code} for payload={payload}, "
        f"url={url}, body={body}, headers={headers}"
    )