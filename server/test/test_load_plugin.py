# test/test_load_plugin_isolated.py
import dill
from pathlib import Path
from watermarking_method import WatermarkingMethod
import tempfile
import pytest
from server import create_app

@pytest.fixture
def isolated_client():
    """
    Returns a new Flask test client with its own temporary STORAGE_DIR.
    Does NOT touch the global app config.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_root = Path(tmpdir)

        # Create a fresh Flask app instance
        app = create_app()
        app.config["TESTING"] = True
        app.config["STORAGE_DIR"] = str(storage_root)

        with app.test_client() as client:
            yield client, storage_root
def test_load_plugin_endpoint(isolated_client, auth_headers):
    """
    Fully isolated /api/load-plugin test.
    Uses temporary storage, does NOT touch real documents.
    """
    client, storage_root = isolated_client

    plugins_dir = storage_root / "files" / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # 1Missing filename → 400
    r = client.post("/api/load-plugin", json={}, headers=auth_headers)
    assert r.status_code == 400
    assert "filename is required" in r.get_json()["error"]

    # 2File not found → 404
    r = client.post(
        "/api/load-plugin",
        json={"filename": "does_not_exist.pkl"},
        headers=auth_headers
    )
    assert r.status_code == 404
    assert "plugin file not found" in r.get_json()["error"]

    # 3Invalid pickle → 400
    bad_file = plugins_dir / "bad_plugin.pkl"
    bad_file.write_bytes(b"not a pickle")
    r = client.post(
        "/api/load-plugin",
        json={"filename": "bad_plugin.pkl"},
        headers=auth_headers
    )
    assert r.status_code == 400
    assert "failed to deserialize" in r.get_json()["error"]

    # 4Valid plugin → 201
    # Use a top-level DummyPlugin class
    class DummyPlugin(WatermarkingMethod):
        name = "DummyMethod"
        def add_watermark(self, pdf_bytes, secret, **kwargs): return pdf_bytes
        def read_secret(self, pdf_bytes, key): return "ok"
        def is_watermark_applicable(self, pdf_bytes, position=None): return True
        @staticmethod
        def get_usage(): return "test usage"

    valid_file = plugins_dir / "valid_plugin.pkl"
    # Use dill to serialize even local class definitions
    valid_file.write_bytes(dill.dumps(DummyPlugin))

    r = client.post(
        "/api/load-plugin",
        json={"filename": "valid_plugin.pkl"},
        headers=auth_headers
    )

    assert r.status_code == 201
    data = r.get_json()
    # Safe checks: loaded, filename, methods_count
    assert data.get("loaded") is True
    assert data.get("filename") == "valid_plugin.pkl"
    assert data.get("methods_count") == 4
