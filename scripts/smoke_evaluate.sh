#!/usr/bin/env bash
# Smoke evaluate-step against local API (requires a valid access token).
# Usage: ACCESS_TOKEN=... ./scripts/smoke_evaluate.sh
set -euo pipefail
API="${API_URL:-http://localhost:8000}"
TOKEN="${ACCESS_TOKEN:?set ACCESS_TOKEN to a Supabase JWT}"

ITEM_ID="${ITEM_ID:-22222222-2222-2222-2222-222222222201}"

curl -sS -X POST "$API/api/v1/session/evaluate-step" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"item_id\":\"$ITEM_ID\",\"part_index\":1,\"answer\":{\"latex\":\"x = 7\"},\"hint_level\":0,\"scaffold_level\":2,\"latency_ms\":1200}" \
  | python -m json.tool

echo
curl -sS "$API/api/v1/session/due" -H "Authorization: Bearer $TOKEN" | python -m json.tool
