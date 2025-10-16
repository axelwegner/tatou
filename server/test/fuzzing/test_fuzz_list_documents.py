from hypothesis import given, settings
import pytest
import requests
from ..fuzz_helpers import API_URL, TIMEOUT, HYP_SETTINGS, LIST_DOCUMENTS_STRATEGY, safe_get

@given(payload=LIST_DOCUMENTS_STRATEGY)
@settings(**HYP_SETTINGS)
@pytest.mark.usefixtures("auth_headers")
def test_fuzz_list_documents(payload, request):
    """
    Fuzzes the /api/list-documents endpoint with varying Authorization headers.
    Tests both valid and malformed tokens depending on 'use_real'.
    """
    token_prefix = payload["token_prefix"]
    token_body = payload["token_body"]
    use_real = payload["use_real"]

    auth_headers = request.getfixturevalue("auth_headers") if payload["use_auth"] else {}

    if use_real:
        headers = auth_headers
    else:
        token = f"{token_prefix} {token_body}".strip()
        headers = {"Authorization": token} if token else {}

    query_key = payload["query_key"]
    doc_id = payload["doc_id"]
    url = f"{API_URL}/list-documents"
    if query_key and doc_id:
        url += f"?{query_key}={doc_id}"

    r = safe_get(url, headers=headers)

    assert r.status_code in (200, 400, 401, 503), (
        f"Unexpected status {r.status_code} for headers={headers}"
    )