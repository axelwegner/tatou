#!/usr/bin/env bash

# --- Check for required key files ---
echo "Checking key files..."

if [ ! -f "$CLIENT_KEYS_DIR/Group_07.asc" ]; then
  echo "Missing public key at $CLIENT_KEYS_DIR/client_pub.asc"
  exit 1
fi

if [ ! -f "$SERVER_PUBLIC_KEY_PATH" ]; then
  echo "Missing server public key at $SERVER_PUBLIC_KEY_PATH"
  exit 1
fi

if [ ! -f "$SERVER_PRIVATE_KEY_PATH" ]; then
  echo "Missing server private key at $SERVER_PRIVATE_KEY_PATH"
  exit 1
fi

echo "All key files found."


# --- Check FLAG_1 ---
if [[ -z "${FLAG_1:-}" ]]; then
  echo "WARNING: FLAG_1 is not set"
fi

# --- Replace placeholder in /flag ---
if [[ -f "/flag" ]]; then
  if grep -q "REPLACE_THIS_STRING_WITH_SERVER_FLAG" "/flag"; then
    #echo "Replacing placeholder in flag with $FLAG_1"
    echo "Replacing placeholder in flag with FLAG_1"
    sed -i "s/REPLACE_THIS_STRING_WITH_SERVER_FLAG/${FLAG_1}/g" /flag
  fi
else
  echo "WARNING: /flag not found, skipping"
fi

# --- Check FLAG_2 ---
if [[ -z "${FLAG_2:-}" ]]; then
  echo "WARNING: FLAG_2 is not set"
fi

# --- Replace placeholder in /app/flag ---
if [[ -f "/app/flag" ]]; then
  if grep -q "REPLACE_THIS_STRING_WITH_SERVER_FLAG" "/app/flag"; then
    #echo "Replacing placeholder in flag with $FLAG_2"
    echo "Replacing placeholder in flag with FLAG_2"
    sed -i "s/REPLACE_THIS_STRING_WITH_SERVER_FLAG/${FLAG_2}/g" /app/flag
  fi
else
  echo "WARNING: /app/flag not found, skipping"
fi

# --- Start the server ---
echo "Starting server..."
exec gunicorn -b 0.0.0.0:5000 server:app