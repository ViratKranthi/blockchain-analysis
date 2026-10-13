# btc-smart-money-research

Research report + **interactive dashboard**: who moves Bitcoin (smart money / institutions / whales), how much, and which free-data confluences are usable for daily swing bias and intraday/scalping.

- **Dashboard (start here):** [`app/index.html`](app/index.html) — open in any browser, no server needed
- **Report:** [`docs/BTC_SMART_MONEY_INFLUENCE.md`](docs/BTC_SMART_MONEY_INFLUENCE.md)
- **Key takeaways:** [`findings.md`](findings.md)
- **Plan:** [`PLAN.md`](PLAN.md)
- **Empirical output:** [`analysis/RESULTS.md`](analysis/RESULTS.md) + `analysis/results/*.csv`

## Open the dashboard

### Static (research snapshot, no server)

```bash
open app/index.html          # macOS — double-click works too
# or rebuild data first if you re-ran the analysis:
.venv/bin/python app/build_data.py && open app/index.html
```

### Live (today's flows, daily bias, who-is-winning)

**FastAPI (recommended):**
```bash
.venv/bin/python -m app.main          # → http://127.0.0.1:8765
# or: uvicorn app.api:app --port 8765
```

**Legacy stdlib server (still works):**
```bash
.venv/bin/python app/server.py        # → http://127.0.0.1:8765
```

**The server runs only while you have it open** — it is not a 24/7 background service. When you launch it, it does one quick warm fetch (a few seconds), then serves from small on-disk cache (total ~300 KB). Ctrl-C stops it. Total app footprint: **under 1 MB**.

If you hit `Address already in use` (Errno 48), a previous server is still running — kill it: `lsof -ti :8765 | xargs kill -9`.

**FastAPI endpoints** (auto-docs at `/docs`):

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Liveness + readiness probe |
| `/api/v1/today` | GET | Full live snapshot (Pydantic-typed) |
| `/api/v1/bias` | GET | Just the bias block |
| `/api/v1/players` | GET | Just the who-is-winning block |
| `/api/v1/history?days=90` | GET | Daily bias history from SQLite |
| `/api/v1/refresh` | POST | Force rebuild |
| `/api/v1/cache` | GET | Disk + DB stats |
| `/ws/today` | WS | WebSocket — pushes snapshots on rebuild |
| `/docs` | GET | Swagger UI |
| `/openapi.json` | GET | OpenAPI 3.1 spec |

Legacy routes (`/api/today`, `/api/history`, etc.) still work.

**SQLite history** — every snapshot is persisted to `app/cache/history.db`, giving you queryable time-series of price, bias score, winner, and taker share.

**The Today** section (top of the page) auto-refreshes from free live endpoints. It shows:

- Hero live price + today's return + funding countdown
- **Control meter** — tug-of-war bar showing which side controls the tape right now
- **Who is winning today** — **15 cohort cards** with a weighted verdict:
  - Aggressive takers (Binance perps)
  - Institutions (US spot ETFs, T+1)
  - CME hedge funds (COT, weekly)
  - Leveraged perp book (funding, 8h)
  - Retail accounts (Binance L/S)
  - Top trader positions (Binance)
  - New money (OI regime)
  - US institutions (Coinbase premium)
  - Bybit top traders
  - OKX retail accounts
  - Options desks (Deribit put/call OI)
  - Vol traders (DVOL)
  - Basis / carry desks (quarterly futures)
  - Market makers (L2 order-book imbalance)
  - Stablecoin / dry powder (USDT-USD)
  - Whale prints (large-body hourly candles, OTC proxy)
- Auto-scored bias factors (10 factors, ~−7 to +7) with plain-English reasons
- Last 14 days tape + 24h taker-share chart + source freshness (22 chips)

Endpoints: `/api/today` (live snapshot, cached 30s), `/api/history?days=90`, `/api/refresh`, `/api/cache`. Port via `KFLOW_DASH_PORT` (default 8765). When opened via `file://`, the Today section degrades gracefully with a start-server hint.

OKX endpoints may timeout from some regions — the dashboard handles this gracefully (cohort falls back to neutral).

What's in it:

| Section | What you see |
|---|---|
| **Overview** | 6 headline KPIs + full price history |
| **Bias Console** | Interactive 0–10 daily-bias scorer (ETF flow, taker share, COT, funding, ATS, F&G) |
| **ETF Flows** | Daily bars + cumulative line, flow-bucket returns, latest day by fund, regime split |
| **Takers & Funding** | Taker-share history, funding z, extreme-decile forward returns |
| **CME COT** | lf_net vs asset-mgr net over 8 years, contrarian decile table |
| **Lead–Lag** | The "does flow lead price?" answer in one chart (no — it co-moves) |
| **Sessions** | Where BTC actually moves: Asia/EU/US windows + hour-of-day heat |
| **Case Studies** | 7 dated events with ✅/❌/➖ verdicts |
| **Confluence** | What-to-trade / what-to-skip matrix + time-factor cards |
| **Raw Results** | All 22 analysis tables, collapsible |
| **Sources** | Free endpoint access sheet |

## Reproduce the analysis

```bash
python3 -m venv .venv && .venv/bin/pip install pandas numpy scipy statsmodels lxml requests
.venv/bin/python scripts/01_fetch_btc_klines.py
.venv/bin/python scripts/02_fetch_etf_flows.py
.venv/bin/python scripts/03_fetch_cot.py
.venv/bin/python scripts/04_fetch_positioning.py
.venv/bin/python scripts/05_build_panel.py
.venv/bin/python scripts/06_analysis.py   # writes analysis/RESULTS.md + results/*.csv
.venv/bin/python app/build_data.py        # refreshes app/data.js for the dashboard
```

## Development

```bash
.venv/bin/python -m pytest tests/ -q          # 40 tests
.venv/bin/ruff check app/ tests/              # lint (all clean)
.venv/bin/mypy app/config.py app/models.py app/db.py app/api.py app/main.py
```

Project layout:
```
app/
  config.py      # pydantic-settings — env-overridable knobs
  models.py      # Pydantic API models (Snapshot, Bias, Players, …)
  db.py          # SQLite persistence (aiosqlite)
  api.py         # FastAPI app — typed routes + WebSocket
  main.py        # uvicorn entry point
  live_fetch.py  # data engine — 20+ free endpoints, 15 cohorts
  index.html     # SPA frontend
  server.py      # legacy stdlib server (still works)
tests/
  conftest.py    # shared fixtures (full + minimal snapshots)
  test_bias.py   # compute_bias — 10 factors, thresholds
  test_players.py# who_is_winning — 15 cohorts, verdict
  test_api.py    # FastAPI endpoints — health, today, bias, cache
```

All data sources are free/open. Data policy, endpoints, and gotchas: report §7.

## Disclaimer

Research only. Not financial advice, not an execution venue. Numbers are an October-2026 snapshot; re-estimate quarterly. This repo is intentionally separate from any trading application — nothing here touches live systems.
