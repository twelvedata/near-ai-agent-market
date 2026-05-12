# Deployment Guide — Hetzner VPS

This guide explains how to deploy the FastAPI proxy and auto-withdraw cron on a Hetzner VPS using Docker Compose + Caddy.

## Architecture

- **Caddy** (port 80/443) terminates TLS via Let's Encrypt and reverse-proxies to the FastAPI app.
- **proxy** (FastAPI/uvicorn) serves `/invoke` and `/health` on internal port 8000.
- **cron** is a one-shot container invoked by the host crontab once a day to check the NEAR balance and withdraw above threshold.

Auto-deploy: every push to `main` triggers `.github/workflows/deploy.yml`, which SSHes to the VPS and runs `git pull && docker compose up -d`.

## 1. Local Testing

```bash
cd proxy
pip install -r requirements.txt

export TWELVE_DATA_API_KEY=your_twelve_data_api_key
export OPENAI_API_KEY=your_openai_api_key   # optional, enables natural language queries

uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Test:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": {"function": "QUOTE", "symbol": "AAPL"}}'
```

## 2. Provision the VPS

1. Create a Hetzner Cloud server (CX22 or larger, Ubuntu 24.04).
2. SSH in as `root`, create a deploy user:
   ```bash
   adduser --disabled-password --gecos "" deploy
   usermod -aG sudo deploy
   mkdir -p /home/deploy/.ssh
   # paste your public key into /home/deploy/.ssh/authorized_keys
   chown -R deploy:deploy /home/deploy/.ssh
   chmod 700 /home/deploy/.ssh
   chmod 600 /home/deploy/.ssh/authorized_keys
   ```
3. Disable password SSH in `/etc/ssh/sshd_config` (`PasswordAuthentication no`), `systemctl reload ssh`.
4. Install Docker:
   ```bash
   apt-get update
   apt-get install -y docker.io docker-compose-plugin
   usermod -aG docker deploy
   ```

## 3. DNS

Point an A record (e.g. `near-ai.twelvedata.com`) at the VPS's public IP. Wait for propagation (`dig +short near-ai.twelvedata.com`).

Then update `Caddyfile` in the repo with the real hostname and push:

```
near-ai.twelvedata.com {
    reverse_proxy proxy:8000
}
```

## 4. First-time deploy on the VPS

As the `deploy` user:

```bash
sudo mkdir -p /opt && sudo chown deploy:deploy /opt
cd /opt
git clone https://github.com/<org>/near-ai-agent-market.git
cd near-ai-agent-market
```

Create `/opt/near-ai-agent-market/.env`:

```
TWELVE_DATA_API_KEY=...
OPENAI_API_KEY=...
AGENT_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
WITHDRAW_TO=twelvedata.near
WITHDRAW_THRESHOLD=1.0
```

```bash
chmod 600 .env
docker compose up -d
docker compose logs -f caddy   # confirm Let's Encrypt cert issuance
```

Verify:

```bash
curl https://near-ai.twelvedata.com/health
curl -X POST https://near-ai.twelvedata.com/invoke \
  -H "Content-Type: application/json" \
  -d '{"input": {"function": "QUOTE", "symbol": "AAPL"}}'
```

## 5. Install the cron

```bash
crontab /opt/near-ai-agent-market/crontab.txt
sudo touch /var/log/near-ai-withdraw.log
sudo chown deploy:deploy /var/log/near-ai-withdraw.log
```

Test once manually:

```bash
cd /opt/near-ai-agent-market
docker compose run --rm cron
```

Confirm a Telegram message arrives.

## 6. Set up GitHub Actions auto-deploy

In the GitHub repo → **Settings → Secrets and variables → Actions**, add:

| Secret | Value |
|---|---|
| `VPS_HOST` | VPS IP or hostname |
| `VPS_USER` | `deploy` |
| `VPS_SSH_KEY` | Private SSH key (matching the pubkey in `/home/deploy/.ssh/authorized_keys`) |

Push any commit to `main` — the workflow in `.github/workflows/deploy.yml` will SSH in, `git pull`, and `docker compose up -d`.

## 7. Update marketplace registration

Once `https://<your-domain>/invoke` is live, update `service-registration.json`:

```json
"endpoint_url": "https://near-ai.twelvedata.com/invoke"
```

Then follow `REGISTRATION.md` to re-register the service on the marketplace.

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `TWELVE_DATA_API_KEY` | Yes | Your Twelve Data API key |
| `OPENAI_API_KEY` | No | Enables natural language queries via Twelve Data's MCP utool server |
| `PROXY_SECRET` | No | If set, requests must include `Authorization: Bearer <secret>`. Do NOT set in production — the marketplace does not forward auth headers. |
| `TD_MCP_BASE_URL` | No | Override Twelve Data MCP base URL (default: `https://mcp.twelvedata.com`) |
| `AGENT_API_KEY` | Yes (cron) | NEAR AI marketplace API key, for balance/withdraw |
| `TELEGRAM_BOT_TOKEN` | Yes (cron) | Telegram bot token for the daily report |
| `TELEGRAM_CHAT_ID` | Yes (cron) | Telegram chat/user ID to message |
| `WITHDRAW_TO` | No | Destination NEAR account (default: `twelvedata.near`) |
| `WITHDRAW_THRESHOLD` | No | Withdraw if balance exceeds this (default: `1.0`) |

## Troubleshooting

- **Caddy can't get a cert**: check DNS actually points at the VPS (`dig`), and that ports 80/443 are open in the Hetzner firewall.
- **`docker compose` not found**: install the compose plugin (`apt-get install docker-compose-plugin`), not the old `docker-compose` v1.
- **Action fails on SSH**: confirm `VPS_SSH_KEY` is the full private key including header/footer lines, and that the matching pubkey is in `authorized_keys`.
