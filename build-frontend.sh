#!/usr/bin/env bash
# Build the React frontend and place the production bundle next to the FastAPI
# server so it can be served from a single uvicorn process.
#
# Usage:
#   ./build-frontend.sh                 # default output: backend/frontend_build
#   FRONTEND_BUILD_DIR=/var/www/...     # override destination
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${FRONTEND_BUILD_DIR:-$ROOT_DIR/backend/frontend_build}"

echo "→ Installing frontend deps with yarn"
cd "$ROOT_DIR/frontend"
yarn install --frozen-lockfile

echo "→ Building React production bundle"
yarn build

echo "→ Syncing build/ to $DEST"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -r build/. "$DEST/"

echo "✓ Frontend built and copied to: $DEST"
