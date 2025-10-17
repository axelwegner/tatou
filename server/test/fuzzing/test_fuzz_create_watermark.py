from hypothesis import given, settings
from ..fuzz_helpers import (
    API_URL,
    HYP_SETTINGS,
    HEADERS,
    CREATE_WATERMARK_STRATEGY,
    safe_request,
)

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

    # Use the real doc id from the fixture
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

    # Helper: stricter validity check
    def is_valid_field(val: str) -> bool:
        return (
            isinstance(val, str)
            and val.strip()
            and val.lower() not in {"null", "none"}
        )

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
                and all(is_valid_field(body[f]) for f in ("method", "intended_for", "secret", "key"))
            ):
                expected = {201}
            else:
                # Otherwise: either bad fields or unknown doc
                expected = {400, 401, 404, 405, 410}

    # Assert: never accept 500/503
    assert r.status_code in expected, (
        f"Unexpected {r.status_code} for payload={payload}, "
        f"url={url}, body={body}, headers={headers}"
    )