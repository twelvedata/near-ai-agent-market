# Deployment Guide for Twelve Data NEAR AI Proxy

This guide explains how to deploy the FastAPI proxy so the NEAR AI Agent Market can call your Twelve Data service.

## Prerequisites

- Python 3.10+
- Your Twelve Data API key
- GitHub repo pushed

## 1. Local Testing (Recommended First)

```bash
cd proxy
pip install -r requirements.txt

export TWELVE_DATA_API_KEY=your_twelve_data_api_key
export PROXY_SECRET=choose_a_secret_token
export OPENAI_API_KEY=your_openai_api_key   # optional, enables natural language queries

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Test it:

```bash
# Structured query
curl -X POST http://localhost:8000/invoke \
  -H "Authorization: Bearer choose_a_secret_token" \
  -H "Content-Type: application/json" \
  -d '{"input": {"function": "QUOTE", "symbol": "AAPL"}}'

# Natural language query
curl -X POST http://localhost:8000/invoke \
  -H "Authorization: Bearer choose_a_secret_token" \
  -H "Content-Type: application/json" \
  -d '{"input": {"query": "What is the current price of Bitcoin?"}}'

# Health check
curl http://localhost:8000/health
```

You should get a response with `"output": {...}` containing market data.

## 2. Deploy to Railway

### 2a. Create a Railway project

1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project** → **Deploy from GitHub repo**
3. Select this repository
4. Railway will auto-detect Python and use `proxy/` as the root (or set the root directory — see 2b)

### 2b. Set the root directory

Railway needs to know the app lives in `proxy/`, not the repo root.

In your Railway project settings:
- **Root Directory**: `proxy`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

Railway injects `$PORT` automatically — uvicorn picks it up.

### 2c. Set environment variables

In Railway → your service → **Variables**, add:

| Variable | Value |
|---|---|
| `TWELVE_DATA_API_KEY` | Your Twelve Data API key |
| `OPENAI_API_KEY` | Your OpenAI API key (optional — enables natural language queries) |

> **Note:** Do NOT set `PROXY_SECRET` in production. The NEAR AI marketplace does not forward auth headers when calling your endpoint, so if `PROXY_SECRET` is set, all marketplace calls will fail with 401. Leave it unset (the endpoint will be open to the marketplace).

Never commit API keys to the repo. Railway keeps them encrypted.

### 2d. Deploy

Railway deploys automatically on every push to `main`. Watch the build logs in the Railway dashboard.

Once deployed, Railway gives you a public URL. The production URL for this service is:
```
https://near-ai-agent-market-production.up.railway.app
```

### 2e. Verify the deployment

```bash
PROXY_URL=https://near-ai-agent-market-production.up.railway.app

# Health check
curl $PROXY_URL/health

# Live data check
curl -X POST $PROXY_URL/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": {"function": "QUOTE", "symbol": "AAPL"}}'
```

## 3. Update service-registration.json

The `service-registration.json` already points to the production URL:

```json
"endpoint_url": "https://near-ai-agent-market-production.up.railway.app/invoke"
```

Then follow `REGISTRATION.md` to register the service on the marketplace.

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `TWELVE_DATA_API_KEY` | Yes | Your Twelve Data API key |
| `PROXY_SECRET` | No | If set, all requests must include `Authorization: Bearer <secret>`. Do NOT set in production — the marketplace does not forward auth headers. |
| `OPENAI_API_KEY` | No | Enables natural language queries via Twelve Data's MCP utool server |
| `TD_MCP_BASE_URL` | No | Override Twelve Data MCP base URL (default: `https://mcp.twelvedata.com`) |
