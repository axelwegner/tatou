# PHASE 3 SPECIALIZATION - FUZZING, AXEL WEGNER

## API : /create-user
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-11)

## API: /login
### Bug #1: Malformed login payload causes 500
- **Input**: Various malformed inputs such as `{"email": "", "password": ""}, {"email": "user@example.com"}, 123, None, "not a dict", []`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `401 Unauthorized`
- **Root Cause**: Endpoint did not properly validate input before accessing keys or database, causing exceptions on invalid types or missing fields
- **Regression Test**: `test_login_invalid_inputs`
- **Status**: Fixed by validating payload type and required fields at the start of `/api/login` (Verified on 2025-10-13)

## API: /upload-document
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-12)

## API: /list-documents
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-12)

## API: /list-versions
### Bug #2: Non-positive document IDs cause 500
- **Input**: `'document_id = -1'` or `'document_id = 0'`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `404 Not Found`
- **Root Cause**: Negative or zero IDs bypasses validation and reaches DB query, which fails unhandled
- **Regression Test**: `test_list_versions_invalid_ids`
- **Status**: Fixed by adding a separate route that handles incorrect IDs (Verified on 2025-10-12)

## API: /list-all-versions
### Bug #3: Malformed header causes transport-layer crash
- **Input**: `headers={'\x80': ''}, headers={' ': ''}, headers={':': ''}`, etc.
- **Response**: `500 Internal Server Error` or uncaught transport exception
- **Expected**: `400 Bad Request` or clean rejection at transport boundary
- **Root Cause**: Non-ASCII or reserved characters in header names/values trigger UnicodeEncodeError or InvalidHeader before reaching route logic
- **Regression Test**: `test_list_all_versions_rejects_malformed_headers`
- **Status**: Fixed by adding header validation logic to `list_all_versions` handler (Verified on 2025-10-12)

## API: /get-document
### Bug #4: Zero, negative or malformed document id returns 401
- **Input**: `'document_id <= 0'` or `document_id = ""`, etc
- **Response**: `401 Unauthorized`
- **Expected**: `400 Bad Request`
- **Root Cause**: Handler lacks guard for malformed or non-positive ids
- **Regression Test**: `test_get_document_rejects_bad_ids`
- **Status**: Fixed by adding additional routes that catch these things  (Verified on 2025-10-15)

## API: /get-version
### Bug #5: Empty link path causes 500
- **Input**: `GET /api/get-version/` (with `link=""`)
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` (invalid link) or `404 Not Found`
- **Root Cause**: No explicit guard for empty links
- **Regression Test**: `test_get_version_rejects_empty_link`
- **Status**: Fixed by adding a separate route that handles empty links. (Verified on 2025-10-15)

### Bug #6: Traversal string causes 500 instead of clean rejection
- **Input**: `GET /api/get-version/../`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` (rejection of traversal)
- **Root Cause**: Traversal segments not normalized/rejected before DB/path resolution.
- **Regression Test**: `test_get_version_rejects_traversal`
- **Status**: - Fixed by adding validators.py that includes strict whitelist regex (^[A-Za-z0-9._-]{1,64}$). Normalized decoded link (collapse slashes, strip). Explicitly rejecting ".", "..", slashes, and backslashes. Added raw_uri_has_traversal to detect encoded traversal attempts. Main handler now calls is_invalid_link from validators.py before DB lookup. Introduced @app before_request reject_traversal_or_malformed to catch malformed URIs (.., //, %2e%2e, <, >, spaces). (Verified on 2025-10-16)

## API: /delete-document
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-16)

## API: /create-watermark
### Bug #7: Wrong doc_id causes 500 instead of clean rejection
- **Input**: `POST /api/create-watermark/1` with valid token, but token user does not own document id 1
- **Response**: `500 Internal Server Error`
- **Expected**: `401 Unauthorized` (if doc exists but not owned) or `404 Not Found` (if doc does not exist)
- **Root Cause**: Endpoint does not guard against ownership mismatch or missing doc before entering watermarking logic, leading to unhandled exception
- **Regression Test**: `test_create_watermark_wrong_docid`
- **Status**: Fixed by adding explicit ownership check before watermarking (Verified on 2025-10-16)

### Bug #8: Empty key or secret causes 500 instead of clean 400
- **Input**: POST `/api/create-watermark/<valid_doc_id>` with valid token and body but empty key or secret
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` with message like "key cannot be empty" or "invalid watermark input"
- **Root Cause**: Empty key and/or secret strings pass validation since only type checking is performed.
- **Regression Test**: `test_create_watermark_empty_key`
- **Status**: Fixed by adding explicit input validation for non-empty key and secret (Verified on 2025-10-16)

### Bug #9: Invalid key or secret causes 500 instead of clean 400
- **Input**: POST `/api/create-watermark/<valid_doc_id>` with valid token and body containing keys/secrets with invalid characters or too short/long values.
- **Response**: `500 Internal Server Error` (before fix)
- **Expected**: `400 Bad Request` with message like "invalid key or secret value"
- **Root Cause**: Placeholder strings passed basic type checks but failed deeper in watermark logic
- **Regression Test**: `test_create_watermark_null_key_secret`
- **Status**: Fixed by enforcing character and length checks inside create_watermark (Verified on 2025-10-17).

## API: /load_plugin
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-16)

## API: /get-watermarking-methods
- **Status**: Fuzzing not applicable — endpoint is read-only and accepts no external input. (Verified on 2025-10-16)

## API: /read-watermark
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-17)

## API: /rmap-initiate
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-17)

## API: /rmap-get-link
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-17)
