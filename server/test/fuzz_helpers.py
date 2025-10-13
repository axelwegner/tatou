# tests/fuzz_helpers.py
import yaml
import urllib.parse
from pathlib import Path
from hypothesis import strategies as st

CONFIG_PATH = Path(__file__).resolve().parents[1] / "fuzz-config.yaml"

def load_config(path=CONFIG_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def _percent_encode(s: str) -> str:
    return urllib.parse.quote_plus(s, safe='')

def build_strategy_from_spec(spec: dict):
    """
    Build a Hypothesis strategy from a YAML strategy spec.
    """
    parts = []

    for comp in spec.get("components", []):
        t = comp.get("type")
        if t == "text":
            mn = comp.get("min_size", 0)
            mx = comp.get("max_size", 200)
            parts.append(st.text(min_size=mn, max_size=mx))
        elif t == "binary":
            mn = comp.get("min_size", 0)
            mx = comp.get("max_size", 64)
            parts.append(st.binary(min_size=mn, max_size=mx).map(lambda b: b.hex()))
        elif t == "integer":
            parts.append(st.integers().map(str))
        elif t == "percent_encoded_text":
            mn = comp.get("min_size", 0)
            mx = comp.get("max_size", 100)
            parts.append(st.text(min_size=mn, max_size=mx).map(_percent_encode))
        elif t == "sampled_from":
            parts.append(st.sampled_from(comp.get("values", [])))
        else:
            raise ValueError(f"Unknown component type: {t}")

    # Include explicitly sampled tokens if present
    sampled_tokens = spec.get("sampled_tokens", [])
    if sampled_tokens:
        parts.append(st.sampled_from(sampled_tokens))

    if not parts:
        return st.text(min_size=0, max_size=120)

    return st.one_of(*parts)

# Load once
_CONFIG = load_config()
API_URL = _CONFIG['target']['base_url']
HEADERS = _CONFIG['auth']['headers']
TIMEOUT = _CONFIG.get('parameters', {}).get('requests', {}).get('timeout_seconds', 6)
HYP_SETTINGS = _CONFIG.get('parameters', {}).get('hypothesis', {})

# Build endpoint strategies
LINK_STRATEGY = build_strategy_from_spec(_CONFIG['strategies']['link_strategy'])
DOCUMENT_ID_STRATEGY = build_strategy_from_spec(_CONFIG['strategies'].get('document_id_strategy', {}))

def build_create_user_strategy(spec):
    return st.fixed_dictionaries({
        "email": build_strategy_from_spec(spec.get("email", {})),
        "login": build_strategy_from_spec(spec.get("login", {})),
        "password": build_strategy_from_spec(spec.get("password", {})),
    })

CREATE_USER_STRATEGY = build_create_user_strategy(_CONFIG['strategies']['create_user'])

def build_login_strategy(spec):
    return st.fixed_dictionaries({
        "email": build_strategy_from_spec(spec.get("email", {})),
        "password": build_strategy_from_spec(spec.get("password", {}))
    })

LOGIN_STRATEGY = build_login_strategy(_CONFIG['strategies'].get('login_strategy', {}))

# --- Add near other builders in tests/fuzz_helpers.py ---

def _bytes_from_sampled_token(tok: str) -> bytes:
    # translate YAML token strings to bytes for magic_prefix
    if not tok:
        return b""
    # handle visible escapes like "\x89PNG" or "PK\x03\x04"
    try:
        # decode python-style escapes if any
        return tok.encode("utf-8").decode("unicode_escape").encode("latin-1")
    except Exception:
        return tok.encode("utf-8")

def build_upload_document_strategy(spec: dict):
    # filename
    fn_spec = spec.get("filename", {})
    fn_strat = build_strategy_from_spec(fn_spec)

    # content: YAML 'binary' spec isn't defined in same shape, but build_strategy_from_spec supports binary
    content_spec = spec.get("content", {})
    content_strat = build_strategy_from_spec(content_spec)

    # mime
    mime_values = spec.get("mime", {}).get("values")
    mime_strat = st.sampled_from(mime_values) if mime_values else st.sampled_from(["application/pdf"])

    # form_name
    form_name_strat = build_strategy_from_spec(spec.get("form_name", {}))

    # extension
    ext_values = spec.get("extension", {}).get("values")
    ext_strat = st.sampled_from(ext_values) if ext_values else st.sampled_from([".pdf"])

    # magic_prefix (map string tokens to bytes)
    magic_values = spec.get("magic_prefix", {}).get("values") or spec.get("magic_prefix", {}).get("sampled_tokens") or []
    if magic_values:
        magic_strats = [st.just(_bytes_from_sampled_token(m)) for m in magic_values]
        magic_strat = st.one_of(*magic_strats)
    else:
        magic_strat = st.sampled_from([b"", b"%PDF", b"PK\x03\x04", b"\x89PNG"])

    # traversal
    traversal_spec = spec.get("traversal", {})
    traversal_strat = st.one_of(st.just(True), st.just(False)) if not traversal_spec else build_strategy_from_spec(traversal_spec)

    # Compose into a fixed dict for clarity
    return st.fixed_dictionaries({
        "filename": fn_strat,
        "content": content_strat,
        "mime": mime_strat,
        "form_name": form_name_strat,
        "extension": ext_strat,
        "magic_prefix": magic_strat,
        "traversal": traversal_strat,
    })

# Build and expose the strategy
UPLOAD_STRATEGY = build_upload_document_strategy(_CONFIG['strategies'].get('upload_document', {}))
