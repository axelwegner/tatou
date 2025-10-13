import base64
import urllib.parse
import pytest
import requests
from hypothesis import given, settings, strategies as st

API_URL = "http://server:5000/api"
HEADERS = {"Authorization": "Bearer VALID_TEST_TOKEN"}

GET_DOC_PATH = f"{API_URL}/get-document"


def format_for_query(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        # base64 to keep it URL-safe
        return base64.b64encode(value).decode("ascii")
    s = str(value)
    # keep control chars and spaces safe for URLs
    return urllib.parse.quote_plus(s, safe='')


fuzz_ids = st.one_of(
    st.none(),
    st.integers(min_value=-(10 ** 12), max_value=10 ** 12),
    st.text(min_size=0, max_size=200),
    st.binary(min_size=0, max_size=200),
)

@given(document_id=fuzz_ids)
@settings(max_examples=200, deadline=None)
def test_fuzz_get_document(document_id):

    session = requests.Session()

    # 1) Query-param variant: /api/get-document?id=<...>
    if document_id is None:
        # call without any id to exercise the "no id provided" branch
        url = GET_DOC_PATH
    else:
        query_val = format_for_query(document_id)
        url = f"{GET_DOC_PATH}?id={query_val}"

    try:
        resp = session.get(url, headers=HEADERS, timeout=6)
    except Exception as e:
        pytest.skip(f"Connection error for {url}: {e}")
        return

    # No internal server errors allowed
    assert resp.status_code < 500, (
        f"5xx from server for query variant ({url}) - status {resp.status_code} - body: {resp.text[:300]}"
    )

    # 2) Path variant: only reasonable for integers
    if isinstance(document_id, int):
        url_path = f"{GET_DOC_PATH}/{document_id}"
        try:
            resp2 = session.get(url_path, headers=HEADERS, timeout=6)
        except Exception as e:
            pytest.skip(f"Connection error for {url_path}: {e}")
            return

        assert resp2.status_code < 500, (
            f"5xx from server for path variant ({url_path}) - status {resp2.status_code} - body: {resp2.text[:300]}"
        )

    # Optionally, note unexpected but non-5xx codes for inspection in test logs
    acceptable = {200, 400, 404, 410}
    if resp.status_code not in acceptable:
        print(f"Query variant returned unexpected status {resp.status_code} for {url}")

    if isinstance(document_id, int) and resp2.status_code not in acceptable:
        print(f"Path variant returned unexpected status {resp2.status_code} for {url_path}")


# Useful reproducible manual test for debugging
def test_manual_repro():
    """Manual quick-check: change the id to try special cases."""
    r = requests.get(f"{GET_DOC_PATH}?id=../../etc/passwd", headers=HEADERS, timeout=6)
    print("status:", r.status_code, "body preview:", r.text[:400])
