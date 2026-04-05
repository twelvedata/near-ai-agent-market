#!/usr/bin/env bash
# Withdraw earned NEAR from NEAR AI Agent Market to twelvedata.near
# Usage: ./scripts/withdraw.sh <amount>
#   e.g. ./scripts/withdraw.sh 5.0
# Requires: AGENT_API_KEY set in environment (source .env.local)

set -euo pipefail

: "${AGENT_API_KEY:?AGENT_API_KEY is not set. Run: source .env.local}"
: "${1:?Usage: $0 <amount>  e.g. $0 5.0}"

AMOUNT="$1"
TO_ACCOUNT="twelvedata.near"
IDEMPOTENCY_KEY="withdraw-$(date +%Y%m%d%H%M%S)-$$"

echo "Withdrawing $AMOUNT NEAR to $TO_ACCOUNT..."

curl -s -X POST "https://market.near.ai/v1/wallet/withdraw" \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"to_account_id\": \"$TO_ACCOUNT\",
    \"amount\": \"$AMOUNT\",
    \"token_id\": \"wNEAR\",
    \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
  }" | jq .
