# test/test_rmap.py
# Test for the full RMAP handshake process including database verification
import base64
import json
import os
from pathlib import Path

import pytest
from pgpy import PGPKey, PGPMessage

# --- Setup once at module import ---
from server import app, get_engine

client = app.test_client()

CLIENT_PRIV_KEY = Path(__file__).parent / "testkey" / "GroupTest_priv.asc"
CLIENT_PASSPHRASE = "GroupTest"
IDENTITY = "GroupTest"
from sqlalchemy import text
from server import get_engine

def test_full_rmap_handshake():
    im = client.application.config["IDENTITY_MANAGER"]

    # --- Step 1: Client -> Server : Message 1 ---
    nonce_client = 12345678
    msg1_plain = {"nonceClient": nonce_client, "identity": IDENTITY}
    msg1 = {"payload": im.encrypt_for_server(msg1_plain)}

    resp1 = client.post("/api/rmap-initiate", json=msg1)
    print(">>> Response 1 status:", resp1.status_code)
    print(">>> Response 1 body:", resp1.get_data(as_text=True))
    assert resp1.status_code == 200
    resp1_json = resp1.get_json()

    pgp_bytes = base64.b64decode(resp1_json["payload"])
    pgp_msg = PGPMessage.from_blob(pgp_bytes)
    client_priv, _ = PGPKey.from_file(str(CLIENT_PRIV_KEY))
    with client_priv.unlock(CLIENT_PASSPHRASE):
        decrypted = client_priv.decrypt(pgp_msg)
    resp1_plain = json.loads(decrypted.message)
    nonce_server = int(resp1_plain["nonceServer"])

    # --- Step 2: Client -> Server : Message 2 ---
    msg2_plain = {"nonceServer": nonce_server}
    msg2 = {"payload": im.encrypt_for_server(msg2_plain)}

    resp2 = client.post("/api/rmap-get-link", json=msg2)
    print(">>> Response 2 status:", resp2.status_code)
    print(">>> Response 2 body:", resp2.get_data(as_text=True))
    assert resp2.status_code == 200, "Expected 200 OK from /rmap-get-link"
    resp2_json = resp2.get_json()
    token = resp2_json["result"]
    link = f"/api/get-version/{token}"
    print(">>> Link returned:", link)
    assert link.startswith("/api/get-version/")

    # --- Check that a new Version row exists in DB ---
    link_token = link.split("/")[-1]
    with get_engine().connect() as conn:
        row = conn.execute(
            text("""
                SELECT v.id, v.documentid, v.secret, d.name
                FROM Versions v
                JOIN Documents d ON v.documentid = d.id
                WHERE v.link = :link
            """),
            {"link": link_token},
        ).first()

    print(">>> DB row for link:", row)
    assert row is not None, "Expected a Versions row for the returned link"
    assert row.name == "Group_19"
    assert row.secret, "Secret should not be empty"