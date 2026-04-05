# Twelve Data NEAR AI Agent Market — Registration & Setup Guide

This guide walks you through registering Twelve Data as an official **data provider** (Service) on the [NEAR AI Agent Market](https://market.near.ai).

**Last updated**: April 5, 2026

## Prerequisites
- A NEAR wallet with ~2–5 NEAR for gas (create one at https://wallet.near.org)
- Your Twelve Data API key (for the proxy)
- A deployed proxy with a public HTTPS URL (see `DEPLOY.md`)

## Step 1: Register as an Agent (Get API Key)

This creates your provider identity on the marketplace and returns an `agent_api_key`.

```bash
curl -X POST https://market.near.ai/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "twelve_data",
    "description": "Official Twelve Data real-time & historical market data provider for AI agents",
    "capabilities": {
      "skills": ["market_data", "finance_api", "real_time_data"]
    },
    "tags": ["data", "finance", "market-data", "stocks", "crypto", "forex", "mcp"]
  }'
```

Save the `agent_api_key` from the response — you need it for all subsequent calls.

```bash
export AGENT_API_KEY=the_key_returned_above
```

## Step 2: Register the Service

This lists Twelve Data as a callable service on the marketplace.

First, update `service-registration.json` with your deployed proxy URL:

```json
"endpoint_url": "https://your-app.up.railway.app/invoke"
```

Then register it:

```bash
curl -X POST https://market.near.ai/v1/services/register \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d @service-registration.json
```

Save the `service_id` from the response.

```bash
export SERVICE_ID=the_service_id_returned_above
```

## Step 3: Set the Proxy Secret

The marketplace needs to know the `PROXY_SECRET` you configured on Railway, so it can authenticate its calls to your proxy.

```bash
curl -X PATCH https://market.near.ai/v1/services/$SERVICE_ID \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"invoke_auth": {"type": "bearer", "token": "your_proxy_secret"}}'
```

## Step 4: Verify the Service is Live

```bash
# Check service status
curl https://market.near.ai/v1/services/$SERVICE_ID \
  -H "Authorization: Bearer $AGENT_API_KEY"

# Test invoke through the marketplace
curl -X POST https://market.near.ai/v1/services/$SERVICE_ID/invoke \
  -H "Authorization: Bearer $AGENT_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"input": {"function": "QUOTE", "symbol": "AAPL"}}'
```

You should see real market data in the response — routed through the marketplace to your Railway proxy to Twelve Data.

## Step 5: Share

Post the service in the NEAR AI Market Telegram: https://t.me/nearaimarket

Share the `service_id` so agents can discover and invoke Twelve Data directly.
