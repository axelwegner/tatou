# PHASE 3 SPECIALIZATION - FUZZING, AXEL WEGNER

## API : /create-user
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-11)

## API: /login
### Bug #1: Malformed login payload causes 500
- **Input**: Various malformed inputs such as {"email": "", "password": ""}, {"email": "user@example.com"}, 123, None, "not a dict", []
- **Response**: `500 Internal Server Error`
- **Expected**: 400 Bad Request or 401 Unauthorized`
- **Root Cause**:Endpoint did not properly validate input before accessing keys or database, causing exceptions on invalid types or missing fields
- **Regression Test**: `test_login_invalid_inputs`
- **Status**: Fixed by validating payload type and required fields at the start of /api/login (Verified on 2025-10-13)

## API: /upload-document
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-12)

## API: /list-documents
- **Status**: No bugs discovered with fuzzing! (Verified on 2025-10-12)

## API: /list-versions
### Bug #1: Negative document ID causes 500
- **Input**: `'document_id = -1'`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `404 Not Found`
- **Root Cause**: Negative ID bypasses validation and reaches DB query, which fails unhandled
- **Regression Test**: `test_negative_document_id_does_not_crash`
- **Status**: Fixed by adding a separate route inside /list-versions that handles incorrect IDs (Verified on 2025-10-12)

### Bug #2: Document ID of 0 causes 500
- **Input**: `'document_id = 0'`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `404 Not Found`
- **Root Cause**: Zero-ID bypasses validation and reaches DB query, which fails unhandled
- **Regression Test**: `test_negative_document_id_does_not_crash`
- **Status**: Fixed by adding a separate route inside /list-versions that handles incorrect IDs (Verified on 2025-10-12)

## API: /list-all-versions
### Bug #3: Malformed header causes transport-layer crash
- **Input**: `headers={'\x80': ''}, headers={' ': ''}, headers={':': ''}, etc.`
- **Response**: `500 Internal Server Error or uncaught transport exception`
- **Expected**: `400 Bad Request or clean rejection at transport boundary`
- **Root Cause**: `Non-ASCII or reserved characters in header names/values trigger UnicodeEncodeError or InvalidHeader before reaching route logic`
- **Regression Test**: `test_list_all_versions_rejects_malformed_headers`
- **Status**: Fixed by adding header validation logic to list_all_versions handler (Verified on 2025-10-12)

## API: /get-document
### Bug #4: Negative document ID causes 500
- **Input**: `'document_id = -1'`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `404 Not Found`
- **Root Cause**: Negative ID bypasses validation and reaches DB query, which fails unhandled
- **Regression Test**: `test_negative_document_id_does_not_crash`
- **Status**: Fixed by adding a separate route inside /get-document that handles incorrect IDs (Verified on 2025-10-12)

### Bug #5: Document ID of 0 causes 500
- **Input**: `'document_id = 0'`
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` or `404 Not Found`
- **Root Cause**: Zero-ID bypasses validation and reaches DB query, which fails unhandled
- **Regression Test**: `test_negative_document_id_does_not_crash`
- **Status**: Fixed by adding a separate route inside /get-document that handles incorrect IDs (Verified on 2025-10-12)

### Bug #6: Empty path segment causes 500
- **Input**: `'/api/get-document/'` (trailing slash, no ID)
- **Response**: `500 Internal Server Error`
- **Expected**: `400 Bad Request` (missing or invalid document ID)
- **Root Cause**: Flask’s int: path converter fails to match an empty path segment, producing an unhandled routing error
- **Regression Test**: `test_get_document_rejects_bad_ids`
- **Status**: Fixed by adding an explicit /api/get-document/ route returning 400 Bad Request (Verified on 2025-10-12)