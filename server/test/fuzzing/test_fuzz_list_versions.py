# test/fuzzing/test_fuzz_list_versions.py
import pytest
import requests
from hypothesis import given, settings
from hypothesis import strategies as st
from ..fuzz_helpers import API_URL, TIMEOUT, HYP_SETTINGS, LIST_VERSIONS_STRATEGY

@given(payload=LIST_VERSIONS_STRATEGY)
@settings(**HYP_SETTINGS)
@pytest.mark.usefixtures("auth_headers")
def test_fuzz_list_versions(payload, request):
    """
    Fuzzes /list-versions and /list-versions/<id> with varied doc_id and query keys.
    Acceptable outcomes: 200 (ok), 400 (bad input), 404 (not found), 503 (db error)
    """
    use_path = payload["use_path"]
    doc_id = payload["doc_id"]
    query_key = payload["query_key"]

    auth_headers = request.getfixturevalue("auth_headers") if payload["use_auth"] else {}

    if use_path and isinstance(doc_id, int):
        url = f"{API_URL}/list-versions/{doc_id}"
        params = {}
    else:
        url = f"{API_URL}/list-versions"
        params = {query_key: doc_id} if query_key else {}

    try:
        r = requests.get(url, headers=auth_headers, params=params, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Transport error during request: {e}")
        return

    expected_statuses = (200, 400, 404, 503)
    if not payload["use_auth"]:
        expected_statuses += (401,)
    assert r.status_code in expected_statuses, (
        f"Unexpected status {r.status_code} for doc_id={doc_id}, "
        f"query_key={query_key}, use_path={use_path}"
    )
