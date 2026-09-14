"""
Twelve Data NEAR AI Agent Market Proxy
Structured queries go to the Twelve Data REST API.
Natural-language queries optionally use /utool when TD_UTOOL_URL is reachable.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from starlette.requests import Request
import httpx
import os

app = FastAPI(title="Twelve Data NEAR AI Agent Market Proxy")

TD_API_BASE = "https://api.twelvedata.com"
TD_MCP_BASE = os.getenv("TD_MCP_BASE_URL", "https://mcp.twelvedata.com")
# Hosted MCP no longer exposes /utool publicly (404). Override only if you run a utool gateway.
TD_UTOOL_URL = os.getenv("TD_UTOOL_URL", f"{TD_MCP_BASE.rstrip('/')}/utool")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROXY_SECRET = os.getenv("PROXY_SECRET")
TIMEOUT = 25.0


def _require_td_key():
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(status_code=500, detail="TWELVE_DATA_API_KEY is not configured")


def _client_headers():
    return {
        "accept": "application/json",
        "user-agent": "near-ai-proxy/1.0",
    }


def _with_apikey(params: dict) -> dict:
    """Twelve Data REST expects apikey as a query parameter, not Authorization."""
    _require_td_key()
    out = dict(params)
    out["apikey"] = TWELVE_DATA_API_KEY
    return out


async def _verify_token(authorization: str = Header(None)):
    if PROXY_SECRET and authorization != f"Bearer {PROXY_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _mask_key(text: str) -> str:
    """Twelve Data echoes the request in error bodies, so the key must not reach the caller."""
    if TWELVE_DATA_API_KEY:
        text = text.replace(TWELVE_DATA_API_KEY, "***")
    return text


def _scrub(data):
    if not isinstance(data, dict):
        return data
    data = dict(data)
    data.pop("apikey", None)
    param = data.get("param")
    if isinstance(param, dict):
        params = param.get("params")
        if isinstance(params, dict):
            params = dict(params)
            params.pop("apikey", None)
            param = dict(param)
            param["params"] = params
            data["param"] = param
    return data


async def _utool(client: httpx.AsyncClient, query: str) -> httpx.Response:
    headers = dict(_client_headers())
    if OPENAI_API_KEY:
        headers["x-openapi-key"] = OPENAI_API_KEY
    return await client.get(
        TD_UTOOL_URL,
        params=_with_apikey({"query": query}),
        headers=headers,
    )


@app.post("/invoke")
async def invoke(request: Request, _=Depends(_verify_token)):
    body = await request.json()
    input_data = body.get("input", {})
    caller_id = request.headers.get("x-caller-agent-id", "unknown")
    mode = "function" if "function" in input_data else "query" if "query" in input_data else "invalid"
    print(f"INVOKE caller={caller_id} mode={mode} input={_scrub(input_data)}", flush=True)

    try:
        async with httpx.AsyncClient(headers=_client_headers(), timeout=TIMEOUT) as client:
            if "function" in input_data:
                func = str(input_data["function"]).lower()
                params = {
                    k: str(v)
                    for k, v in input_data.items()
                    if k != "function" and k != "apikey"
                }
                resp = await client.get(
                    f"{TD_API_BASE}/{func}",
                    params=_with_apikey(params),
                )
                if resp.status_code >= 400:
                    # Optional NL fallback — only if utool is actually deployed.
                    query = input_data.get("query") or " ".join(
                        str(v) for v in input_data.values()
                    )
                    utool = await _utool(client, query)
                    if utool.status_code < 400:
                        resp = utool
                    else:
                        detail = _mask_key(resp.text)
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                f"Twelve Data REST /{func} returned {resp.status_code}: {detail}. "
                                f"utool fallback also failed ({utool.status_code})."
                            ),
                        )

            elif "query" in input_data:
                resp = await _utool(client, str(input_data["query"]))
                if resp.status_code >= 400:
                    raise HTTPException(
                        status_code=502,
                        detail=(
                            f"Natural-language /utool unavailable ({resp.status_code}). "
                            "Use structured input: "
                            '{"input":{"function":"QUOTE","symbol":"AAPL"}}. '
                            "Hosted mcp.twelvedata.com no longer serves /utool."
                        ),
                    )

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Input must contain 'function' or 'query'",
                )

            data = resp.json()

        return {
            "output": _scrub(data),
            "provider": "Twelve Data",
            "source": "https://twelvedata.com",
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e.response, "text") else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=_mask_key(error_detail))
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=_mask_key(f"Failed to reach Twelve Data: {str(e)}")
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
