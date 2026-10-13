# Plan — Smart Money / Whale Influence on Bitcoin: Research Report

**Mode:** research report only (no app code, no backtest engine).
**Data policy:** free / open sources only.
**Coverage:** both trading horizons — (a) daily swing bias, (b) intraday + scalping triggers.
**Deliverable (SEPARATE REPO — KFlow untouched):** this repo `btc-smart-money-research`. Main report `docs/BTC_SMART_MONEY_INFLUENCE.md`, plus reproducible `scripts/` + `data/` + `analysis/` output, `findings.md`, `progress.md`.

---

## 1. Goal

Answer, with sourced evidence, the user's four questions:

1. **Who** are the market makers / takers / institutions / banks / hedge funds / whales that trade BTC daily and effectively set market direction?
2. **How much influence** do they measurably have on price (quantified, from academic + industry studies)?
3. **How does their positioning data compare** with BTC price movement — do price and direction follow them, and with what lag?
4. **Which confluences**, built from free data, are actually usable for daily bias + intraday/scalping execution?

Report must be honest: separate *influence* from *predictability*, and document the known traps (T+1 ETF lag, weekly COT lag, exchange-housekeeping false positives, market-maker hedges ≠ directional view).

---

## 2. Research already gathered (source material, no further search strictly required)

### 2.1 The cast (named players + free observability)
| Cohort | Who | Free way to observe them |
|---|---|---|
| Market makers | Wintermute, Jump Crypto, Jane Street, Citadel, GSR, Cumberland, Flow Traders, QCP | Wintermute public market updates + labeled Hyperliquid perp positions (Aug 2026: ~$191–211M shorts incl. $70.8M BTC); exchange labeled wallets |
| Institutions / ETFs | BlackRock IBIT (~798.7k BTC), Fidelity FBTC (184k), Grayscale GBTC+BTC (190k), Bitwise, ARK, VanEck, MSBT (Morgan Stanley), Franklin, Invesco, WisdomTree — **US spot ETFs hold ~1,289,507 BTC = 6.14% of supply / ~$108.5B** | Bitbo.io, CoinClass, SoSoValue, Newhedge free daily flow tables |
| Banks / brokers | Standard Chartered (research), JPMorgan, Goldman, BNY Mellon (custody), Morgan Stanley (MSBT ETF), Wintermute's new US broker-dealer | 13F/press; MSBT flows |
| Hedge funds / basis traders | CME "leveraged funds" (Capula, Millennium, GoldenTree, Tudor, Ruffer class of player) | **CFTC COT free CSV** (CME Bitcoin, CFTC code 133741 / 133741 TFF), CryptoQuant CME net-position charts |
| Corporate treasuries / DATs | Strategy, Tesla, Block, Metaplanet | Treasury disclosure sites (bitbo.io), their filings |
| On-chain whales | 10k+ BTC cohort; 1,303 entities ≥1,000 BTC (Jan 2026); exchanges, miners (MARA/Riot), governments (US/UK/El Salvador), Mt. Gox trustee | Free Glassnode/CryptoQuant charts, Whale Alert free web feed, public explorer labels |
| Aggressive takers (the mass) | Perp traders taking liquidity | **Public exchange WS** — taker buy/sell, CVD, OI, funding, liquidations (KFlow already ingests all of these) |

### 2.2 Quantified influence evidence (core of "how much")
- **Lim (2026, SSRN 6592830), "The Price Impact of Spot Bitcoin ETF Flows"**: +$100M net ETF flow ⇒ **+53 bp same-day BTC return** (Kyle's λ 53 bp/$100M OLS; 74 bp IV, first-stage F=21.58); flows explain **21% of daily return variance (t=8.99)**; **predict next-day returns (Newey–West t=3.12)**; Granger **bidirectional** (β=0.47, t=9.75); cumulative impact **96 bp/$100M at 10 days**; "flow-persistence illusion" — individual shocks reverse, persistence mimics permanence.
- **Mazur & Polyzos (SSRN, 2025)**: net ETF flows **R²=95% vs BTC price *levels***; daily flows >5× daily mined BTC; **most BTC price change occurs *outside* ETF trading hours**; price rise → abnormal ETF volume (reverse causality).
- **Shen et al. (2025, ScienceDirect, "The role of whale investors in the bitcoin market")**: whale traders are a subset of **trend traders**; raising whale share 1%→8% ⇒ **intraday volatility +55%**; whale trades cause connected traders to follow in the next trade; whales ⇒ **daily volatility +104%**.
- **Order-flow literature (EFMA 2024)**: lagged order flow uncorrelated with lagged returns **significantly predicts** future crypto returns (t=5.54); permanent-component view supported.
- **Meta-order impact (arXiv 1412.4503)**: BTC obeys **square-root impact law, δ≈0.5** — a single large metaorder's price effect scales with √size (why whale prints matter intraday).
- **CME leads spot** (SEC/NYSE Arca price-discovery study): futures market leads spot — CME positioning/session is the intraday tell.
- **Wintermute H1 2026 OTC report**: institutions = **record 72% of spot OTC flow** (vs 61% H2'25, 59% H1'25); institutional activity after a price surge **fades in ~1 day** vs ~3 days for retail; yield/option flow **dampens** majors' day-to-day vol.
- **Glassnode cohort behavior (dated, checkable against price)**: whales (10k+) first to buy April-2025 $75k lows; shifted to distribution before May-2025 top; Aug–Oct 2025 3-month distribution while retail accumulated (BTC fell from ATH to $76–80k); **flip to accumulation w/c 27-Nov-2025 (ATS 0.8) → BTC reclaimed $90k**; Jan-2026 10k+ cohort the *only* net accumulators at $78k while retail sold.
- **CME COT, Aug 10 2026**: leveraged funds **flipped net long** for first time in years (basis trade unwinding as 3M basis ~3% < 2Y Treasury 3.8%) — a rare structural positioning shift.
- **Counter-evidence / trap**: Jan 2 2026 — apparent "whale accumulation" was **exchange cold-wallet housekeeping**; after filtering, actual 1k+ whales were net sellers (CryptoQuant, Julio Moreno). Balance fell 3.2M → 2.9M BTC through December.

### 2.3 Free data sources identified
CFTC COT (cftc.gov CSV / tradingster.com), Bitbo ETF flow table, CoinClass/SoSoValue/Newhedge ETF flows, Glassnode free charts, CryptoQuant free tier (10k credits/mo, market data only, 30-day history — on-chain needs paid), Whale Alert ($29.95+ API; free web/X feed), mempool.space/blockchain.com explorer, public exchange WS (KFlow connectors already), Hyperliquid leaderboard + `clearinghouseState`, Fear & Greed (alternative.me), DXY/macro.

---

## 3. Report structure (the document to write)

`docs/BTC_SMART_MONEY_INFLUENCE.md`

1. **Executive summary** — one page: who moves BTC, how much, what's exploitable at each timeframe, what's a trap.
2. **The map of holders** — tiered table (market makers → institutions/ETFs → banks → hedge funds/basis → treasuries → on-chain whales → miners/govs → retail), each with: what they do, how they set direction, free observation method, refresh cadence, lag.
3. **Evidence: how much influence do they have** — quantified section (§2.2 above), each claim with citation + date + number. Include a "measured influence ranking" table (influence vs horizon vs signal latency).
4. **Comparison vs price** — dated case studies (whale ATS flips, ETF flow streaks, COT flips, Wintermute positioning) laid against what BTC actually did next; plus explicit **what does NOT work** (reverse causality, lag, false positives).
5. **Free-data confluence stack** — the practical output:
   - **Daily bias layer** (overnight → session open): COT Δ, ETF 5-day flow, whale cohort ATS, exchange netflow/whale ratio, stablecoin mint, funding/OI/basis regime, Fear&Greed + DXY. Scoring table 0–10.
   - **Intraday/scalping layer**: taker buy/sell per venue, cross-venue CVD divergence, OI Δ + liquidation sweep, big/whale prints, exchange-inflow whale tx, CME open/lead, ETF-session vs off-session behavior (Mazur finding). Trigger rules + invalidation.
   - **Session/time window table** (Asia/EU/US, CME Globex open, US ETF window 14:30–21:00 UTC) with what each window is dominated by.
   - **Confluence matrix**: which combos are aligned / mixed / do-not-trade.
6. **Known traps & limitations** — T+1 ETF reporting, COT weekly/Tuesday snapshot, exchange-housekeeping false positives, market-maker short ≠ bearish (inventory hedge), basis-trade distortion of COT, bidirectional Granger causality, survivorship of "whale guru" narratives, liquidation cascades overriding flow.
7. **Appendix: source access sheet** — URL, endpoint, cost ($0), refresh cadence, history depth, gotchas; and the list of what *would* upgrade this (CryptoQuant Pro / Glassnode / Arkham) if budget ever opens.
8. **Not financial advice / not an execution venue** disclaimer (repo README tone).

---

## 4. Execution steps

1. Repo already scaffolded (`docs/ data/ scripts/ analysis/`). Create `findings.md`, `progress.md`.
2. **Verification searches (small, targeted)** — only to firm up facts the report states as actionable:
   - CFTC COT exact free download URL + CME Bitcoin contract codes (133741 legacy / TFF) and release cadence.
   - CME Bitcoin futures Globex session hours + US spot ETF regular trading hours (for the session-window table).
   - Confirm current US spot ETF total BTC & latest 5-day flow figures (already have: 1,289,507 BTC; recent daily flows).
   - Confirm Glassnode free-chart availability for Accumulation Trend Score by cohort (no API) and CryptoQuant free-tier limits (have: 10k credits, 30d, market-data only).
   - Free stablecoin net-issuance tracker (Tether/Circle mint) endpoint.
3. Write `docs/BTC_SMART_MONEY_INFLUENCE.md` per §3 (target ~2,500–4,000 words, tables-heavy, every number sourced with URL + date).
4. Write `findings.md` (key takeaways + the ranked influence table) and `progress.md` in this folder.
5. **Verify**: every numeric claim in the report must have a source line OR be reproducible from `scripts/` + `data/`; re-run scripts to confirm numbers; `git status` in KFlow must show no new/changed files from this work.

## 5. Out of scope (explicit)

- **No KFlow changes at all** — separate repo per user instruction (no code, no feeds, no `:wallet-intel`).
- No self-run statistical backtest (user chose research report, not backtest study) — but the report will cite existing measured studies and dated case comparisons.
- No paid APIs.

## 6. Risks / open questions

- Some free chart sources (Glassnode) have no API → report documents the *chart-reading* workflow, not an automated feed (noted as a limitation).
- ETF flow data publishes T+1 → daily-bias layer must state "yesterday's flow".
- Report is a snapshot (Oct 2026 market structure); numbers drift — include an "as of" date on every table.
