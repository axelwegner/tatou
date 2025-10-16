from hypothesis import given, settings
from ..fuzz_helpers import API_URL, TIMEOUT, HYP_SETTINGS, HEADERS, GET_DOCUMENT_STRATEGY, safe_get

@given(payload=GET_DOCUMENT_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_get_document(payload):
    """
    Fuzzes /api/get-document using both path and query variants.
    Covers malformed IDs, missing IDs, and edge-case query keys.
    """
    use_path = payload["use_path"]
    doc_id = payload["doc_id"]
    query_id = payload["query_id"]
    query_key = payload["query_key"]
    extra_headers = payload["extra_headers"]

    if use_path:
        url = f"{API_URL}/get-document/{doc_id}"
    else:
        url = f"{API_URL}/get-document?{query_key}={query_id}"
    
    auth_headers = HEADERS if payload["use_auth"] else {}
    headers = {**auth_headers, **extra_headers}

    r = safe_get(url, headers=headers)

#     expected_statuses = (200, 400, 404, 410, 500, 503)
#     if not payload["use_auth"]:
#         expected_statuses += (401,)
#     assert r.status_code in expected_statuses, (
#         f"Unexpected status {r.status_code} for URL={url}"
# )

    """ Because 401 can still happen if an authenticated user is trying to access a document they do not own I am allowing 401 unconditionally """

    expected_statuses = (200, 400, 404, 410, 500, 503, 401)

    assert r.status_code in expected_statuses, (
        f"Unexpected status {r.status_code} for URL={url}, headers={headers}"
    )