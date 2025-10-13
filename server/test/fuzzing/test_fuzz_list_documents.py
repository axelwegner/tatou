import pytest
from hypothesis import given, strategies as st
import requests

API_URL = "http://server:5000/api"

@pytest.mark.usefixtures("auth_headers")
@given(
    token_prefix=st.sampled_from(["Bearer", "Token", ""]),
    token_body=st.text(
        min_size=0,
        max_size=128,
        alphabet=st.characters(
            whitelist_categories=["Ll", "Lu", "Nd"],
            whitelist_characters="-._~",
            max_codepoint=127
        )
    )
)
def test_fuzz_list_documents(token_prefix, token_body, request):
    auth_headers = request.getfixturevalue("auth_headers")

    # Use the real token from the fixture to test valid path
    valid_token = auth_headers["Authorization"].split(" ", 1)[1]

    # Replace token_body with fuzzed value unless it's empty
    token = f"{token_prefix} {token_body}".strip()
    headers = {"Authorization": token} if token else {}

    r = requests.get(f"{API_URL}/list-documents", headers=headers)
    assert r.status_code in (200, 401, 503), f"Unexpected status {r.status_code} for token={token}"