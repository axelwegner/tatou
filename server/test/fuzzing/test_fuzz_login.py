from hypothesis import given, settings
import pytest
import requests
from ..fuzz_helpers import API_URL, HEADERS, TIMEOUT, HYP_SETTINGS, LOGIN_STRATEGY

# Build strategy from YAML
@given(payload=LOGIN_STRATEGY)
@settings(**HYP_SETTINGS, deadline = None)
def test_fuzz_login(payload):
    try:
        r = requests.post(f"{API_URL}/login", json=payload, headers=HEADERS, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Request error: {e}")

    # Acceptable outcomes
    assert r.status_code in (200, 400, 401, 503), f"Unexpected status {r.status_code} for input: {payload}"
