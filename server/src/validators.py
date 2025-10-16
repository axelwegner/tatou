#THIS IS AN ATTEMPT AT FIXING TRAVERSAL ATTEMPTS- I HAVE NO IDEA WHAT I AM DOING.

import re
from urllib.parse import unquote

# Define exactly what a valid link is:
# - 1 to 64 characters
# - Only alphanumerics, dot, underscore, dash
_VALID_LINK_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

def is_invalid_link(link: str) -> bool:
    if not link:
        return True

    # Decode percent-encodings and strip whitespace
    decoded = unquote(link).strip()

    # Collapse multiple slashes, strip trailing slash
    decoded = re.sub(r"/+", "/", decoded).rstrip("/")

    # Reject anything with path semantics
    if decoded.startswith("/") or "/" in decoded or "\\" in decoded:
        return True
    if decoded in {".", ".."}:
        return True

    # Enforce whitelist
    return _VALID_LINK_RE.fullmatch(decoded) is None

def raw_uri_has_traversal(raw_uri: str) -> bool:
    """Return True if the raw URI contains encoded traversal attempts."""
    raw = (raw_uri or "").lower()
    return ("%2f" in raw) or ("%5c" in raw) or ("%2e%2e" in raw)

