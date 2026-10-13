# Smart Money & Bitcoin: Who Actually Moves Price, How Much, and What Is Usable From Free Data

**As of:** 2026-10-13 (all tables; numbers drift — treat as an October-2026 market-structure snapshot)
**Scope:** research report only. No trading advice, no execution venue, no changes to any trading app.
**Empirical base:** this repo's own panel — 3,345 daily candles (2017-08-17 → 2026-10-13), 24,399 hourly candles (2024-01 →), 707 US spot ETF flow days (2024-01-11 →), 444 weekly CFTC COT reports (2018-04 →). Every self-computed number is reproducible from `scripts/` + `data/`; full tables in `analysis/RESULTS.md` and `analysis/results/*.csv`.

---

## 1. Executive summary

**Who moves BTC:** five cohorts, in descending measurable impact per unit of observable data:

1. **US spot ETF authorized participants + their underlying institutional flow** — largest *quantified* daily driver. Same-day impact ~**+32 bp per $100M net flow** in our 2024–2026 panel (t=9.7, R²≈14% of daily variance); academic IV estimate **+53 bp/$100M** and **21% of daily variance** (Lim 2026).
2. **Aggressive perp takers** (the mass of leveraged retail + prop flow taking liquidity on Binance/Bybit/etc.) — same-day **+31 bp per +1 pp taker-buy share** (t=3.3), and the only signal in our panel with clean *forward* power at 2–3 days.
3. **Hedge funds on CME** ("leveraged funds" in COT — basis/relative-value shops) — no daily predictive power; a **contrarian monthly** signal (when they are maximally net short, the next 4 weeks average +2.5%, p=0.003).
4. **On-chain mega whales (10k+ BTC)** — real *volatility* impact (+55% intraday / +104% daily volatility when their market share rises; Shen et al. 2025) but a **poor timing signal**: of 7 dated whale-accumulation events 2025–2026, only ~4 worked and 2 were catastrophically early (−17.6% and −18.3% over the following 2 weeks).
5. **Market makers** (Wintermute, Jump, Jane Street, Citadel, GSR, Cumberland…) — they *set the quote* and absorb metaorders; price impact of large metaorders follows the **square-root law δ≈0.5**. Their own directional positioning is mostly inventory/basis hedging and is **not** a readable free signal (except labeled Hyperliquid accounts, which lag and are tiny vs OTC).

**The central honest finding (our own lead-lag test):** positioning and price **co-move**; they do **not** lead it at daily horizon. ETF flow vs same-day return correlation peaks at **0.375** at lag 0/−1 and collapses to **~0.00 at +1…+3 days** (`analysis/results/h5_lag_corr.csv`). flows **confirm** the day's direction (and are partly *caused* by it); they do **not** forecast tomorrow. Academic next-day predictability (Lim: NW t=3.12) is sample-dependent — in our 2024–2026 panel (including the 2025–26 bear phase) the forward coefficient is only **3.4 bp/$100M, t=1.28, n.s.**

**What *is* exploitable at each timeframe, from free data only:**

| Timeframe | Usable signal (free) | Measured edge in our panel | Mechanism |
|---|---|---|---|
| Daily bias | **Bear confluence:** ETF 5-day flow < 0 **and** taker-buy share ≤ 0.5 | mean next-day **−0.18%** vs +0.09% baseline; 3-day −0.36% (p≈0.09) | persistent institutional supply meets no aggressive bid |
| Daily bias | **Extreme taker day** (top/bottom decile of taker-buy share) | next 2–3 days continue: +0.72%/−0.23% (d2, p=0.023), +0.89%/−0.44% (d3, p=0.011) | crowded aggressive flow takes time to unwind |
| Swing (1–4 wks) | CME hedge funds **maximally net short** (bottom decile of lf_net) | next 4 weeks **+2.46%** vs −1.50% when least short (t=−2.99, p=0.003) | basis-trade crowding → unwind is a buy |
| Swing (1–2 wks) | Funding z ≤ −2 (crowded shorts, n=30) | next week **+3.16%**, hit 66.7% | liquidation-squeeze regime |
| Intraday | **Time of day:** 13:00–15:00 UTC (US data + cash/ETF open) | 43–54 bp mean absolute hourly move vs 27–29 bp Asia/EU | institutional session is where metaorders land |
| Intraday | Taker imbalance + OI Δ + liquidation sweep on the live WS | (real-time; KFlow-style feeds already ingest these) | aggressive flow is the execution horizon where positioning *is* price |

**What does not work (traps, tested):** raw "big ETF inflow day → buy tomorrow" (same-day only; forward n.s.); weekly COT *level* as a trend signal (n.s. at 1–2 wks); funding rate alone as a long/short signal (linear R²≈0); "whales are accumulating" headlines as entry timing (see §4 — two dated −18% failures); treating market-maker shorts as bearish (inventory hedges).

---

## 2. The map of holders (who they are, how they set direction, how to watch them free)

| Tier | Cohort | Who (examples) | How they set direction | Free observation | Refresh | Lag |
|---|---|---|---|---|---|---|
| 1 | **ETF APs / institutional flow** | BlackRock IBIT (~799k BTC), Fidelity FBTC (~184k), Grayscale (~190k), Bitwise, ARK 21Shares, VanEck, Invesco, WisdomTree, Morgan Stanley MSBT; US spot ETFs ≈ **1,289,507 BTC = 6.14% of supply** (Bitbo, as of Oct 2026) | Creation baskets force APs to buy spot in size during US hours → permanent demand shock | **Farside** full history `farside.co.uk/bitcoin-etf-flow-all-data/` (needs browser User-Agent; total flows validated at $57,112m); Bitbo/SoSoValue/Newhedge mirrors | Daily, **T+1** (today's number publishes tomorrow) | 1 day (publication), 0 (impact) |
| 2 | **Aggressive takers (perps)** | Mass of leveraged retail/prop on Binance, Bybit, OKX, Hyperliquid | Taker flow *is* price at execution horizon; extreme days show 2–3 day continuation | Binance klines field 9 = taker-buy base volume (free, any timeframe); `www.binance.com/futures/data/takerlongshortRatio` (rolling 30d) | Real-time / 1m | ~0 |
| 3 | **Hedge funds / basis traders (CME)** | Capula, Millennium, GoldenTree, Tudor, Ruffer class; "leveraged funds" leg of COT | Mostly cash-and-carry (long spot/ETF, short CME) → structural short; *changes* = basis regime shifts | **CFTC TFF** Socrata `publicreporting.cftc.gov/resource/gpe5-46if.json`, contract `133741` (444 weeks fetched) | Weekly, **Fri release, data as of Tue** | ~3–5 days |
| 4 | **Market makers** | Wintermute, Jump Crypto, Jane Street, Citadel, GSR, Cumberland, Flow Traders, QCP | Quote/warehouse inventory; metaorder impact δ≈√size (Bucci et al.) — they transmit, not choose, direction | Wintermute public market updates; Hyperliquid labeled accounts (Wintermute ~$191–211M shorts Aug 2026 incl. $70.8M BTC); OTC share reports | Ad hoc | days |
| 5 | **Corporate treasuries / DATs** | Strategy, Tesla, Block, Metaplanet | lumpy program buying/selling | Bitbo treasuries, filings | Weekly/monthly | 1 week+ |
| 6 | **On-chain whales (10k+)** | exchange cold wallets, OTC desks, early holders; 1,303 entities ≥1,000 BTC (Jan 2026) | regime accumulation/distribution; first to buy Apr-2025 $75k lows (Glassnode ATS) | Glassnode free **Accumulation Trend Score** charts (read-only, no API); CryptoQuant free tier (10k credits/mo, market-data only, 30d); Whale Alert free web feed | Daily/weekly | 1 day (Glassnode delay) |
| 7 | **Miners / governments / custodians** | MARA, Riot; US (~200k seized), UK, El Salvador; BNY Mellon custody; Mt. Gox trustee | forced/lumpy supply | filings, explorer labels, mempool.space | Days–weeks | high |
| 8 | **Retail (for contrast)** | everything else | herds late; crowded-long funding is retail's fingerprint | funding rate, account long/short ratio (Binance) | 8h | ~0 |

---

## 3. Evidence: how much influence, quantified

### 3.1 US spot ETF flows — the biggest *measured* daily force

**Academic/industry (external, cited):**

| Study | Finding |
|---|---|
| Lim (2026, SSRN 6592830) | +$100M net flow ⇒ **+53 bp same-day** (OLS; 74 bp IV, first-stage F=21.58); **21% of daily return variance** (t=8.99); next-day predictability **NW t=3.12**; Granger **bidirectional** (β=0.47); cumulative **96 bp/$100M at 10 days** |
| Mazur & Polyzos (2025) | net flows explain **R²≈95%** of BTC price *levels*; daily flow >5× daily mined BTC; most price change occurs *outside* ETF hours (see §5.3 — reinterpreted by our session data); reverse causality present |
| Wintermute H1 2026 OTC report | institutions = record **72%** of spot OTC flow; institutional activity fades after ~1 day vs ~3 for retail |

**Our own panel (2024-01-11 → 2026-10-13, n=1,007 days; `a_etf_ols.csv`, HAC/NW t-stats):**

| Regression | bp per $100M | t | R² |
|---|---|---|---|
| ETF flow → **same-day** return | **+32.46** | **9.73** | **0.141** |
| ETF flow → next-day (d1) | +3.41 | 1.28 (n.s.) | 0.002 |
| ETF 5d flow → same-day | +3.58 | 3.95 | 0.017 |
| ETF 5d flow → d1 | +0.48 | 0.61 (n.s.) | 0.000 |

Same-day correlation **0.375** (Pearson); forward-day correlation **0.039** (`a_etf_corr.csv`). Lead-lag scan: correlation with returns peaks at lag −1/0 (0.33–0.38) and is ≈0 at +1…+3 (`h5_lag_corr.csv`) → **impact, not information**.

**Asymmetry (the useful part):** outflow days are worse than inflow days are good (`a_etf_quintiles.csv`, `h1_etf_outflow_asymmetry.csv`):

| Bucket (daily net flow) | n | mean next-day | hit% | mean d7 |
|---|---|---|---|---|
| strong outflow < −$250m | 92 | −9.6 bp | 43.5% | +0.46% |
| outflow −250…−50 | 156 | **−20.7 bp** | 47.4% | +0.33% |
| flat | 411 | +23.5 bp | 55.0% | +0.62% |
| inflow 50…250 | 170 | +2.5 bp | 46.5% | +0.46% |
| strong inflow > +$250m | 177 | +16.7 bp | 52.0% | **+1.32%** |

Pooled outflow days (n=248): **−16.6 bp** next-day vs **+17.2 bp** for all other days; t=−1.78, **p=0.076**; outflow-day hit rate 46.0% (binomial p=0.23 vs 50%). Not a standalone trade — a **bias overlay**. Regime split (`h2_etf_regimes.csv`): same-day co-movement is stable across 2024/2025/2026 (corr 0.33 / 0.30 / **0.58**); the 2026 next-day coefficient is larger (+10.0 bp/$100m) but still small in economic terms.

### 3.2 Aggressive takers (Binance perp) — the only clean *forward* signal at 2–3 days

Daily taker-buy share = taker buy volume / total, from klines field 9 (n=3,344 days, 2017→).

| Regression | bp per +1 pp share | t | R² |
|---|---|---|---|
| taker share → same-day | **+30.9** | **3.30** | 0.085 |
| → next-day | +2.5 | 1.12 (n.s.) | 0.001 |

Extreme days **do** predict continuation (`c_taker_extremes.csv`, Welch t):

| Group (decile of taker-buy share) | n | mean share | d1 | **d2** | **d3** |
|---|---|---|---|---|---|
| HIGH (buyers dominant) | 335 | 55.1% | +0.43% | **+0.72%** (p=0.023) | **+0.89%** (p=0.011) |
| LOW (sellers dominant) | 335 | 43.9% | −0.15% | **−0.23%** | **−0.44%** |

Interpretation: a full day of one-sided aggressive flow is a *positioning imbalance* that takes 48–72 hours to work off — long enough to matter for swing entries, short enough to gate intraday continuation trades.

### 3.3 CME hedge funds (COT) — no daily edge, contrarian monthly edge

Leveraged-fund net position (contracts; structurally negative = basis trade), weekly Tue snapshot, Fri release, n≈3,100 weeks (`b_cot_ols.csv`, `b_cot_extremes.csv`):

| Signal | Result |
|---|---|
| lf_net level → d7/d14 | n.s. (t≈0.75), R² < 0.2% |
| lf_net **level** decile → **d28** | bottom decile (most net short, ≈ −19,089 contracts) → **+2.46%** vs top decile (≈ −6) → **−1.50%**; **t=−2.99, p=0.003** |
| lf_net weekly **change** top decile | d7 +1.99%, **hit 60.4%**; d14 +2.46%, hit 65.8% (mean-vs-mean difference n.s.; within-group hit rate binomial-p ≈ 0.0001) |

Read: when basis traders are *maximally short CME*, the monthly forward return is positive (squeeze/unwind); when they are *least short*, forward returns are worst. This is a **regime/contrarian** signal, not a trend-following one — and it is contaminated by the basis trade's popularity correlating with bull markets (see traps).

### 3.4 Funding rate — crowded-short contrarian only

Funding z-score (7-day rolling mean / rolling std; n=2,531) has **no linear** predictive power (R²≈0). Extremes (`d_funding_regimes.csv`):

| Regime | n | mean d7 | hit d7 | mean d14 |
|---|---|---|---|---|
| z ≥ +2 (crowded long) | 99 | +1.15% | 53.5% | +0.51% |
| **z ≤ −2 (crowded short)** | **30** | **+3.16%** | **66.7%** | **+3.08%** |
| neutral | 2,092 | +0.75% | 52.0% | +1.88% |

Crowded-long funding does **not** precede crashes in this sample; crowded-short does precede outsized weekly rallies (small n — use as confirmation, not standalone).

### 3.5 On-chain whales — volatility effect real, timing effect weak

External: Shen et al. (2025) — whale traders are a *trend-trader* subset; raising whale share 1%→8% ⇒ **intraday vol +55%**, **daily vol +104%**; connected traders follow whale trades with one-trade lag. Bucci et al. — metaorder impact scales **√size (δ≈0.5)**: a $50M print moves ~7× less than a $2.5B program, not 50× less — why *sustained* whale programs, not single prints, are what matter.

Our dated event study (§4) shows the **signal is regime-level, not entry-level**.

### 3.6 Measured influence ranking

| Rank | Cohort | Impact per observable unit | Works at | Signal latency | Free? |
|---|---|---|---|---|---|
| 1 | ETF flow (institutional via APs) | 32–53 bp / $100M **same-day**; 14–21% of variance | daily (impact); weak/asymmetric daily (bias) | 0 (impact) / 1d (publication) | yes |
| 2 | Aggressive perp takers | 31 bp / +1 pp share same-day; deciles → 2–3 d continuation | intraday + 2–3 d | ~0 (WS) | yes |
| 3 | Hedge funds (CME COT) | contrarian +2.5% / 4 wks at max-net-short decile | 2–4 wks | 3–5 d | yes |
| 4 | Funding/OI (crowded shorts) | +3.2% / week at z≤−2 | 1–2 wks | 0 | yes |
| 5 | On-chain whales | vol multiplier +55–104%; direction regime only | weeks | 1 d | charts-only |
| 6 | Market makers | δ≈√size transmission; OTC 72% institutional | intraday mechanics | labeled wallets lag | partial |
| 7 | Miners/governments | lump supply events | event-driven | days | yes |

---

## 4. Comparison vs price — dated case studies (what smart money did → what BTC did next)

Event dates from public reports (Glassnode weekly ATS commentary, CryptoQuant/COT); returns computed from our daily closes (`g_events.csv`):

| Date | Event (source) | Close | d1 | d3 | d7 | d14 | Verdict |
|---|---|---|---|---|---|---|---|
| 2025-04-08 | Whales 10k+ buying tariff-tantrum lows ~$75k (Glassnode ATS) | $76,322 | **+8.3%** | +9.3% | +9.6% | **+22.4%** | ✅ worked |
| 2025-11-07 | Whale ATS flip back to accumulation after 3 months selling (Glassnode) | $103,339 | −1.0% | +2.6% | −8.5% | **−17.6%** | ❌ **failed badly** |
| 2025-11-27 | ATS 0.8 strong accumulation; BTC reclaims $90k | $91,334 | −0.5% | −1.1% | +0.8% | +1.3% | ➖ flat |
| 2026-01-30 | Mega-whales sole accumulators at ~$78k while retail sells | $84,260 | **−6.6%** | −6.6% | **−16.2%** | **−18.3%** | ❌ **failed badly** (dip kept dipping) |
| 2026-04-22 | All ETF rolling flow periods positive; IBIT +$246.9m | $78,178 | +0.1% | −0.7% | −3.1% | +4.2% | ➖ mixed |
| 2026-08-10 | CME leveraged funds flip net long for first time in years | $63,970 | −0.6% | −0.8% | +0.9% | **+23.5%** | ✅ worked (after ~2 wks) |
| 2026-10-07 | ETF outflow $484.9m (largest recent) | $83,322 | **−1.9%** | −0.4% | — | — | ✅ worked (short horizon) |

**Score: 3 clear wins, 3 flat/mixed, 2 catastrophic losses.** Whale-accumulation headlines are a **slow regime overlay** (weeks), never an entry trigger. Note also the documented false positive: the 2026-01-02 "whale accumulation" print was **exchange cold-wallet housekeeping** — after filtering, real 1k+ whales were *net sellers* (CryptoQuant, J. Moreno). Any on-chain signal that ignores transfer-context will generate exactly this class of trap.

**What does NOT work (summary of our tests):**

1. **"Big inflow day → long tomorrow"** — forward coefficient 3.4 bp/$100m, t=1.28, n.s.; decile spread t=0.63. Impact is same-day only.
2. **COT level as a trend following signal** — t<1 at 1–2 weeks.
3. **Funding rate alone** — linear R²≈0 at d1/d7/d14.
4. **Crowded-long funding as a crash signal** — z≥+2 weeks averaged **+1.15%** over the next week (no crash premium in this sample).
5. **Single-day taker spike at daily horizon** — level regression n.s.; only the *deciles* (extremes) carry forward power, at 2–3 days.
6. **Whale ATS as timing** — 2 of 7 events lost −17% and −18% over two weeks.

---

## 5. Free-data confluence stack (the practical output)

All inputs below are $0 endpoints verified in this repo (`data/` + `scripts/04…06`).

### 5.1 Daily bias layer — score from 0 to 10 (computed after the US close, using *yesterday's* published data)

| # | Input (free source) | Bull points | Bear points | Weight rationale (our evidence) |
|---|---|---|---|---|
| 1 | **ETF 5-day net flow** (Farside, T+1) | > 0 → **+2**; > +$1B → **+3** | < 0 → **−2**; < −$500m → **−3** | NEG/NEG bucket −0.18%/day vs +0.09% baseline; outflow asymmetry p=0.076 |
| 2 | **Taker-buy share vs 0.5** (Binance klines, last 24h) | ≥ 55th pctile → **+2** | ≤ 45th pctile → **−2** | decile continuation d2/d3 p=0.023/0.011 |
| 3 | **CME lf_net weekly change** (CFTC TFF, as-of Tue) | top decile add → **+1** | — (no reliable bear edge) | top-decile hit 60.4% d7 |
| 4 | **CME lf_net level vs 1y range** | bottom decile (max short) → **+2** (contrarian) | top decile (least short) → **−1** | d28 t=−2.99 |
| 5 | **Funding z (7d)** | z ≤ −2 → **+2** | — | +3.16% d7, n=30 |
| 6 | **Whale ATS** (Glassnode free chart, read manually) | ATS ≥ 0.7 → **+1** | ATS ≤ 0.3 → **−1** | regime only (§4) |
| 7 | **Fear & Greed** (alternative.me, free JSON) | ≤ 25 (extreme fear) → **+1** | ≥ 75 → **−1** | contrarian overlay, untested here — *lowest weight* |

**Scoring → bias state:**

| Score | State | Rule |
|---|---|---|
| ≥ +6 | Strong bull | only longs (or stand aside on shorts); expect continuation |
| +2…+5 | Mild bull | longs with tighter invalidation |
| −1…+1 | **Neutral / chop** | **no daily-bias trades** — baseline hit rate is ~50.8% (coin flip) |
| −5…−2 | Mild bear | only shorts |
| ≤ −6 | Strong bear | only shorts (or stand aside on longs); outflow asymmetry helps here |

**Empirical anchor:** the two-factor core of this score (ETF 5d sign × taker sign) already separates regimes in our panel (`e_confluence.csv`): both-negative → **−0.179%** mean next-day (hit 48.4%), **−0.356%** mean over 3 days; all other cells ≥ +0.119% (hit 52.9–53.1%). The both-negative cell is also worse than the rest at conventional 10% levels (d1 p=0.13, d3 **p=0.09**, `h4_confluence_sig.csv`). Adding tiers 3–5 uses only confirmed-weak-but-directional edges — treat the composite as a **bias, never as a signal to fire blind**.

### 5.2 Intraday / scalping layer (real-time free streams)

| Trigger | Setup | Invalidation | Evidence type |
|---|---|---|---|
| **Taker imbalance burst** | 5–15m taker-buy share ≥ 60% on 2+ venues (Binance/Bybit/OKX WS), OI rising | share < 50% within 2 candles, or OI falling into the move (no new money) | aggressive flow *is* price at this horizon (§3.2) |
| **Liquidation sweep + reclaim** | OI spike + wick through a session high/low, price reclaims within 1–2 candles | close beyond the sweep extreme | crowded funding regime (§3.4) |
| **ETF-window continuation** | After 15:00 UTC, continue in direction of the 14:00–15:00 UTC move *if* today's (early) ETF-flow reports are aligned | reversal of the 13:00–15:00 UTC range | US window = 36.1% of all absolute movement (§5.3) |
| **CME open impulse** | 22:00 UTC Globex open: first 30 min range sets the overnight reference; trade breaks of that range only with taker-flow confirmation | mid-range chop = no trade | CME leads spot in price-discovery studies; overnight window is thin |
| **Do NOT scalp on** | COT release (Fri 19:30 ET), ETF flow headline prints (T+1 morning), 13:30 UTC US data | — | data/flow already lags or is simultaneous |

Cross-venue **CVD divergence** (spot CVD up, perp CVD flat → smart-money spot bid vs retail perp hesitation) is a standard free-stream pattern; it is **not** separately tested here — list as untested, use small.

### 5.3 Session / time-window table (from our 24,399 hourly candles, 2024-01 → 2026-10)

| Window (UTC) | Hours | Mean |hour| (bp) | Share of all |move| | Share of hours | Intensity (move share ÷ hour share) | Dominated by |
|---|---|---|---|---|---|---|
| **Asia 00:00–07:00** | 7,119 | 29.0 | 26.0% | 29.2% | 0.89× | CN/JP/KR flows, funding reset, ETF-of-Japan headlines |
| **EU 07:00–13:00** | 6,102 | 27.3 | 20.9% | 25.0% | 0.84× | European desks, macro leaks, basis rebalancing |
| **Pre-US 13:00–14:00** | 1,017 | **43.1** | 5.5% | 4.2% | **1.33×** | **US data 13:30 UTC** (CPI/PPI/NFP) — single hottest hour band |
| **US cash / ETF 14:00–21:00** | 7,113 | **40.3** | **36.1%** | 29.2% | **1.24×** | **Spot ETF creation/redemption + institutional metaorders** |
| US after 21:00–24:00 | 3,048 | 30.1 | 11.5% | 12.5% | 0.92× | CME Globex reopen (22:00), US late flows |

Hottest single hours: **14:00 UTC (53.9 bp mean |move|), 15:00 (49.1), 13:00 (43.1)** (`f_hours.csv`). Framing vs the Mazur-Polyzos "most change happens outside ETF hours" claim: *in aggregate* 64% of absolute movement does occur outside 14:00–21:00 — but that is simply because the off-window is 3.5× longer. **Per hour**, the US cash/ETF window is the most violent (1.24×) and the 13:00–14:00 data window the most violent of all (1.33×). Scalpers should concentrate risk there; swing traders should expect *regime-setting* moves there and thin false breaks elsewhere.

### 5.4 Confluence matrix (daily bias decisions)

| ETF 5d flow | Taker share | Other confirmations | State | Action |
|---|---|---|---|---|
| > 0 | ≥ 0.5 | lf_net max-short or funding z≤−2 | **Aligned long** | longs only, size normally (mean d1 +0.19% but hit 49% — expect chop into trend) |
| > 0 | < 0.5 | — | Mixed | half size longs; needs 2nd factor |
| < 0 | ≥ 0.5 | — | Mixed | half size shorts; retail takers fighting institutional supply |
| < 0 | ≤ 0.5 | + any of: lf_net top decile, ATS ≤0.3 | **Aligned bear** | shorts only (**−0.18%/day, −0.36%/3d**; the only cell with negative expectancy in our panel) |
| any | mid-range (45–55%) | nothing extreme | **No-trade** | baseline is a coin flip (50.8% hit) — stand aside or pure technicals |

---

## 6. Known traps & limitations

1. **T+1 ETF reporting** — the "today" flow number publishes tomorrow morning; the daily layer must be computed on *yesterday's* flow and will always be one step behind intraday price.
2. **Reverse causality** — Granger runs **both ways** (Lim: β=0.47); price rising *causes* ETF creations (arbitrage). Same-day correlation (0.375) is not skill, it's simultaneity (our H5).
3. **COT weekly / Tuesday snapshot** — 3–5 day lag; a "hedge funds added" headline describes last Tuesday. Also the **basis-trade distortion**: lf_net is structurally short because desks long spot/ETF + short CME; "net short" ≠ "bearish on BTC". Only *changes* and *extremes* carry information.
4. **Exchange housekeeping false positives** — cold-wallet reshuffles print as "whale accumulation" (documented 2026-01-02 trap; CryptoQuant). Never trade a raw whale-print headline.
5. **Market-maker shorts ≠ bearish** — Wintermute-style Hyperliquid shorts are inventory/basis hedges; reading them as directional views is the classic error.
6. **Liquidation cascades override flow** — in a z≤−2 crowded-short regime, a 5% squeeze can ignore all daily-layer bear confluences; the intraday layer must stand down.
7. **Regime dependence of our own results** — the ETF next-day coefficient grew from ~0.4 bp/$100m (2024) to ~10 bp (2026) (`h2_etf_regimes.csv`); sample includes a bear phase. Re-estimate quarterly before trusting any single coefficient.
8. **Whale-signal survivorship** — public ATS commentary is written *after* the move is legible; our two −18% failures are the honest base rate, not exceptions.
9. **Free on-chain data is chart-only** — Glassnode free tier has no ATS API; the +1/−1 ATS score line in §5.1 is **manual**, which limits scale.
10. **Binance futures/data endpoints only serve ~30 days** — fine for live positioning (our H6 snapshot: taker buy/sell ratio mean 0.98, OI ~99k BTC, top-trader long/short 1.93), useless for history. Use klines-derived taker share for history instead.

---

## 7. Appendix — free source access sheet (all verified 2026-10-13)

| Source | Endpoint / URL | Cost | Refresh | History | Gotchas |
|---|---|---|---|---|---|
| BTC candles + taker-buy vol | `api.binance.com/api/v3/klines` (field 9 = taker buy base vol) | $0 | 1m+ | full | field 9 → taker share at any TF |
| Binance funding history | `fapi.binance.com/fapi/v1/fundingRate` | $0 | 8h | 2019→ | paginated ascending; ~500 rows/call |
| Binance positioning (live) | `www.binance.com/futures/data/takerlongshortRatio` + `openInterestHist` + `globalLongShortAccountRatio` + `topLongShortPositionRatio` | $0 | 5m | **30d only** | must use `www.` host (not `futures.`) |
| CFTC COT (TFF, Bitcoin 133741) | `publicreporting.cftc.gov/resource/gpe5-46if.json?$where=cftc_contract_market_code='133741'` | $0 | weekly (Fri) | 2018→ | legacy `6dca-aqww`; use lf/am/dealer fields |
| US spot ETF flows (full) | `farside.co.uk/bitcoin-etf-flow-all-data/` | $0 | daily T+1 | 2024-01-11→ | **403 without browser User-Agent**; validate total vs Total row ($57,112m) |
| ETF holdings/treasuries | `bitbo.io/treasuries/`, CoinClass, SoSoValue, Newhedge | $0 | daily | — | Bitbo JSON API is Pro/paid |
| Whale ATS / cohorts | Glassnode free charts (manual read) | $0 | daily | — | no API; chart-reading workflow |
| On-chain market data | CryptoQuant free tier | $0 | daily | 30d | 10k credits/mo; on-chain metrics need paid |
| Whale transfers | Whale Alert web/X feed | $0 web | real-time | — | API $29.95+; watch housekeeping traps |
| Fear & Greed | `alternative.me/crypto/fear-and-greed-index/` | $0 | daily | full | contrarian overlay only |
| Mempool / explorers | `mempool.space`, blockchain.com | $0 | real-time | full | miner/gov wallet labels |
| Hyperliquid | leaderboard + `clearinghouseState` (Wintermute etc.) | $0 | real-time | ~months | labeled MM accounts = hedges, not views |
| **Would upgrade (paid, out of scope)** | Glassnode Pro API, CryptoQuant Pro, Arkham, SoSoValue Pro, Kaiko | $50–500+/mo | — | — | ATS-by-cohort API + entity-labeled flows are the two things worth paying for |

---

## 8. Disclaimer

This document is research, not financial advice. It describes measurable historical relationships in public data as of October 2026. Nothing here is an offer, a recommendation, or an execution venue. Positioning data is lagged, noisy, and regime-dependent; two of seven dated "smart money" events in the last 18 months preceded 18% drawdowns. Size accordingly, re-estimate the coefficients quarterly (`scripts/06_analysis.py`), and treat every score as a bias overlay on your own risk framework.
