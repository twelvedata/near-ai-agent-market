# Restore Twelve Data on market.near.ai

Related to GitLab `twelvedata/mcp-data#9`.

## Root cause (2026-09-12)

Two independent problems:

### 1. Marketplace product changed

Old model (what this repo was built for): **service registry** — register a callable HTTP service, appear in discover, agents `POST /v1/services/{id}/invoke`.

New model (live today on [market.near.ai](https://market.near.ai)): **agent hiring marketplace** (“hire agents like teammates”). Public catalog is agents (`GET /v1/agents?q=…`, category pages like [/agents/data.md](https://market.near.ai/agents/data.md)), not the old service cards.

Evidence:

- `GET https://market.near.ai/v1/services` → **404**
- `GET https://market.near.ai/v1/agents?q=twelve` → `{"agents":[]}`
- Twelve Data is absent from [/agents/data.md](https://market.near.ai/agents/data.md) and [/agents/finance.md](https://market.near.ai/agents/finance.md)
- Old UUID invoke `…/v1/services/6b18f956-878d-47bc-9f3f-df42d2fcf88a/invoke` is gone with the services API
- Legacy host `market-legacy.near.ai` still answers `/v1/services` but requires auth (401 without bearer) — not the public discover UI

**Conclusion:** we were not “kicked for a missing form field”. The listing model moved; old service registration is not what discover shows anymore.

### 2. Our proxy `/invoke` was broken (even for health/smoke)

- `GET https://near-ai.twelvedata.com/health` → 200
- `POST https://near-ai.twelvedata.com/invoke` with `{"input":{"function":"QUOTE","symbol":"AAPL"}}` → **404**

Why:

1. Proxy sent `Authorization: apikey …`. Twelve Data REST **ignores** that and requires `?apikey=` → REST returns 401.
2. Fallback called `https://mcp.twelvedata.com/utool` → **404** (hosted MCP no longer exposes `/utool`).
3. Proxy re-raised the utool 404 to the caller.

Fix in `proxy/main.py`: pass `apikey` as query param; clear errors when utool is gone; optional `TD_UTOOL_URL` if we ever host a NL gateway again.

## Fix plan

### A. Ship proxy fix (code — this PR)

1. Merge/deploy `proxy/main.py` fix to the VPS (`near-ai.twelvedata.com` via GitHub Actions on `main`).
2. Smoke:

```bash
curl -sS https://near-ai.twelvedata.com/health
curl -sS -X POST https://near-ai.twelvedata.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"input":{"function":"QUOTE","symbol":"AAPL"}}'
```

Expect JSON with quote data, not 404/502.

Do **not** set `PROXY_SECRET` in production (marketplace / public callers will not send it).

### B. Re-list on the new marketplace (ops — needs publisher account)

Register as a **worker agent**, not as a legacy service:

1. Get `aat_…` token (owner mints in cabinet, or `POST /v1/agents/register` once — token shown once).
2. `PATCH /v1/agents/{id}` — description, `webhook_url` pointing at our backend (HMAC webhook, see [a2a-x402 flow](https://market.near.ai/skill/flows/a2a-x402.md)).
3. `POST /v1/agents/{id}/pricing-plans` — e.g. per_call USD/USDC.
4. `POST /v1/agents/{id}/webhook/test`
5. `PATCH /v1/agents/{id}` — `{"listing_status":"live"}`
6. Verify: `GET https://market.near.ai/v1/agents?q=twelve` and category pages; card at `https://<handle>.market.near.ai/.well-known/agent-card.json`

A self-registered agent stays out of Discover and cannot withdraw until a human adopts it (`POST /v1/agents/me/adoption-code`), so step 1 needs an owner lined up.

**Blocker today:** no `AGENT_API_KEY` / cabinet access in this environment. Ask Yury/Kolya/Midas for the publisher account or a fresh `aat_` token. Handle is immutable and becomes a DNS label — use `twelvedata`.

### C. Optional architecture follow-up

Legacy `POST /invoke` proxy can stay for direct/partner calls, but **catalog presence** requires the webhook/job (or A2A) worker path. Either:

- wrap the existing proxy behind a thin webhook that maps job briefs → structured Twelve Data calls and submits deliverables, or
- run a managed agent on the marketplace and call Twelve Data from there.

## Acceptance for #9

- [x] Root cause written (platform migration + broken invoke auth/utool)
- [ ] Proxy fix deployed; structured `QUOTE` smoke green
- [ ] Agent re-registered with `listing_status=live` **or** explicit blocker: missing `aat_` / cabinet
- [ ] Twelve Data visible via `GET /v1/agents?q=twelve` or documented won’t-do
