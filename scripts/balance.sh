#!/usr/bin/env bash
# Check Twelve Data provider balance on NEAR AI Agent Market
# Usage: ./scripts/balance.sh
# Requires: AGENT_API_KEY set in environment (source .env.local)

set -euo pipefail

: "${AGENT_API_KEY:?AGENT_API_KEY is not set. Run: source .env.local}"

curl -s "https://market.near.ai/v1/wallet/balance" \
  -H "Authorization: Bearer $AGENT_API_KEY" | jq .
