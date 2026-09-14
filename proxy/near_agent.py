"""Worker side of the NEAR AI Agent Market: take hire webhooks, deliver Twelve Data payloads.

The marketplace never calls Twelve Data directly. It posts a signed event here, we answer the
brief with a structured REST payload, host it, and submit the link back as the deliverable.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import Response

from twelvedata_client import TwelveDataError, fetch_rest, rest_params

router = APIRouter(prefix="/near")

MARKET_BASE = os.getenv("NEAR_MARKET_BASE_URL", "https://market.near.ai")
PUBLIC_BASE = os.getenv("NEAR_PUBLIC_BASE_URL", "https://near-ai.twelvedata.com")
DELIVERABLE_DIR = Path(os.getenv("NEAR_DELIVERABLE_DIR", "/data/deliverables"))
TIMEOUT = 25.0
# market.near.ai/skill/reference/webhooks.md — reject stale deliveries.
MAX_SKEW_SECONDS = 300
WORK_EVENTS = frozenset({"hire.created", "hire.changes_requested"})

HELP_BODY = (
    "I could not read a market-data request from this brief. Send the instrument and what you "
    'need, for example "QUOTE for AAPL", "daily OHLCV for EUR/USD, last 30 bars" or '
    '"14-day RSI for MSFT". A JSON block such as '
    '{"function":"TIME_SERIES","symbol":"AAPL","interval":"1day"} is taken as-is.'
)

FUNCTION_KEYWORDS = (
    (("rsi",), "RSI"),
    (("macd",), "MACD"),
    (("bollinger", "bbands"), "BBANDS"),
    (("sma", "simple moving average"), "SMA"),
    (("ema", "exponential moving average"), "EMA"),
    (("ohlcv", "time series", "candles", "history", "historical", "bars"), "TIME_SERIES"),
    (("exchange rate", "convert"), "EXCHANGE_RATE"),
    (("quote", "price", "change"), "QUOTE"),
)
SYMBOL_RE = re.compile(r"\b([A-Z]{1,6}(?:/[A-Z]{3,6})?)\b")
INTERVAL_RE = re.compile(
    r"\b(?:1|5|15|30|45)\s*min\b"
    r"|\b(?:1|2|4|8)\s*h(?:our)?\b"
    r"|\b(?:1day|daily|1week|weekly|1month|monthly)\b",
    re.I,
)
PERIOD_RE = re.compile(r"\b(\d{1,3})[- ]day\b", re.I)
COUNT_RE = re.compile(r"\blast\s+(\d{1,4})\b", re.I)
NOT_A_SYMBOL = {"RSI", "MACD", "SMA", "EMA", "OHLCV", "USD", "JSON", "API", "I", "A"}


def _signature_ok(raw: bytes, headers) -> bool:
    """HMAC-SHA256 over `{X-Market-Timestamp}.{raw_body}` per marketplace webhook reference."""
    secret = os.getenv("NEAR_WEBHOOK_SECRET", "")
    timestamp = headers.get("x-market-timestamp")
    provided = headers.get("x-market-signature", "")
    if not secret or not timestamp or not provided:
        return False
    try:
        if abs(time.time() - int(timestamp)) > MAX_SKEW_SECONDS:
            return False
    except ValueError:
        return False
    expected = hmac.new(
        secret.encode(),
        f"{timestamp}.".encode() + raw,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(provided.removeprefix("sha256=").strip().lower(), expected)


def _interval(text: str) -> str | None:
    match = INTERVAL_RE.search(text)
    if not match:
        return None
    raw = match.group(0).lower().replace(" ", "")
    return {"daily": "1day", "weekly": "1week", "monthly": "1month"}.get(raw, raw)


def parse_brief(title: str, description: str) -> dict | None:
    """Turn a job brief into Twelve Data input. Returns None when the ask is not recognisable."""
    text = f"{title}\n{description}".strip()

    for block in re.findall(r"\{[^{}]*\}", text, re.S):
        try:
            candidate = json.loads(block)
        except ValueError:
            continue
        candidate = candidate.get("input", candidate)
        if isinstance(candidate, dict) and candidate.get("function"):
            return candidate

    lowered = text.lower()
    function = next(
        (name for words, name in FUNCTION_KEYWORDS if any(w in lowered for w in words)), None
    )
    symbols = [s for s in SYMBOL_RE.findall(text) if s not in NOT_A_SYMBOL]
    if not function or not symbols:
        return None

    request = {"function": function, "symbol": symbols[0]}
    interval = _interval(text)
    if interval:
        request["interval"] = interval
    elif function != "QUOTE" and function != "EXCHANGE_RATE":
        request["interval"] = "1day"
    period = PERIOD_RE.search(text)
    if period and function in ("RSI", "SMA", "EMA", "BBANDS"):
        request["time_period"] = period.group(1)
    count = COUNT_RE.search(text)
    if count:
        request["outputsize"] = count.group(1)
    return request


def store_deliverable(assignment_id: str, request: dict, data) -> tuple[str, str]:
    body = json.dumps(
        {
            "request": request,
            "data": data,
            "provider": "Twelve Data",
            "source": "https://twelvedata.com",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        indent=2,
    ).encode()
    # The deliverable URL is unauthenticated, so the name must not be guessable from a job id.
    name = f"{assignment_id}-{secrets.token_hex(8)}.json"
    DELIVERABLE_DIR.mkdir(parents=True, exist_ok=True)
    (DELIVERABLE_DIR / name).write_bytes(body)
    url = f"{PUBLIC_BASE.rstrip('/')}/near/deliverables/{name}"
    return url, hashlib.sha256(body).hexdigest()


async def _market_post(path: str, payload: dict | None = None) -> httpx.Response:
    token = os.getenv("NEAR_AGENT_TOKEN", "")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        return await client.post(
            f"{MARKET_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )


async def deliver(assignment_id: str, title: str, description: str) -> None:
    await _market_post(f"/v1/assignments/{assignment_id}/start")
    request = parse_brief(title, description)
    if not request:
        await _market_post(
            f"/v1/assignments/{assignment_id}/messages", {"body": HELP_BODY}
        )
        return
    try:
        data = await fetch_rest(str(request["function"]), rest_params(request))
    except TwelveDataError as exc:
        await _market_post(
            f"/v1/assignments/{assignment_id}/messages", {"body": str(exc)}
        )
        return
    url, digest = store_deliverable(assignment_id, request, data)
    await _market_post(
        f"/v1/assignments/{assignment_id}/submit",
        {"deliverableUrl": url, "deliverableHash": digest},
    )


@router.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not _signature_ok(raw, request.headers):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    payload = json.loads(raw or b"{}")
    event = str(payload.get("event") or request.headers.get("x-market-event") or "unknown")
    assignment_id = payload.get("assignment_id")
    delivery = request.headers.get("x-market-delivery")
    print(
        f"NEAR webhook event={event} assignment={assignment_id} delivery={delivery}",
        flush=True,
    )

    # webhook.ping / hire.accepted / etc. — acknowledge only; work starts on hire.created.
    if event in WORK_EVENTS and assignment_id:
        title = str(payload.get("title") or "")
        description = str(payload.get("description") or "")
        if event == "hire.changes_requested" and payload.get("feedback"):
            description = f"{description}\n{payload['feedback']}".strip()
        background.add_task(deliver, str(assignment_id), title, description)
    return {"status": "accepted", "event": event}


@router.get("/deliverables/{name}")
async def deliverable(name: str):
    path = DELIVERABLE_DIR / name
    if path.name != name or not path.is_file():
        raise HTTPException(status_code=404, detail="Not Found")
    return Response(content=path.read_bytes(), media_type="application/json")
