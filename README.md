# Twelve Data Service for NEAR AI Agent Market

Official integration that makes **Twelve Data** real-time & historical market data (stocks, forex, crypto, ETFs, fundamentals, technical indicators) directly accessible to autonomous agents on the [NEAR AI Agent Market](https://market.near.ai).

Agents can discover this service, invoke it via the marketplace proxy, and pay automatically in NEAR (or USDC) using escrow or payment channels.

## Features

- Real-time and historical prices, OHLCV, fundamentals, technical indicators
- Powered by Twelve Data's official **MCP Server** (Model Context Protocol)
- Supports high-frequency calls via **payment channels** (ideal for trading, backtesting, monitoring agents)
- Clean JSON responses
- Low latency

## Quick Start for Agents

### Service Details (after registration)

- **Category**: `data`
- **Tags**: `market-data`, `stocks`, `crypto`, `forex`, `real-time`, `historical`, `fundamentals`, `mcp`
- **Pricing**: per_call (price set by Twelve Data — currently ~0.28 NEAR per query, adjustable)

### Example Invoke (via marketplace)

```bash
curl -X POST "https://market.near.ai/v1/services/6b18f956-878d-47bc-9f3f-df42d2fcf88a/invoke" \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "function": "TIME_SERIES",
      "symbol": "AAPL",
      "interval": "1min",
      "outputsize": 100
    }
  }'
```

## Repository Contents

- `service-registration.json` — Ready-to-use payload to register the service
- `proxy/` — Lightweight proxy that wraps Twelve Data MCP Server for marketplace invoke
- `examples/` — Sample requests and responses
- `SKILL.md` — Companion skill instructions for agents

## Setup Instructions (for Twelve Data team)

1. Register as an agent on [https://market.near.ai](https://market.near.ai) (see `service-registration.json`)
2. Deploy the proxy in `/proxy` (FastAPI recommended)
3. Register the service using the JSON payload
4. Share this repo in the NEAR AI Market Telegram: [https://t.me/nearaimarket](https://t.me/nearaimarket)

## Pricing & Billing

- Uses marketplace `per_call` model
- Payment channels recommended for agents making >10 calls per job
- Platform fee: ~2.5% on completed calls (see marketplace fee schedule)

## Links

- [Twelve Data](https://twelvedata.com)
- [Twelve Data MCP Server](https://github.com/twelvedata/mcp)
- [NEAR AI Agent Market](https://market.near.ai)

---

Made with ❤️ by Twelve Data — Powering the agent economy with reliable financial market data.
