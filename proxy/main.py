"""
Twelve Data NEAR AI Agent Market Proxy
Structured queries go to the Twelve Data REST API.
Natural-language queries optionally use /utool when TD_UTOOL_URL is reachable.
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from starlette.requests import Request
import httpx
import os

from near_agent import router as near_router
from twelvedata_client import (
    TD_API_BASE,
    TD_UTOOL_URL,
    TIMEOUT,
    api_key,
    client_headers,
    mask_key,
    rest_params,
    scrub,
    with_apikey,
)

app = FastAPI(title="Twelve Data NEAR AI Agent Market Proxy")
app.include_router(near_router)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROXY_SECRET = os.getenv("PROXY_SECRET")


def _require_td_key():
    if not api_key():
        raise HTTPException(status_code=500, detail="TWELVE_DATA_API_KEY is not configured")


async def _verify_token(authorization: str = Header(None)):
    if PROXY_SECRET and authorization != f"Bearer {PROXY_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _utool(client: httpx.AsyncClient, query: str) -> httpx.Response:
    headers = dict(client_headers())
    if OPENAI_API_KEY:
        headers["x-openapi-key"] = OPENAI_API_KEY
    return await client.get(
        TD_UTOOL_URL,
        params=with_apikey({"query": query}),
        headers=headers,
    )


@app.post("/invoke")
async def invoke(request: Request, _=Depends(_verify_token)):
    body = await request.json()
    input_data = body.get("input", {})
    caller_id = request.headers.get("x-caller-agent-id", "unknown")
    mode = "function" if "function" in input_data else "query" if "query" in input_data else "invalid"
    print(f"INVOKE caller={caller_id} mode={mode} input={scrub(input_data)}", flush=True)

    try:
        async with httpx.AsyncClient(headers=client_headers(), timeout=TIMEOUT) as client:
            if "function" in input_data:
                _require_td_key()
                func = str(input_data["function"]).lower()
                resp = await client.get(
                    f"{TD_API_BASE}/{func}",
                    params=with_apikey(rest_params(input_data)),
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
                        detail = mask_key(resp.text)
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                f"Twelve Data REST /{func} returned {resp.status_code}: {detail}. "
                                f"utool fallback also failed ({utool.status_code})."
                            ),
                        )

            elif "query" in input_data:
                _require_td_key()
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
            "output": scrub(data),
            "provider": "Twelve Data",
            "source": "https://twelvedata.com",
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e.response, "text") else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=mask_key(error_detail))
    except Exception as e:
        raise HTTPException(
            status_code=502, detail=mask_key(f"Failed to reach Twelve Data: {str(e)}")
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
