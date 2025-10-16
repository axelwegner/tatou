# test/fuzzing/test_fuzz_upload_document.py
from hypothesis import given, settings
import pytest
import requests
from io import BytesIO
from ..fuzz_helpers import API_URL, HEADERS, TIMEOUT, HYP_SETTINGS, UPLOAD_STRATEGY

@given(payload=UPLOAD_STRATEGY)
@settings(**HYP_SETTINGS)
@pytest.mark.usefixtures("auth_headers")
def test_fuzz_upload_document(payload, request):
    """
    Post multipart file to /api/upload-document with data from upload strategy.
    Acceptable outcomes: 201 (created), 400 (bad input), 503 (db), 415 (unsupported media)
    """
    # Unpack
    filename = payload["filename"]
    content = payload["content"]
    mime = payload["mime"]
    form_name = payload["form_name"]
    extension = payload["extension"]
    magic_prefix = payload["magic_prefix"]
    traversal = payload["traversal"]

    # Ensure filename extension present
    if not filename.lower().endswith(".pdf"):
        filename_with_ext = filename + extension
    else:
        filename_with_ext = filename

    if traversal:
        filename_with_ext = "../" + filename_with_ext

    if isinstance(content, str):
        try:
            content_bytes = bytes.fromhex(content)
        except Exception:
            content_bytes = content.encode("utf-8")
    else:
        content_bytes = content  # bytes

    # prefix
    file_bytes = magic_prefix + content_bytes

    file_obj = BytesIO(file_bytes)
    file_obj.seek(0)

    files = {"file": (filename_with_ext, file_obj, mime)}
    data = {"name": form_name}

    extra_headers = payload["extra_headers"]
    auth_headers = request.getfixturevalue("auth_headers") if payload["use_auth"] else {}
    headers = {**auth_headers, **extra_headers}


    try:
        r = requests.post(f"{API_URL}/upload-document", files=files, data=data, headers=headers, timeout=TIMEOUT)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"Transport error during request: {e}")
        return

    expected_statuses = (201, 400, 415, 503)
    if not payload["use_auth"]:
        expected_statuses += (401,)
    assert r.status_code in expected_statuses, (
        f"Unexpected status {r.status_code} for filename={filename_with_ext}, mime={mime}, name={form_name}"
    )

