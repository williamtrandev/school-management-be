#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DEPLOY_DIR"

echo "Loading backend image..."
if [ ! -f "../backend-image.tar.gz" ]; then
  echo "backend-image.tar.gz not found in parent directory"
  exit 1
fi
docker load < ../backend-image.tar.gz

echo "Starting backend (no MongoDB restart)..."
docker compose up -d --no-deps web

echo "Waiting for backend to be ready..."
sleep 5
if curl -fsS http://localhost:8000/api/v1/events/public >/dev/null; then
  echo "Backend healthy."
else
  echo "Warning: health check failed (continuing)."
fi

echo "Done."


