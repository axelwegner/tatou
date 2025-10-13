# test/fuzzing/test_fuzz_list_all_versions.py

import pytest
import requests
from hypothesis import given, strategies as st

API_URL = "http://server:5000/api"

@pytest.mark.usefixtures("auth_headers")
@given(extra_headers=st.dictionaries(
    keys=st.text(min_size=1, max_size=20),
    values=st.text(min_size=0, max_size=100),
    max_size=3
))
def test_fuzz_list_all_versions(extra_headers, request):
    auth_headers = request.getfixturevalue("auth_headers")
    headers = {**auth_headers, **extra_headers}

    try:
        r = requests.get(f"{API_URL}/list-all-versions", headers=headers)
    except (UnicodeEncodeError, requests.exceptions.InvalidHeader) as e:
        print(f"[FUZZ] Transport-layer exception for headers={repr(extra_headers)} → {type(e).__name__}: {e}")
        return  # Skip this input — already covered by regression
    except Exception as e:
        assert False, f"[FUZZ] Unexpected exception for headers={repr(extra_headers)} → {type(e).__name__}: {e}"

    assert r.status_code in (200, 503, 400), (
        f"[FUZZ] Unexpected status {r.status_code} with headers={repr(extra_headers)}"
    )

    if r.status_code == 200:
        body = r.json()
        assert "versions" in body, "[FUZZ] Missing 'versions' key in response"
        assert isinstance(body["versions"], list), "[FUZZ] 'versions' is not a list"
        for v in body["versions"]:
            assert isinstance(v, dict), "[FUZZ] Each version must be a dict"
            for key in ("id", "documentid", "link", "intended_for", "method"):
                assert key in v, f"[FUZZ] Missing key '{key}' in version entry"