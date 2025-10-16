# fuzz_helpers.py
# Loads fuzzing config and builds Hypothesis strategies for each endpoint.
# Config file: server/fuzz-config.yaml

import yaml
import urllib.parse
import pytest
import requests
from pathlib import Path
from hypothesis import strategies as st
from hypothesis import assume
from src.validators import is_invalid_link



# --- Config loading ---

CONFIG_PATH = Path(__file__).resolve().parents[1] / "fuzz-config.yaml"

def load_config(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_shared_refs(config):
    shared = config.get("shared_components", {})
    for strategy_name, strategy in config.get("strategies", {}).items():
        for field, spec in strategy.items():
            if isinstance(spec, str) and spec.startswith("${shared_components."):
                key = spec[len("${shared_components."):-1]
                strategy[field] = shared.get(key, {})

_CONFIG = load_config()
resolve_shared_refs(_CONFIG)
API_URL = _CONFIG['target']['base_url']
HEADERS = _CONFIG['auth']['headers']
TIMEOUT = _CONFIG.get('parameters', {}).get('requests', {}).get('timeout_seconds', 6)
HYP_SETTINGS = _CONFIG.get('parameters', {}).get('hypothesis', {})

# --- Encoding helpers ---
# Ensure headers are transport-safe (Latin-1, printable, no control chars)
# Skip tests that would cause transport-layer exceptions. Those are not covered by fuzzing.
def is_transport_safe(headers: dict) -> bool:
    return all(
        isinstance(k, str) and isinstance(v, str) and
        is_header_safe(k) and is_header_safe(v)
        for k, v in headers.items()
    )

# When making requests, skip test cases that would cause transport-layer exceptions.
def safe_get(url, headers=None, timeout=TIMEOUT):
    if headers and not is_transport_safe(headers):
        assume(False)  # Skip this test case
    try:
        return requests.get(url, headers=headers, allow_redirects=False, timeout=timeout)
    except (UnicodeEncodeError, requests.exceptions.InvalidHeader):
        assume(False)
    except Exception as e:
        raise AssertionError(f"Unexpected transport error: {type(e).__name__} → {e}")
    
def safe_request(method, url, **kwargs):
    try:
        return requests.request(method, url, timeout=TIMEOUT, **kwargs)
    except Exception as e:
        class DummyResponse:
            status_code = 599
            text = str(e)
        return DummyResponse()


def _percent_encode(s: str) -> str:
    return urllib.parse.quote_plus(s, safe='')

def _bytes_from_sampled_token(tok: str) -> bytes:
    if not tok:
        return b""
    try:
        return tok.encode("utf-8").decode("unicode_escape").encode("latin-1")
    except Exception:
        return tok.encode("utf-8")

def is_header_safe(s: str) -> bool:
    """True if s is Latin-1 encodable, printable, and free of control chars or leading/trailing whitespace."""
    if not isinstance(s, str):
        return False
    if not s or s[0].isspace() or s[-1].isspace():
        return False
    try:
        s.encode("latin-1")
    except UnicodeEncodeError:
        return False
    return all(32 <= ord(c) <= 126 and c not in '\r\n' for c in s)


# --- Strategy builder ---
def build_strategy_from_spec(spec: dict):
    parts = []
    if "type" in spec:
        parts.append(_build_component_strategy(spec))
    for comp in spec.get("components", []):
        parts.append(_build_component_strategy(comp))
    if not parts:
        raise ValueError("Empty strategy spec: no 'type' or 'components'")
    return st.one_of(*parts)

def _build_component_strategy(comp: dict):
    t = comp.get("type")
    mn = comp.get("min_size", 0)
    mx = comp.get("max_size", 200)

    if t == "text":
        alph = comp.get("alphabet")
        if alph:
            whitelist = alph.get("whitelist_characters", "")
            safe_chars = [chr(c) for c in range(32, 127)
                        if chr(c) not in '\r\n#']  # exclude CR/LF and fragments
            for ch in whitelist:
                if ch not in safe_chars:
                    safe_chars.append(ch)
            strat = st.text(alphabet=safe_chars, min_size=mn, max_size=mx)
        else:
            # default: printable ASCII minus CR/LF and '#'
            safe_chars = [chr(c) for c in range(32, 127)
                        if chr(c) not in '\r\n#']
            strat = st.text(alphabet=safe_chars, min_size=mn, max_size=mx)

        # filter out pure whitespace, which collapses to empty after strip()
        return strat.filter(lambda s: s.strip() != "")


    elif t == "binary":
        return st.binary(min_size=mn, max_size=mx).map(lambda b: b.hex())

    elif t == "integer":
        return st.integers().map(str)

    elif t == "percent_encoded_text":
        return st.text(min_size=mn, max_size=mx).map(_percent_encode)

    elif t == "sampled_from":
        return st.sampled_from(comp.get("values", []))

    raise ValueError(f"Unknown component type: {t}")

# --- Endpoint-specific strategies ---

# /api/create-user
CREATE_USER_STRATEGY = st.fixed_dictionaries({
    "email": build_strategy_from_spec(_CONFIG['strategies']['create_user'].get("email", {})),
    "login": build_strategy_from_spec(_CONFIG['strategies']['create_user'].get("login", {})),
    "password": build_strategy_from_spec(_CONFIG['strategies']['create_user'].get("password", {})),
})

# /api/login
LOGIN_STRATEGY = st.fixed_dictionaries({
    "email": build_strategy_from_spec(_CONFIG['strategies']['login'].get("email", {})),
    "password": build_strategy_from_spec(_CONFIG['strategies']['login'].get("password", {})),
})

# /api/upload-document
UPLOAD_STRATEGY = st.fixed_dictionaries({
    "filename": build_strategy_from_spec(_CONFIG['strategies']['upload_document'].get("filename", {})),
    "content": build_strategy_from_spec(_CONFIG['strategies']['upload_document'].get("content", {})),
    "mime": st.sampled_from(_CONFIG['strategies']['upload_document'].get("mime", {}).get("values", ["application/pdf"])),
    "form_name": build_strategy_from_spec(_CONFIG['strategies']['upload_document'].get("form_name", {})),
    "extension": st.sampled_from(_CONFIG['strategies']['upload_document'].get("extension", {}).get("values", [".pdf"])),
    "magic_prefix": st.one_of(*[
        st.just(_bytes_from_sampled_token(m))
        for m in _CONFIG['strategies']['upload_document'].get("magic_prefix", {}).get("values", ["%PDF", "PK\x03\x04", "\x89PNG", ""])
    ]),
    "traversal": st.booleans(),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['upload_document']["use_auth"]),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['upload_document']["extra_headers"]),
})

# /api/list-documents
LIST_DOCUMENTS_STRATEGY = st.fixed_dictionaries({
    "token_prefix": build_strategy_from_spec(_CONFIG['strategies']['list_documents'].get("token_prefix", {})),
    "token_body": st.text
        (alphabet=[chr(c) for c in range(32, 127) if chr(c) not in '\r\n' and chr(c) not in ' \t'] + list("-._~"),
        min_size=0,
        max_size=128
    ),
    "use_real": build_strategy_from_spec(_CONFIG['strategies']['list_documents'].get("use_real", {})),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['list_documents']["use_auth"]),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['list_documents']["query_key"]),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['list_documents']["doc_id"]),

})

# /api/list-versions
LIST_VERSIONS_STRATEGY = st.fixed_dictionaries({
    "use_path": build_strategy_from_spec(_CONFIG['strategies']['list_versions']['use_path']),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['list_versions']['doc_id']),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['list_versions']['query_key']),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['list_versions']["use_auth"]),
})
# /api/list-all-versions
LIST_ALL_VERSIONS_STRATEGY = st.fixed_dictionaries({
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['list_all_versions']['extra_headers']),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['list_all_versions']["use_auth"]),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['list_all_versions']["query_key"]),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['list_all_versions']["doc_id"]),

})

# /api/get-document
GET_DOCUMENT_STRATEGY = st.fixed_dictionaries({
    "use_path": build_strategy_from_spec(_CONFIG['strategies']['get_document']['use_path']),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['get_document']['doc_id']),
    "query_id": build_strategy_from_spec(_CONFIG['strategies']['get_document']['query_id']),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['get_document']['query_key']),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['get_document']['use_auth']),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['get_document']["extra_headers"]),
})

# /api/get-version
GET_VERSION_STRATEGY = st.fixed_dictionaries({
    "link": build_strategy_from_spec(_CONFIG['strategies']['get_version']['link'])
              .filter(lambda s: not is_invalid_link(s)),
    "traversal": build_strategy_from_spec(_CONFIG['strategies']['get_version']['traversal']),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['get_version']['extra_headers']),
})

# /api/delete-document
DELETE_DOCUMENT_STRATEGY = st.fixed_dictionaries({
    "use_path": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("use_path", {})),
    "use_query": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("use_query", {})),
    "use_body": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("use_body", {})),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("doc_id", {})),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("query_key", {})),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("use_auth", {})),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['delete_document'].get("extra_headers", {})),
})

# /api/create_watermark
CREATE_WATERMARK_STRATEGY = st.fixed_dictionaries({
    "location": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("location", {})),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("doc_id", {})),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("query_key", {})),
    "method": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("method", {})),
    "intended_for": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("intended_for", {})),
    "position": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("position", {})),
    "secret": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("secret", {})),
    "key": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("key", {})),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("use_auth", {})),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['create_watermark'].get("extra_headers", {})),
})

# /api/load-plugin
LOAD_PLUGIN_STRATEGY = st.fixed_dictionaries({
    "filename": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("filename", {})),
    "file_bytes": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("file_bytes", {})),
    "overwrite": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("overwrite", {})),
    "extension": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("extension", {})),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("use_auth", {})),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['load_plugin'].get("extra_headers", {})),
})

# /api/read-watermark
READ_WATERMARK_STRATEGY = st.fixed_dictionaries({
    "location": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("location", {})),
    "doc_id": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("doc_id", {})),
    "query_key": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("query_key", {})),
    "method": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("method", {})),
    "position": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("position", {})),
    "key": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("key", {})),
    "use_auth": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("use_auth", {})),
    "extra_headers": build_strategy_from_spec(_CONFIG['strategies']['read_watermark'].get("extra_headers", {})),
})

# RMAP /api/rmap-initiate strategy
# Recursive JSON-like payload used safely in the rmap fuzzer
_json_leaf = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=512),
)
JSON_PAYLOAD = st.recursive(
    _json_leaf,
    lambda children: st.lists(children, max_size=6) | st.dictionaries(
        st.text(min_size=0, max_size=64), children, max_size=6
    ),
    max_leaves=50,
)

# Try to build use_auth / extra_headers from your _CONFIG if available, else fallback
try:
    _use_auth_spec = _CONFIG['strategies']['rmap_initiate'].get('use_auth', {})
    _headers_spec = _CONFIG['strategies']['rmap_initiate'].get('extra_headers', {})
    USE_AUTH_STRAT = build_strategy_from_spec(_use_auth_spec)
    EXTRA_HEADERS_STRAT = build_strategy_from_spec(_headers_spec)
except Exception:
    USE_AUTH_STRAT = st.booleans()
    EXTRA_HEADERS_STRAT = st.dictionaries(
        st.text(min_size=1, max_size=16),
        st.text(min_size=0, max_size=128),
        max_size=5
    )

RMAP_INITIATE_STRATEGY = st.fixed_dictionaries({
    # payload: arbitrary JSON-like structure (dict/list/primitives)
    "payload": JSON_PAYLOAD,
    # use_auth + extra_headers kept consistent with other strategies
    "use_auth": USE_AUTH_STRAT,
    "extra_headers": EXTRA_HEADERS_STRAT,
})

# RMAP /api/rmap-get-link strategy
# Recursive JSON-like leaf
_json_leaf = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=512),
)

# Recursive JSON for payload
JSON_PAYLOAD = st.recursive(
    _json_leaf,
    lambda children: st.lists(children, max_size=6) | st.dictionaries(
        st.text(min_size=0, max_size=64), children, max_size=6
    ),
    max_leaves=50,
)

# Try to use project _CONFIG if available, else fall back
try:
    _use_auth_spec = _CONFIG['strategies']['rmap_get_link'].get('use_auth', {})
    _headers_spec = _CONFIG['strategies']['rmap_get_link'].get('extra_headers', {})
    USE_AUTH_STRAT = build_strategy_from_spec(_use_auth_spec)
    EXTRA_HEADERS_STRAT = build_strategy_from_spec(_headers_spec)
except Exception:
    USE_AUTH_STRAT = st.booleans()
    EXTRA_HEADERS_STRAT = st.dictionaries(
        st.text(min_size=1, max_size=16),
        st.text(min_size=0, max_size=128),
        max_size=5
    )

RMAP_GET_LINK_STRATEGY = st.fixed_dictionaries({
    "payload": JSON_PAYLOAD,
    "use_auth": USE_AUTH_STRAT,
    "extra_headers": EXTRA_HEADERS_STRAT,
})
