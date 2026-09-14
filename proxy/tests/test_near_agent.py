import hashlib
import hmac
import json
import time

import httpx
import pytest
import respx

import near_agent
from near_agent import parse_brief

MARKET = "https://market.near.ai"
TD_API_BASE = "https://api.twelvedata.com"
ASSIGNMENT = "a1b2c3"


def signed(payload: dict) -> tuple[bytes, dict]:
    raw = json.dumps(payload).encode()
    timestamp = str(int(time.time()))
    digest = hmac.new(
        b"test-webhook-secret",
        f"{timestamp}.".encode() + raw,
        hashlib.sha256,
    ).hexdigest()
    return raw, {
        "content-type": "application/json",
        "x-market-timestamp": timestamp,
        "x-market-signature": f"sha256={digest}",
        "x-market-event": payload.get("event", ""),
        "x-market-delivery": "test-delivery",
    }


@pytest.fixture(autouse=True)
def deliverable_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(near_agent, "DELIVERABLE_DIR", tmp_path)
    monkeypatch.setattr(near_agent, "PUBLIC_BASE", "https://near-ai.twelvedata.com")


def test_parse_brief_reads_json_block():
    request = parse_brief("Data pull", 'use {"function":"TIME_SERIES","symbol":"AAPL"}')
    assert request == {"function": "TIME_SERIES", "symbol": "AAPL"}


def test_parse_brief_reads_plain_english():
    assert parse_brief("Need a quote", "current price for AAPL please") == {
        "function": "QUOTE",
        "symbol": "AAPL",
    }
    assert parse_brief("History", "daily OHLCV for EUR/USD, last 30 bars") == {
        "function": "TIME_SERIES",
        "symbol": "EUR/USD",
        "interval": "1day",
        "outputsize": "30",
    }
    assert parse_brief("Indicator", "14-day RSI for MSFT") == {
        "function": "RSI",
        "symbol": "MSFT",
        "interval": "1day",
        "time_period": "14",
    }


def test_parse_brief_returns_none_when_unreadable():
    assert parse_brief("Write my thesis", "no instrument here") is None


def test_webhook_rejects_bad_signature(client):
    resp = client.post("/near/webhook", json={"event": "hire.created"})
    assert resp.status_code == 401


@respx.mock
def test_webhook_delivers_quote(client):
    respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/start").mock(
        return_value=httpx.Response(200, json={"startedAt": "now"})
    )
    respx.get(f"{TD_API_BASE}/quote").mock(
        return_value=httpx.Response(200, json={"symbol": "AAPL", "close": "150.00"})
    )
    submit = respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/submit").mock(
        return_value=httpx.Response(200, json={})
    )
    raw, headers = signed(
        {
            "event": "hire.created",
            "assignment_id": ASSIGNMENT,
            "title": "Quote",
            "description": "current price for AAPL",
        }
    )

    resp = client.post("/near/webhook", content=raw, headers=headers)

    assert resp.status_code == 200
    assert submit.called
    body = json.loads(submit.calls.last.request.content)
    path = body["deliverableUrl"].removeprefix("https://near-ai.twelvedata.com")
    assert path.startswith(f"/near/deliverables/{ASSIGNMENT}-") and path.endswith(".json")
    assert len(body["deliverableHash"]) == 64

    hosted = client.get(path)
    assert hosted.status_code == 200
    assert hosted.json()["data"]["symbol"] == "AAPL"


def test_deliverable_path_traversal_is_rejected(client):
    assert client.get("/near/deliverables/..%2F..%2Fetc%2Fpasswd").status_code == 404


@respx.mock
def test_webhook_ping_is_ack_only(client):
    start = respx.post(url__regex=r".*/v1/assignments/.*").mock(
        return_value=httpx.Response(200, json={})
    )
    raw, headers = signed({"event": "webhook.ping", "agent_id": "agt_1", "test": True})

    resp = client.post("/near/webhook", content=raw, headers=headers)

    assert resp.status_code == 200
    assert resp.json()["event"] == "webhook.ping"
    assert not start.called


@respx.mock
def test_webhook_asks_for_clarification_when_brief_unreadable(client):
    respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/start").mock(
        return_value=httpx.Response(200, json={"startedAt": "now"})
    )
    messages = respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/messages").mock(
        return_value=httpx.Response(200, json={})
    )
    raw, headers = signed(
        {
            "event": "hire.created",
            "assignment_id": ASSIGNMENT,
            "title": "Help",
            "description": "do something nice",
        }
    )

    resp = client.post("/near/webhook", content=raw, headers=headers)

    assert resp.status_code == 200
    assert messages.called
    assert "market-data request" in json.loads(messages.calls.last.request.content)["body"]


@respx.mock
def test_webhook_reports_twelve_data_failure_without_leaking_key(client):
    respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/start").mock(
        return_value=httpx.Response(200, json={"startedAt": "now"})
    )
    respx.get(f"{TD_API_BASE}/quote").mock(
        return_value=httpx.Response(401, text='{"message":"bad apikey=test-td-key"}')
    )
    messages = respx.post(f"{MARKET}/v1/assignments/{ASSIGNMENT}/messages").mock(
        return_value=httpx.Response(200, json={})
    )
    raw, headers = signed(
        {
            "event": "hire.created",
            "assignment_id": ASSIGNMENT,
            "title": "Quote",
            "description": "price for AAPL",
        }
    )

    client.post("/near/webhook", content=raw, headers=headers)

    body = json.loads(messages.calls.last.request.content)["body"]
    assert "test-td-key" not in body
    assert "***" in body
