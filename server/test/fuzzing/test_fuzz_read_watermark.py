# test/fuzzing/test_fuzz_read_watermark_strict.py
from pathlib import Path
from hypothesis import given, settings
from ..fuzz_helpers import API_URL, HYP_SETTINGS, safe_request, HEADERS, READ_WATERMARK_STRATEGY

@given(payload=READ_WATERMARK_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_read_watermark(payload, uploaded_document, auth_headers):

    base = f"{API_URL}/read-watermark"
    method_http = "POST"
    body = {
        "method": payload["method"],
        "position": payload["position"],
        "key": payload["key"],
    }

    KNOWN_DOC_ID = uploaded_document["id"]
    loc = payload["location"]

    # Construct URL & inject doc_id
    url = base
    if loc == "path":
        # Ensure path is a valid int string
        url = f"{base}/{payload['doc_id']}"
    elif loc == "query":
        url = f"{base}?{payload['query_key']}={payload['doc_id']}"
    elif loc == "body":
        body["id"] = payload["doc_id"]

    # Build headers
    headers = {**payload.get("extra_headers", {})}
    if payload.get("use_auth", True):
        headers.update(auth_headers)

    # Dispatch request
    r = safe_request(method_http, url, headers=headers, json=body)

    # Determine expected status codes
    if not payload.get("use_auth", True):
        # Strict: only 401 is allowed
        expected = {401}
    else:
        expected = set()

        # doc_id parsing
        loc_path_invalid = False
        if loc == "path":
            try:
                doc_id_int = int(payload["doc_id"])
            except (TypeError, ValueError):
                loc_path_invalid = True
                expected.add(405)  # Flask rejects invalid path int
        else:
            try:
                doc_id_int = int(payload["doc_id"])
            except (TypeError, ValueError):
                expected.add(400)

        if not loc_path_invalid:
            method_valid = isinstance(body.get("method"), str) and body["method"]
            key_valid = isinstance(body.get("key"), str) and body["key"]

            if loc != "path":
                # Any query/body invalid doc_id yields 400
                try:
                    _ = int(payload["doc_id"])
                except Exception:
                    expected.add(400)

            if loc != "path" and method_valid and key_valid and int(payload["doc_id"]) == KNOWN_DOC_ID:
                expected.update({201, 404, 410})
            elif method_valid and key_valid and int(payload["doc_id"]) == KNOWN_DOC_ID:
                # path location with valid int doc_id
                expected.update({201, 404, 410})
            else:
                # bad fields, empty method/key, unknown doc
                expected.update({400, 404, 410})
