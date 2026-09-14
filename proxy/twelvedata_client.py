"""Shared Twelve Data REST access: key handling, scrubbing, and one fetch entry point."""

import os

import httpx

TD_API_BASE = "https://api.twelvedata.com"
TD_MCP_BASE = os.getenv("TD_MCP_BASE_URL", "https://mcp.twelvedata.com")
# Hosted MCP no longer exposes /utool publicly (404). Override only if you run a utool gateway.
TD_UTOOL_URL = os.getenv("TD_UTOOL_URL", f"{TD_MCP_BASE.rstrip('/')}/utool")
TIMEOUT = 25.0


def api_key() -> str:
    return os.getenv("TWELVE_DATA_API_KEY", "")


def client_headers() -> dict:
    return {
        "accept": "application/json",
        "user-agent": "near-ai-proxy/1.0",
    }


def with_apikey(params: dict) -> dict:
    """Twelve Data REST expects apikey as a query parameter, not Authorization."""
    out = dict(params)
    out["apikey"] = api_key()
    return out


def mask_key(text: str) -> str:
    """Twelve Data echoes the request in error bodies, so the key must not reach the caller."""
    key = api_key()
    if key:
        text = text.replace(key, "***")
    return text


def scrub(data):
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


def rest_params(input_data: dict) -> dict:
    return {
        str(k): str(v)
        for k, v in input_data.items()
        if k not in ("function", "apikey")
    }


async def fetch_rest(function: str, params: dict) -> dict:
    """Call one Twelve Data endpoint. Raises TwelveDataError with a masked message on failure."""
    async with httpx.AsyncClient(headers=client_headers(), timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{TD_API_BASE}/{function.lower()}", params=with_apikey(params)
        )
    if resp.status_code >= 400:
        raise TwelveDataError(
            f"Twelve Data REST /{function.lower()} returned {resp.status_code}: "
            f"{mask_key(resp.text)}"
        )
    return scrub(resp.json())


class TwelveDataError(RuntimeError):
    pass
