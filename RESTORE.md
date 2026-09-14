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

### B. Re-list as an http worker agent (ops)

Create the agent **under our own builder account**. `POST /v1/agents/register` also works without an account, but a self-registered agent stays out of Discover and cannot withdraw until a human redeems `POST /v1/agents/me/adoption-code` — an extra step with no upside for us.

`runtime: managed` is the other option: the marketplace executes an uploaded skill (`POST /v1/accounts/{id}/skills`). Rejected — that puts `TWELVE_DATA_API_KEY` inside their runtime and lets their model decide how many credits we spend.

1. `POST /v1/auth/signup` — work email, `handle: twelvedata`, `display_name: Twelve Data`; confirm email, then sign the Builder Agreement (`GET /v1/legal/builder-agreement`, stamped as `operator_agreement_signed_at`).
2. `POST /v1/accounts/{account_id}/agents` — `{"handle":"twelvedata","name":"…","category":"finance","runtime":"http","sla_seconds":…}`. Handle is immutable, becomes a DNS label, and allows only lowercase letters, digits and `_`. The `aat_…` token is shown once → store as the `NEAR_AGENT_TOKEN` repo secret.
3. Put `NEAR_AGENT_TOKEN` and a generated `NEAR_WEBHOOK_SECRET` in GitHub secrets, run the **Sync env** workflow.
4. `PATCH /v1/agents/{id}` — description, `bio_markdown`, `tags`, `webhook_secret`, `webhook_url: https://near-ai.twelvedata.com/near/webhook`, `webhook_enabled: true`.
5. `POST /v1/agents/{id}/pricing-plans` — `per_call`, amount as a string.
6. `POST /v1/agents/{id}/webhook/test` → then `PATCH /v1/agents/{id}` with `{"listing_status":"live"}` (needs a default pricing plan).
7. Verify: `GET https://market.near.ai/v1/agents?q=twelvedata`, the [data](https://market.near.ai/agents/data.md) / [finance](https://market.near.ai/agents/finance.md) category pages, and the card at `https://twelvedata.market.near.ai/.well-known/agent-card.json`.

The `verified` badge additionally needs a live agent plus 50 delivered jobs (`GET /v1/accounts/{id}/verification`) — it does not gate the listing.

### C. Worker implementation (code — this PR)

`proxy/near_agent.py` serves the worker path: HMAC-SHA256 check on the event, immediate 2xx, then `POST /v1/assignments/{id}/start`, brief → structured Twelve Data call, deliverable hosted at `/near/deliverables/{assignment}.json` and submitted via `POST /v1/assignments/{id}/submit` (the API takes a URL plus hash, not an inline body). Unreadable briefs get a message in the thread instead of a junk deliverable.

The signature header spelling is not in their OpenAPI spec, so several usual names are accepted; `webhook/test` will confirm which one they send. Legacy `POST /invoke` stays for direct and partner calls.

## Acceptance for #9

- [x] Root cause written (platform migration + broken invoke auth/utool)
- [x] Proxy fix deployed; structured `QUOTE` smoke green
- [x] Worker webhook implemented and covered by tests
- [ ] Builder account created, agent `twelvedata` with `listing_status=live`
- [ ] Twelve Data visible via `GET /v1/agents?q=twelvedata`
