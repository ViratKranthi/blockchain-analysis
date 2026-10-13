# Findings — Smart Money / BTC (as of 2026-10-13)

Full report: `docs/BTC_SMART_MONEY_INFLUENCE.md`. Raw tables: `analysis/RESULTS.md` + `analysis/results/*.csv`.

## Headline answers to the four questions

1. **Who moves BTC** — (i) US spot ETF institutional flow via APs, (ii) aggressive perp takers, (iii) CME basis/hedge funds, (iv) on-chain 10k+ whales (volatility, not direction), (v) market makers (transmission via √size impact, not directional view).
2. **How much influence** — ETF flow: **+32.5 bp/$100M same-day** (our panel, t=9.7, 14% of variance; Lim IV: 53 bp, 21%). Takers: **+31 bp per +1 pp** same-day (t=3.3). Whales: +55–104% volatility multiplier (Shen). Hedge funds: contrarian only (+2.5%/4wk at max-net-short decile, p=0.003).
3. **Does price follow them (lag?)** — **No at daily horizon**: lead-lag correlation of ETF flow vs returns peaks at lag −1/0 (0.33–0.38) and ≈0 at +1…+3. Positioning **co-moves** with price; impact is same-day, publication T+1. Two dated whale "accumulation" events preceded −17.6% and −18.3% two-week drawdowns.
4. **Usable free confluence** — bear cell (ETF 5d < 0 **and** taker ≤ 0.5): **−0.18%/day, −0.36%/3d** (p≈0.09); extreme taker deciles → 2–3 day continuation (p=0.023/0.011); crowded-short funding z≤−2 → +3.2%/week (n=30); US 13:00–15:00 UTC = hottest hour band (43–54 bp |move| vs 27–29 Asia/EU).

## Ranked influence (free-data view)

| Rank | Cohort | Impact/unit | Horizon | Latency |
|---|---|---|---|---|
| 1 | ETF flow | 32–53 bp / $100M same-day | daily | 0 / T+1 pub |
| 2 | Perp takers | 31 bp / +1pp; deciles 2–3d | intraday + 2–3d | ~0 |
| 3 | CME hedge funds | contrarian +2.5%/4wk | 2–4 wks | 3–5 d |
| 4 | Funding extremes | +3.2%/wk at z≤−2 | 1–2 wks | 0 |
| 5 | On-chain whales | vol ×1.55–2.04 | weeks | 1 d (charts) |

## Key traps confirmed by our own tests

- Big inflow day → long tomorrow: **n.s.** (t=1.28). Same-day only.
- COT level as trend signal: **n.s.** at 1–2 weeks.
- Funding linear prediction: **R²≈0**. Crowded-long does NOT precede crashes (+1.15% next week).
- Whale ATS headlines: **2 of 7 catastrophic** at 2 weeks; one "accumulation" print was exchange housekeeping.
- Market-maker shorts = inventory hedges, not views.
