from hypothesis import given, settings
from ..fuzz_helpers import API_URL, HYP_SETTINGS, HEADERS, DELETE_DOCUMENT_STRATEGY, safe_request

@given(payload=DELETE_DOCUMENT_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_delete_document(payload):
    """
    Fuzzes /api/delete-document across path, query, and body variants.
    Covers malformed IDs, missing IDs, auth toggles, and extra headers.
    """
    base = f"{API_URL}/delete-document"

    # Default to DELETE; allow POST if body is used
    method = "DELETE"
    body = None

    # Construct URL and body depending on strategy
    if payload["use_path"]:
        url = f"{base}/{payload['doc_id']}"
    elif payload["use_query"]:
        url = f"{base}?{payload['query_key']}={payload['doc_id']}"
    elif payload["use_body"]:
        url = base
        method = "POST"  # body only makes sense with POST
        body = {"id": payload["doc_id"]}
    else:
        url = base

    # Build headers
    headers = {**payload["extra_headers"]}
    if payload["use_auth"]:
        headers.update(HEADERS)

    # Dispatch request
    r = safe_request(method, url, headers=headers, json=body)

    # Work out expected statuses
    expected = set()

    if not payload["use_auth"]:
        expected = {401}
    else:
        try:
            int(payload["doc_id"])
            # malformed query keys or conflicting params → 400 possible
            if payload["use_query"] and not payload["query_key"].isidentifier():
                expected = {200, 400, 401, 404}
            elif method in ("DELETE", "POST"):
                expected = {200, 401, 404}
            else:
                expected = {405}
        except (TypeError, ValueError):
            expected = {400}