# import os
# import requests
# import base64
# import json
# from pathlib import Path
# from pgpy import PGPKey, PGPMessage
# import pytest
# from dotenv import load_dotenv

# # --- Load environment variables ---
# load_dotenv()
# KEY_PATH = os.getenv("SERVER_PRIVATE_KEY_PATH")
# KEY_PASSPHRASE = os.getenv("SERVER_KEY_PASSPHRASE")
# IDENTITY = "Group_19"

# # --- Target groups ---
# # Including own group just to test.
# GROUPS = {
#     "Group_03": "http://10.11.12.13:5000",
#     "Group_04": "http://10.11.12.19:5000",
#     "Group_07": "http://10.11.12.14:5000",
#     "Group_08": "http://10.11.12.7:5000",
#     "Group_09": "http://10.11.12.10:5000",
#     "Group_14": "http://10.11.12.18:5000",
#     "Group_19": "http://server:5000",
#     "Group_20": "http://10.11.12.9:5000",
#     "Group_22": "http://10.11.12.8:5000",
#     "Group_24": "http://10.11.12.15:5000",
#     "Group_26": "http://10.11.12.12:5000",
# }

# # Identity Manager
# from server import app
# im = app.config["IDENTITY_MANAGER"]

# @pytest.mark.parametrize("group_name, base_url", GROUPS.items())
# def test_rmap_external_group(group_name, base_url):
#     print(f"Testing {group_name}...", end="", flush=True)
#     try:
#         # Step 1: initiate handshake
#         nonce_client = 12345678
#         msg1_plain = {"nonceClient": nonce_client, "identity": IDENTITY}
#         msg1 = {"payload": im.encrypt_for_server(msg1_plain)}
#         resp1 = requests.post(f"{base_url}/rmap-initiate", json=msg1)
#         assert resp1.status_code == 200

#         # Step 2: decrypt server response
#         armored = base64.b64decode(resp1.json()["payload"]).decode("utf-8")
#         pgp_msg = PGPMessage.from_blob(armored)
#         client_priv, _ = PGPKey.from_file(KEY_PATH)
#         with client_priv.unlock(KEY_PASSPHRASE):
#             decrypted = client_priv.decrypt(pgp_msg)
#         nonce_server = json.loads(decrypted.message)["nonceServer"]

#         # Step 3: request link
#         msg2_plain = {"nonceServer": nonce_server}
#         msg2 = {"payload": im.encrypt_for_server(msg2_plain)}
#         resp2 = requests.post(f"{base_url}/rmap-get-link", json=msg2)
#         assert resp2.status_code == 200
#         token = resp2.json()["result"]
#         link = f"/api/get-version/{token}"

#         # Step 4: fetch PDF
#         pdf_resp = requests.get(f"{base_url}{link}")
#         assert pdf_resp.status_code == 200
#         assert pdf_resp.headers["Content-Type"] == "application/pdf"

#         # Step 5: save PDF locally
#         out_path = Path("/app/storage/rmap_pdfs") / f"{group_name}_watermarked.pdf"
#         with open(out_path, "wb") as f:
#             f.write(pdf_resp.content)

#         print(" success")

#     except Exception as e:
#         print(" failed")
#         print(f"    Reason: {e}")
#         pytest.fail(f"RMAP test failed for {group_name}")