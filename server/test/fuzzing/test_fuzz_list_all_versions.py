# test/fuzzing/test_fuzz_list_all_versions.py

import pytest
import requests
from hypothesis import given, settings
from ..fuzz_helpers import API_URL, TIMEOUT, HYP_SETTINGS, LIST_ALL_VERSIONS_STRATEGY

@given(payload=LIST_ALL_VERSIONS_STRATEGY)
@settings(**HYP_SETTINGS)
@pytest.mark.usefixtures("auth_headers")
def test_fuzz_list_all_versions(payload, request):
    extra_headers = payload["extra_headers"]
    auth_headers = request.getfixturevalue("auth_headers") if payload["use_auth"] else {}
    headers = {**auth_headers, **extra_headers}

    try:
        r = requests.get(f"{API_URL}/list-all-versions", headers=headers, timeout=TIMEOUT)
    except (UnicodeEncodeError, requests.exceptions.InvalidHeader) as e:
        print(f"[FUZZ] Transport-layer exception for headers={repr(extra_headers)} → {type(e).__name__}: {e}")
        return
    except Exception as e:
        assert False, f"[FUZZ] Unexpected exception for headers={repr(extra_headers)} → {type(e).__name__}: {e}"

    expected_statuses = (200, 503, 400)
    if not payload["use_auth"]:
        expected_statuses += (401,)
    assert r.status_code in expected_statuses, (
        f"[FUZZ] Unexpected status {r.status_code} with headers={repr(extra_headers)}"
)

    query_key = payload["query_key"]
    doc_id = payload["doc_id"]
    url = f"{API_URL}/list-all-versions"
    if query_key and doc_id:
        url += f"?{query_key}={doc_id}"
    r = requests.get(url, headers=headers, timeout=TIMEOUT)

    if r.status_code == 200:
        body = r.json()
        assert "versions" in body, "[FUZZ] Missing 'versions' key in response"
        assert isinstance(body["versions"], list), "[FUZZ] 'versions' is not a list"
        for v in body["versions"]:
            assert isinstance(v, dict), "[FUZZ] Each version must be a dict"
            for key in ("id", "documentid", "link", "intended_for", "method"):
                assert key in v, f"[FUZZ] Missing key '{key}' in version entry"