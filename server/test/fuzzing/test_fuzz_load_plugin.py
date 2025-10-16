# test/fuzzing/test_fuzz_load_plugin_safe.py
import os
import tempfile
from pathlib import Path
from hypothesis import given, settings
from ..fuzz_helpers import API_URL, HYP_SETTINGS, safe_request, HEADERS, LOAD_PLUGIN_STRATEGY

@given(payload=LOAD_PLUGIN_STRATEGY)
@settings(**HYP_SETTINGS)
def test_fuzz_load_plugin_safe(payload):
    """
    Fuzz /api/load-plugin safely using a temporary directory.

    - Writes payload['file_bytes'] to a temp STORAGE_DIR/files/plugins/<filename>.
    - Calls POST /api/load-plugin with {"filename": filename, "overwrite": overwrite}.
    - Asserts server returns reasonable responses:
        400 = bad filename/pickle
        401 = unauthenticated
        404 = file not found
        201 = success
        500/503 = server error
    """
    # Use a temporary STORAGE_DIR for fuzzing
    with tempfile.TemporaryDirectory() as tmp_storage_dir:
        storage_root = Path(tmp_storage_dir)
        plugins_dir = storage_root / "files" / "plugins"
        plugins_dir.mkdir(parents=True, exist_ok=True)

        filename = (payload.get("filename") or "").strip()
        overwrite = bool(payload.get("overwrite", False))
        file_bytes = payload.get("file_bytes") or b""
        use_auth = bool(payload.get("use_auth", True))
        extra_headers = payload.get("extra_headers", {}) or {}

        url = f"{API_URL}/load-plugin"
        body = {"filename": filename, "overwrite": overwrite}

        # Build headers
        headers = {}
        if use_auth:
            headers.update(HEADERS)
        headers.update(extra_headers)

        # If filename is empty -> expect 400 immediately
        if not filename:
            r = safe_request("POST", url, headers=headers, json=body)
            assert r.status_code in {400, 401}, (
                f"Unexpected {r.status_code} for missing filename payload={payload}"
            )
            return

        # Write plugin file into temp plugins directory
        plugin_path = plugins_dir / filename
        try:
            plugin_path.parent.mkdir(parents=True, exist_ok=True)
            plugin_path.write_bytes(file_bytes)
        except Exception:
            # If writing fails, server may return 404/500/503
            r = safe_request("POST", url, headers=headers, json=body)
            assert r.status_code in {400, 401, 404, 500, 503}, (
                f"Unexpected {r.status_code} after file write failure for payload={payload}"
            )
            return

        # Call the API
        r = safe_request("POST", url, headers=headers, json=body)

        # Allowed responses for fuzzing
        allowed = {400, 401, 404, 201, 500, 503}
        assert r.status_code in allowed, (
            f"Unexpected {r.status_code} for payload={payload}, "
            f"url={url}, body={body}, headers={headers}"
        )
