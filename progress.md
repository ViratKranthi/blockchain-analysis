# Progress

## Done

- **Repo setup** — separate git repo `btc-smart-money-research` (KFlow untouched; `.planning/` work folder removed from KFlow; KFlow's 5 pre-existing modified files left as-is).
- **Data pipeline** (all verified working):
  - `01_fetch_btc_klines.py` → daily 3,345 / hourly 24,399 / 15m 5,760 candles (Binance klines, taker-buy vol = field 9)
  - `02_fetch_etf_flows.py` → Farside full history 707 rows; validated total **$57,112m** (= Farside Total row); browser UA required; negative-sign parse bug fixed
  - `03_fetch_cot.py` → CFTC TFF contract 133741, 444 weeks (2018-04 → 2026-10-06) via Socrata
  - `04_fetch_positioning.py` → funding history 7,771 rows (pagination + stall guard fixed) + Binance 30d positioning metrics
  - `05_build_panel.py` → `analysis/panel_daily.csv` (merged signals, z-scores, pctile ranks)
  - `06_analysis.py` → sections A–H → `analysis/RESULTS.md` + 22 CSVs in `analysis/results/`
- **Analysis complete** — ETF OLS+lead-lag+regime splits, COT extremes, taker deciles, funding regimes, confluence cells, hourly session study, 7 dated case studies, robustness (Welch t, binomial, H5 lag scan, H6 live snapshot).
- **Report written** — `docs/BTC_SMART_MONEY_INFLUENCE.md` (all 8 planned sections incl. 0–10 daily-bias score, intraday triggers, session table, confluence matrix, traps, free-source access sheet).
- **findings.md** written.
- **Interactive dashboard** — `app/index.html` (zero-dependency static SPA):
  - `app/build_data.py` bundles panel + ETF + COT + hourly aggregates + all 22 result tables into `app/data.js` (~250 KB)
  - Sections: Overview KPIs · **interactive Bias Console** (0–10 scorer, live) · ETF flows (bars+cum, buckets, latest-by-fund, regimes) · Takers & Funding (history + extreme-decile forward returns) · CME COT (8-yr chart + contrarian table) · Lead–Lag (the "does flow lead?" chart) · Sessions (window table + hour-of-day) · Case Studies (✅/❌/➖) · Confluence matrix + time-factors · Raw results (all 22 tables, collapsible) · Sources sheet
  - Hand-rolled SVG charts (no CDN, works offline via `file://`)
  - Verified in headless Chromium; fixed: unquoted `%` object keys, null-safe path builder, COT fraction→% display, grid `min-width:0`, event verdict column keys, funding z-scale clipping, lag-label clipping
- **Live local dashboard** — `app/server.py` + `app/live_fetch.py` + Today section in `index.html`:
  - `live_fetch.py`: cached pull (TTL intraday 5min / ETF 6h / COT 24h) of daily+hourly klines, funding, premium, OI, OI hist, taker/global/top L-S ratios, Farside ETF (lxml flavor), CFTC COT (`report_date_as_yyyy_mm_dd` field; 60-week history for percentile); `build_snapshot()` + `compute_bias()` (0–10 with per-factor reasons) + `who_is_winning()` (7 cohorts → weighted verdict + price confirmation); standalone CLI writes `app/cache/latest_snapshot.json`
  - `server.py`: stdlib `ThreadingHTTPServer` on 127.0.0.1:8765 (`KFLOW_DASH_PORT`), routes `/api/today[?force=1]` (30s in-process cache + lock, stale fallback), `/api/history`, `/api/cache`, `/api/refresh`, background pre-warm
  - **Today** section in `index.html`: live strip, verdict bar (NOBODY 2–2 etc.), 7 player cards, auto-scored bias factors, 14-day tape table, 24h taker spark, source-freshness chips; `file://` fallback message
  - Browser-verified: all live elements render, zero console errors; fixed premium `lastPrice` missing (use markPrice), COT 400 (wrong date field), ETF `read_html` (needs `StringIO`+`flavor="lxml"`), hourly x-labels (show HH:MM)
- **Professional UI redesign** — complete visual overhaul of `app/index.html`:
  - Design system: warm-dark trading-terminal palette (`#090b0f` bg, gold `#c9a54c` accent), CSS custom properties for all colors/radii/type
  - Typography: system stack + monospace for all numbers, tabular-nums, proper type scale
  - Layout: hero price block (36px monospace), **control meter** (tug-of-war bar — signature element), player cards with left accent borders, consistent 8px grid
  - All sections restyled: KPIs with gold top-accent, proper table headers, session color bar, confluence matrix, source chips
  - `prefers-reduced-motion` respected, focus-visible rings, custom scrollbar
  - Verified in browser: hero strip (8 stats), control meter (NOBODY 2–2), 7 player cards, bias factors, ETF charts, all render cleanly
- **Server lifecycle clarified** — server only runs when launched via `python app/server.py` (not 24/7); one warm fetch on start; cache capped small
- **Port-in-use fix** — `server.py` sets `allow_reuse_address = True`; on Errno 48 prints kill command (`lsof -ti :8765 | xargs kill -9`) and auto-tries next 4 ports; `server_close()` on Ctrl-C
- **Expanded whale cohorts (15 total)** — all free, no API keys, storage-aware:
  - New fetchers in `live_fetch.py`: Coinbase spot + USDT-USD premium (US institutions + dry powder), Bybit ticker + top-trader L/S, OKX ticker + retail L/S (6s timeout — geo-block safe), Deribit DVOL + options put/call OI (reduced to 6 numbers before cache), Binance quarterly basis (nearest expiry, annualized), L2 order-book imbalance (top-100 bid/ask ratio), whale prints (large-body hourly candles derived, no extra API)
  - `who_is_winning()` expanded from 7 → 15 cohorts with per-cohort reasons + lag + weight
  - `compute_bias()` expanded from 6 → 10 factors (added Coinbase premium, Deribit P/C, order-book imbalance, stablecoin premium); range ~−7 to +7
  - Cache capped via `_trim_cache()` — keeps `app/cache/` under 900 KB (currently ~300 KB)
  - UI player-card classifier updated for all new side labels (BUYERS/SELLERS/US BUYERS/CARRY LONGS/WHALE ACCUM etc.)
  - Sources table + source chips updated (22 sources tracked)
  - End-to-end verified: 15 cards render, 10 bias factors, 22 source chips, cache 299 KB, OKX gracefully errors when geo-blocked
- **Week 1 Foundation — FastAPI backend**:
  - `pyproject.toml` — project metadata, deps, ruff/mypy/pytest config
  - `app/config.py` — pydantic-settings (env-overridable: port, TTLs, cache ceiling, CORS)
  - `app/models.py` — Pydantic models: Snapshot, Bias, Players, PriceInfo, FundingInfo, OIInfo, EtfInfo, CotInfo, CrossExchange, OptionsInfo, TapeDay, HistoryRow, HealthResponse
  - `app/db.py` — SQLite persistence (aiosqlite): `snapshots` table (price, bias, winner, payload JSON), `cache_meta`; `init_db`, `save_snapshot`, `latest_snapshot`, `snapshot_history`, `snapshot_count`
  - `app/api.py` — FastAPI app: `/healthz`, `/api/v1/today` (typed), `/api/v1/bias`, `/api/v1/players`, `/api/v1/history`, `/api/v1/refresh`, `/api/v1/cache`, `/ws/today` (WebSocket push), `/docs` (Swagger), legacy routes preserved; lifespan warm-fetch + SQLite init; CORS; lazy asyncio.Lock (event-loop safe)
  - `app/main.py` — uvicorn entry point
  - **40 tests passing** (`tests/conftest.py`, `test_bias.py`, `test_players.py`, `test_api.py`)
  - **ruff: all checks passed** · **mypy: no issues** (new modules)
  - End-to-end verified: healthz, today (15 players, MILD BEAR), bias (10 factors), players, cache (12 DB snapshots), history, Swagger `/docs`, WebSocket push — all working
- **Week 2 — Multi-asset + frontend**:
  - `app/assets.py` — `AssetConfig` dataclass for BTC/ETH/SOL: binance symbols, Bybit, OKX, Deribit, Coinbase product, ETF flag, COT code, accent color
  - `live_fetch.py` fully parameterized — every fetcher accepts `asset="BTC"` with per-asset cache keys (`ETH:daily`, `SOL:funding`); `build_snapshot(asset)` returns per-asset snapshot with `asset` + `asset_name` keys
  - API multi-asset: `GET /api/v1/assets`, `GET /api/v1/today?asset=ETH|SOL`, per-asset in-process cache, per-asset SQLite history
  - Frontend: **asset switcher** (BTC/ETH/SOL buttons with per-asset accent colors), hero label updates, ETH verified end-to-end (price 2511, 14 players, no COT)
  - SOL auto-skips ETF/COT/options (11 players — only available cohorts)
- **Week 3 — Features**:
  - **Alert engine** (`app/alerts.py`): 7 default rules (bias_flip, bias_threshold, etf_flow, funding_extreme, taker_extreme, whale_print, price_move) with cooldown store; evaluated after each snapshot build; Discord webhook support (`KFLOW_DISCORD_WEBHOOK_URL`); browser notification payload format
  - **Custom bias weights** (`app/weights.py`): 4 presets (balanced/conservative/aggressive/institutional), per-factor weights 0–3×, persisted to `app/cache/bias_weights.json`; `apply_weights()` re-scales factor points and recomputes score/state
  - API: `GET/POST /api/v1/weights`, `POST /api/v1/weights/apply`, `GET /api/v1/alerts`, `POST /api/v1/alerts/test`
  - Frontend: **alerts banner** (recent 3), **alerts list** (full history), **weight editor** (sliders per factor), **preset buttons** (balanced/conservative/aggressive/institutional), **WebSocket live push** (auto-reconnect, 60s fallback refresh)
  - **60 tests passing** (added `tests/test_features.py` — assets, alerts, weights)
  - **ruff: all clean** · **mypy: no issues** (all 8 modules)
- **v0.3.1 — Charts, playback, notifications**:
  - **TradingView Lightweight Charts** (v4.2.0 via CDN): candlestick + volume histogram, 1H/4H/1D timeframe switcher, live Binance klines (200 candles), per-asset symbol label, crosshair + zoom
  - **Historical playback**: `GET /api/v1/history/dates` (available dates), `GET /api/v1/history/{date}?asset=` (full snapshot for date); UI time-machine slider with ▶ Play animation (800ms/tick), LIVE button to return; hero + status bar reflect playback state
  - **Alert persistence**: `alerts` table in SQLite (`save_alerts`, `get_alerts`); all fired alerts stored on evaluate; `GET /api/v1/alerts/history?asset=&limit=`; frontend reads from SQLite first, falls back to in-memory
  - **Browser notifications**: `Notification.requestPermission()` on load; toast slide-in animation (bull/bear/info variants); WebSocket alerts → toast + native notification with tag dedup; 8s auto-dismiss
  - **64 tests passing** (added history dates, history 404, alerts history tests)
  - **ruff: all clean** · **mypy: no issues** (all 8 modules)

## Bugs fixed along the way

- Farside negative flows parsed as positive (sign stripped before `to_numeric`) — fixed with `(`/`)`/`,` strip then exact-`-`→0 map.
- Funding pagination infinite loop on empty page — stall guard added.
- ETF quintiles broken by zero-flow ties (qcut → 9-row bin) — replaced with explicit buckets.
- `ret_d1_bp` missing outside ETF slice — created on full panel.
- COT/taker coefficients reported in unusable units — rescaled to bp/1000 contracts and bp/+1pp.
- H2 column mislabeled bp/100m (was per $1m) — fixed ×100.
- Dashboard: JS `SyntaxError` from unquoted `mean_d1%:` object keys — auto-quoted.
- Dashboard: `pathFrom` crashed on `[x, null]` points — null-guard added.
- Dashboard: `parse_dates` failed on hourly CSV (col is `open_time` ms) — converted with `unit="ms"`.
- Dashboard: COT table showed `-0.0%` (fraction not ×100) — mapped columns to percent before render.
- Dashboard: verdict column empty — column key is `ret_d14%` (with percent sign), not `ret_d14`.
- Dashboard: grid columns squeezed by wide tables — `minmax(0,1fr)` + `min-width:0`.

## Next / open

- Commit this repo (initial commit pending — awaiting explicit go-ahead per policy).
- Optional: quarterly re-estimate runbook (`06_analysis.py` re-run + regime table H2 check + `build_data.py`).
- Optional (paid, out of scope): Glassnode ATS API, CryptoQuant Pro for automated whale layer.
- Optional: auto-refresh Today section every 5 min via `setInterval` + `/api/today` poll.
