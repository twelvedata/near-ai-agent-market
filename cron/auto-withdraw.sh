#!/usr/bin/env bash
# Auto-withdraw earned NEAR if balance exceeds threshold, then send Telegram report.
# Runs as a Railway cron job.
# Env vars required:
#   AGENT_API_KEY        — NEAR AI marketplace API key
#   TELEGRAM_BOT_TOKEN   — Telegram bot token
#   TELEGRAM_CHAT_ID     — Telegram chat/user ID
# Env vars optional:
#   WITHDRAW_TO          — destination NEAR account (default: twelvedata.near)
#   WITHDRAW_THRESHOLD   — withdraw if balance exceeds this (default: 1.0)

set -euo pipefail

: "${AGENT_API_KEY:?AGENT_API_KEY is not set}"
: "${TELEGRAM_BOT_TOKEN:?TELEGRAM_BOT_TOKEN is not set}"
: "${TELEGRAM_CHAT_ID:?TELEGRAM_CHAT_ID is not set}"

WITHDRAW_TO="${WITHDRAW_TO:-twelvedata.near}"
THRESHOLD="${WITHDRAW_THRESHOLD:-1.0}"
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

send_telegram() {
  local msg="$1"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"$TELEGRAM_CHAT_ID\", \"text\": \"$msg\", \"parse_mode\": \"Markdown\"}" \
    > /dev/null
}

echo "[$NOW] Checking balance..."

BALANCE_JSON=$(curl -s "https://market.near.ai/v1/wallet/balance" \
  -H "Authorization: Bearer $AGENT_API_KEY")

BALANCE=$(echo "$BALANCE_JSON" | jq -r '
  .balances[]
  | select(.token_id == "nep141:wrap.near")
  | .balance
  // "0"
')

echo "wNEAR balance: $BALANCE (threshold: $THRESHOLD)"

WITHDREW="no"
WITHDRAW_MSG="No withdrawal (balance below threshold of $THRESHOLD NEAR)."

SHOULD_WITHDRAW=$(awk -v bal="$BALANCE" -v thr="$THRESHOLD" 'BEGIN { print (bal+0 > thr+0) ? "yes" : "no" }')

if [ "$SHOULD_WITHDRAW" = "yes" ]; then
  IDEMPOTENCY_KEY="auto-withdraw-$(date +%Y%m%d%H%M%S)-$$"
  echo "Withdrawing $BALANCE NEAR to $WITHDRAW_TO..."
  WITHDRAW_RESULT=$(curl -s -X POST "https://market.near.ai/v1/wallet/withdraw" \
    -H "Authorization: Bearer $AGENT_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{
      \"to_account_id\": \"$WITHDRAW_TO\",
      \"amount\": \"$BALANCE\",
      \"token_id\": \"wNEAR\",
      \"idempotency_key\": \"$IDEMPOTENCY_KEY\"
    }")
  echo "$WITHDRAW_RESULT" | jq .
  TX_HASH=$(echo "$WITHDRAW_RESULT" | jq -r '.tx_hash // "unknown"')
  WITHDREW="yes"
  WITHDRAW_MSG="Withdrew *$BALANCE NEAR* to \`$WITHDRAW_TO\`\nTx: \`$TX_HASH\`"
fi

# Send Telegram report
MESSAGE="*Twelve Data NEAR AI Report*
🕐 $NOW

💰 *Balance:* $BALANCE NEAR

🏦 *Withdrawal:* $WITHDRAW_MSG"

send_telegram "$MESSAGE"
echo "Telegram notification sent."
