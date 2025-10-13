import pytest
from hypothesis import given, strategies as st
import requests

API_URL = "http://server:5000/api"

@pytest.mark.usefixtures("auth_headers")
@given(
    use_path=st.booleans(),
    doc_id=st.one_of(
        st.integers(min_value=-1000, max_value=100000),
        st.text(min_size=0, max_size=16)
    ),
    query_key=st.sampled_from(["id", "documentid", ""])
)
def test_fuzz_list_versions(use_path, doc_id, query_key, request):
    auth_headers = request.getfixturevalue("auth_headers")

    if use_path and isinstance(doc_id, int):
        url = f"{API_URL}/list-versions/{doc_id}"
        params = {}
    else:
        url = f"{API_URL}/list-versions"
        params = {query_key: doc_id} if query_key else {}

    r = requests.get(url, headers=auth_headers, params=params)

    assert r.status_code in (200, 400, 404, 503), (
        f"Unexpected status {r.status_code} for doc_id={doc_id}, "
        f"query_key={query_key}, use_path={use_path}"
    )