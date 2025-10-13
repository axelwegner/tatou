# # Test for global DDoS protection by simulating multiple requests to the upload endpoint

# import pytest
# from server import app
# from io import BytesIO


# @pytest.fixture
# def client():
#     app.config["TESTING"] = True
#     with app.test_client() as client:
#         yield client

# @pytest.mark.parametrize("endpoint", [
#     "/api/upload-document"
# ])
# def test_rate_limit_exceeded(client, endpoint):
#     # Simulate 151 requests from the same IP
#     for i in range(151):
#         resp = client.post(endpoint, data={"file": (BytesIO(b"%PDF-1.4"), "test.pdf")}, content_type="multipart/form-data")
#         if i < 150:
#             assert resp.status_code != 429, f"Unexpected rate limit at request {i + 1}"
#         else:
#             assert resp.status_code == 429, "Expected rate limit to trigger on 151st request"