#!/usr/bin/env bash
# Start the checked-out LightRAG branch, rebuilding the WebUI when necessary.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBUI_DIR="$ROOT/lightrag_webui"
WEBUI_BUILD="$ROOT/lightrag/api/webui"
SERVER="$ROOT/.venv/bin/lightrag-server"

if [[ ! -x "$SERVER" ]]; then
  echo "Missing project environment: $SERVER" >&2
  echo "Run: uv sync --extra api" >&2
  exit 1
fi

if [[ ! -f "$WEBUI_BUILD/index.html" || ! -f "$WEBUI_BUILD/workspace.html" ]]; then
  if ! command -v bun >/dev/null 2>&1; then
    echo "Bun is required to build the WebUI. Install it with Homebrew:" >&2
    echo "  brew install bun" >&2
    exit 1
  fi

  if [[ ! -d "$WEBUI_DIR/node_modules/vite" \
    || ! -d "$WEBUI_DIR/node_modules/typescript" \
    || ! -d "$WEBUI_DIR/node_modules/mermaid" ]]; then
    echo "Installing WebUI dependencies with the configured npm mirror..."
    (
      cd "$WEBUI_DIR"
      bun install \
        --frozen-lockfile \
        --registry="${BUN_REGISTRY:-https://registry.npmmirror.com}"
    )
  fi

  echo "Building WebUI..."
  (
    cd "$WEBUI_DIR"
    bun run build
  )
fi

export PROMPT_DIR="${PROMPT_DIR:-$ROOT/prompts}"

echo "Starting LightRAG from $ROOT"
echo "WebUI: http://127.0.0.1:${PORT:-9621}/webui/"
echo "Swagger: http://127.0.0.1:${PORT:-9621}/docs"
exec "$SERVER" "$@"
