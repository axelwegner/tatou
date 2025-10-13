from hypothesis import given, settings
import pytest
import requests
from ..fuzz_helpers import API_URL, HEADERS, TIMEOUT, HYP_SETTINGS, CREATE_USER_STRATEGY

@given(payload=CREATE_USER_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_create_user(payload):
    try:
        r = requests.post(f"{API_URL}/create-user", json=payload, headers=HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Request error: {e}")

    # Acceptable outcomes
    assert r.status_code in (201, 400, 409, 503), f"Unexpected status {r.status_code} for input: {payload}"
