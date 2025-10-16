# test/fuzzing/test_fuzz_rmap_initiate.py
import json
from hypothesis import given, settings, strategies as st
from ..fuzz_helpers import API_URL, HYP_SETTINGS, safe_request

# Build a generic JSON-like strategy (strings, numbers, booleans, null, lists, dicts)
json_leaf = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=512),
)
JSON_VALUE = st.recursive(
    json_leaf,
    lambda children: st.lists(children, max_size=6) | st.dictionaries(st.text(min_size=0, max_size=64), children, max_size=6),
    max_leaves=50,
)

# Occasionally produce a missing 'payload' case as well
REQUEST_BODY = st.one_of(
    st.fixed_dictionaries({"payload": JSON_VALUE}),
    st.dictionaries(st.text(min_size=0, max_size=32), JSON_VALUE, max_size=6)  # possibly missing 'payload'
)

@given(body=REQUEST_BODY)
@settings(**HYP_SETTINGS)
def test_fuzz_rmap_initiate(body):
    """
    Fuzz /api/rmap-initiate by varying the 'payload' JSON.

    Expectations:
      - If request is missing 'payload' => server should return 400.
      - If request contains 'payload' => server should return 200 (success) or 400 (handler-level error).
      - Server must not return 500/503 (unhandled crash) — those are considered failures for fuzzing.
    """
    url = f"{API_URL}/rmap-initiate"

    # Dispatch request
    r = safe_request("POST", url, headers={}, json=body)

    # Never accept server crashes
    assert r.status_code not in {500, 503}, (
        f"Server error {r.status_code} for body={body!r}; response text: {r.text}"
    )

    # If no payload key, we expect a 400
    if "payload" not in body or body.get("payload") in (None, "", []):
        # server should indicate missing/invalid payload
        assert r.status_code == 400, f"Expected 400 for missing/empty payload; got {r.status_code}: {r.text}"
        return

    # Otherwise payload is present — either handler returns success (200) or returns an error (400).
    assert r.status_code in {200, 400}, (
        f"Unexpected {r.status_code} for payload present body={body!r}: {r.text}"
    )

    # If it's 200, response JSON should not contain an "error" key (the handler returns 200 only on success).
    if r.status_code == 200:
        try:
            j = r.json()
        except Exception:
            assert False, f"200 response not JSON for body={body!r}; raw: {r.text}"
        assert "error" not in j, f"200 response contained error field: {j}"
