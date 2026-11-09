#!/bin/bash
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting HomeOffice Assistant ..."
# Trust X-Forwarded-Proto/For only from these proxy addresses (comma-separated,
# or "*"). Set FORWARDED_ALLOW_IPS to the TLS proxy's address so the session
# cookie is marked secure behind it.
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 \
    --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-127.0.0.1}"
