import pytest
import respx
import httpx
TD_API_BASE = "https://api.twelvedata.com"
TD_MCP_BASE = "https://mcp.twelvedata.com"
QUOTE_RESPONSE = {"symbol": "AAPL", "close": "150.00", "status": "ok"}
UTOOL_RESPONSE = {"result": "some natural language answer", "status": "ok"}


@respx.mock
def test_function_routes_to_correct_rest_endpoint(client, auth_headers):
    route = respx.get(f"{TD_API_BASE}/time_series").mock(
        return_value=httpx.Response(200, json={"values": [], "status": "ok"})
    )
    resp = client.post("/invoke", json={"input": {"symbol": "AAPL", "function": "TIME_SERIES", "interval": "1day"}}, headers=auth_headers)
    assert resp.status_code == 200
    assert route.called


@respx.mock
def test_function_key_stripped_from_forwarded_params(client, auth_headers):
    route = respx.get(f"{TD_API_BASE}/quote").mock(
        return_value=httpx.Response(200, json=QUOTE_RESPONSE)
    )
    client.post("/invoke", json={"input": {"symbol": "AAPL", "function": "QUOTE"}}, headers=auth_headers)
    assert "function" not in str(route.calls.last.request.url)


@respx.mock
def test_rest_failure_falls_back_to_utool(client, auth_headers):
    respx.get(f"{TD_API_BASE}/unknown_func").mock(
        return_value=httpx.Response(404, json={"status": "error"})
    )
    utool_route = respx.get(f"{TD_MCP_BASE}/utool").mock(
        return_value=httpx.Response(200, json=UTOOL_RESPONSE)
    )
    resp = client.post("/invoke", json={"input": {"symbol": "AAPL", "function": "UNKNOWN_FUNC"}}, headers=auth_headers)
    assert resp.status_code == 200
    assert utool_route.called


@respx.mock
def test_query_goes_to_utool_with_openai_key(client, auth_headers):
    route = respx.get(f"{TD_MCP_BASE}/utool").mock(
        return_value=httpx.Response(200, json=UTOOL_RESPONSE)
    )
    client.post("/invoke", json={"input": {"query": "What is the RSI for AAPL?"}}, headers=auth_headers)
    assert route.called
    assert route.calls.last.request.headers.get("x-openapi-key") == "test-openai-key"


@respx.mock
def test_query_does_not_hit_rest(client, auth_headers):
    respx.get(f"{TD_MCP_BASE}/utool").mock(return_value=httpx.Response(200, json=UTOOL_RESPONSE))
    rest_route = respx.get(f"{TD_API_BASE}/").mock(return_value=httpx.Response(200, json={}))
    client.post("/invoke", json={"input": {"query": "Any question"}}, headers=auth_headers)
    assert not rest_route.called


def test_symbol_alone_returns_400(client, auth_headers):
    resp = client.post("/invoke", json={"input": {"symbol": "AAPL"}}, headers=auth_headers)
    assert resp.status_code == 400


def test_proxy_secret_blocks_unauthorized(client):
    resp = client.post("/invoke", json={"input": {"symbol": "AAPL"}})
    assert resp.status_code == 401


def test_proxy_secret_allows_correct_token(client, auth_headers):
    # Just checking auth passes — no outbound call needed for this assertion
    # (will 502 because no mock, but auth itself is not the blocker)
    resp = client.post("/invoke", json={"input": {}}, headers=auth_headers)
    assert resp.status_code != 401


@respx.mock
def test_apikey_scrubbed_from_response(client, auth_headers):
    dirty_response = {
        "symbol": "AAPL",
        "apikey": "super-secret",
        "param": {"params": {"apikey": "super-secret", "symbol": "AAPL"}},
    }
    respx.get(f"{TD_API_BASE}/quote").mock(return_value=httpx.Response(200, json=dirty_response))
    resp = client.post("/invoke", json={"input": {"symbol": "AAPL", "function": "QUOTE"}}, headers=auth_headers)
    output = resp.json()["output"]
    assert "apikey" not in output
    assert "apikey" not in output.get("param", {}).get("params", {})
