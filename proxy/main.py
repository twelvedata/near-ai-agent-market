"""
Twelve Data NEAR AI Agent Market Proxy
Supports both structured queries (fast & cheap) and natural language (u-tool with OpenAI).
"""

from fastapi import FastAPI, HTTPException, Header, Depends
from starlette.requests import Request
import httpx
import os

app = FastAPI(title="Twelve Data NEAR AI Agent Market Proxy")

TD_API_BASE = "https://api.twelvedata.com"
TD_MCP_BASE = os.getenv("TD_MCP_BASE_URL", "https://mcp.twelvedata.com")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PROXY_SECRET = os.getenv("PROXY_SECRET")
TIMEOUT = 25.0


def _require_td_key():
    if not TWELVE_DATA_API_KEY:
        raise HTTPException(status_code=500, detail="TWELVE_DATA_API_KEY is not configured")

def _headers():
    _require_td_key()
    return {
        "accept": "application/json",
        "user-agent": "near-ai-proxy/1.0",
        "Authorization": f"apikey {TWELVE_DATA_API_KEY}",
    }

async def _verify_token(authorization: str = Header(None)):
    if PROXY_SECRET and authorization != f"Bearer {PROXY_SECRET}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.post("/invoke")
async def invoke(request: Request, _=Depends(_verify_token)):
    body = await request.json()
    input_data = body.get("input", {})

    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=TIMEOUT) as client:

            utool_headers = {**_headers()}
            if OPENAI_API_KEY:
                utool_headers["x-openapi-key"] = OPENAI_API_KEY

            if "function" in input_data:
                func = input_data["function"].lower()
                params = {k: str(v) for k, v in input_data.items() if k != "function"}
                try:
                    resp = await client.get(f"{TD_API_BASE}/{func}", params=params)
                    resp.raise_for_status()
                except Exception:
                    query = input_data.get("query") or " ".join(str(v) for v in input_data.values())
                    resp = await client.get(f"{TD_MCP_BASE}/utool", params={"query": query}, headers=utool_headers)

            elif "query" in input_data:
                resp = await client.get(f"{TD_MCP_BASE}/utool", params={"query": input_data["query"]}, headers=utool_headers)

            else:
                raise HTTPException(status_code=400, detail="Input must contain 'function' or 'query'")

            resp.raise_for_status()
            data = resp.json()

        # === SECURITY FIX: Sanitize sensitive data ===
        if isinstance(data, dict):
            # Remove apikey if it appears anywhere in the response
            if "param" in data and isinstance(data["param"], dict):
                if "params" in data["param"] and isinstance(data["param"]["params"], dict):
                    data["param"]["params"].pop("apikey", None)
            
            # Also clean top level if somehow present
            data.pop("apikey", None)

        return {
            "output": data,
            "provider": "Twelve Data",
            "source": "https://twelvedata.com"
        }

    except HTTPException:
        raise
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e.response, 'text') else str(e)
        raise HTTPException(status_code=e.response.status_code, detail=error_detail)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach Twelve Data: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)