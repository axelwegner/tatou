# Server image: minimal Flask + Gunicorn
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates openssh-client \
 && rm -rf /var/lib/apt/lists/*

# Copy project description, to install dependencies
COPY pyproject.toml /app/pyproject.toml

# Install runtime dependencies
RUN pip install --no-cache-dir -e .

# --- Optional: install dev dependencies like pytest ---
# Uncomment this line during development/testing
RUN pip install --no-cache-dir -e .[dev]

# ------------------------------------------------------

# Copy sources after dependencies installation
COPY src /app/src
COPY flag /app/flag
COPY entrypoint.sh /app/entrypoint.sh

# For testing
COPY test /app/test


# Reinstall in editable mode (optional redundancy — can be removed if already done above)
RUN pip install --no-cache-dir -e .

RUN mkdir -p /app/logs

EXPOSE 5000

# Default command runs the web server
CMD ["./entrypoint.sh"]
