"""Empirical study: does institutional / whale positioning data predict BTC price?

Reads analysis/panel_daily.csv, writes:
  analysis/RESULTS.md          all tables (the evidence base for the report)
  analysis/results/*.csv       individual table outputs

Sections
  A  ETF flows        (Farside, daily, 2024-01-11 -> )
  B  CME COT          (leveraged funds / asset managers, weekly, 2018 -> )
  C  Taker buy share  (Binance aggressive-taker volume share, daily)
  D  Funding regime   (crowded positioning z-score)
  E  Confluence combos (daily-bias layer hit rates)
  F  Session study    (hourly: where does BTC actually move?)
  G  Event case studies (dated, verifiable)
"""
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm

ROOT = os.path.join(os.path.dirname(__file__), "..")
AN = os.path.join(ROOT, "analysis")
RES = os.path.join(AN, "results")
LINES = []


def log(s=""):
    LINES.append(str(s))
    print(s)


def save(df, name):
    path = os.path.join(RES, name)
    df.to_csv(path, index=False)
    return path


def ols_hac(y, x, const=True):
    """OLS with Newey-West (HAC) errors, lag = floor(4*(n/100)^(2/9))."""
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    if len(d) < 30:
        return None
    X = sm.add_constant(d["x"]) if const else d[["x"]]
    m = sm.OLS(d["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": int(len(d) ** 0.4)})
    ci = m.conf_int()
    return {
        "n": int(m.nobs),
        "coef": m.params["x"],
        "t": m.tvalues["x"],
        "p": m.pvalues["x"],
        "r2": m.rsquared,
        "ci_lo": ci.loc["x", 0],
        "ci_hi": ci.loc["x", 1],
    }


def welch(a, b):
    from scipy import stats
    a, b = a.dropna(), b.dropna()
    if len(a) < 10 or len(b) < 10:
        return np.nan, np.nan
    t, p = stats.ttest_ind(a, b, equal_var=False)
    return t, p


def quintile_table(df, sig_col, ret_col, q=5):
    d = df[[sig_col, ret_col]].dropna()
    if len(d) < 100:
        return None
    d = d.copy()
    d["q"] = pd.qcut(d[sig_col], q, labels=False, duplicates="drop")
    g = d.groupby("q")[ret_col].agg(["count", "mean", "median", "std"])
    g["hit%"] = d.groupby("q")[ret_col].apply(lambda s: (s > 0).mean() * 100)
    g[f"%{sig_col}"] = d.groupby("q")[sig_col].mean()
    return g.reset_index()


def decile_extremes(df, sig_col, ret_cols, pct=0.90):
    d = df.dropna(subset=[sig_col])
    hi = d[d[sig_col] >= d[sig_col].quantile(pct)]
    lo = d[d[sig_col] <= d[sig_col].quantile(1 - pct)]
    rows = []
    for name, grp in [("HIGH", hi), ("LOW", lo)]:
        r = {"group": name, "n": len(grp), f"mean_{sig_col}": grp[sig_col].mean()}
        for rc in ret_cols:
            s = grp[rc].dropna()
            r[f"mean_{rc}"] = s.mean()
            r[f"hit%_{rc}"] = (s > 0).mean() * 100
        rows.append(r)
    out = pd.DataFrame(rows)
    if len(ret_cols) > 0 and len(out) == 2:
        for rc in ret_cols:
            t, pv = welch(hi[rc], lo[rc])
            out.loc[0, f"t_H-L_{rc}"] = t
            out.loc[0, f"p_H-L_{rc}"] = pv
    return out


def section(title):
    log()
    log("=" * 78)
    log(title)
    log("=" * 78)


def main():
    os.makedirs(RES, exist_ok=True)
    p = pd.read_csv(os.path.join(AN, "panel_daily.csv"), parse_dates=["date"])
    p = p.sort_values("date").reset_index(drop=True)

    for h in (1, 2, 3, 7, 14, 28):
        p[f"ret_d{h}_bp"] = p[f"ret_d{h}"] * 1e4        # basis points
    etf = p[p["date"] >= "2024-01-11"].copy()          # US spot ETF era

    log("# Empirical results — institutional/whale positioning vs BTC price")
    log(f"\nPanel: {len(p)} days ({p['date'].min().date()} → {p['date'].max().date()}); "
        f"ETF era {len(etf)} days ({etf['date'].min().date()} → {etf['date'].max().date()})")

    # ---------------------------------------------------------------- A: ETF
    section("A. US SPOT ETF NET FLOWS -> BTC RETURNS  (Farside daily, US$m)")
    rows = []
    for sig in ["etf_flow", "etf_flow_5d", "etf_flow_10d"]:
        for ret in ["ret_prev_d1", "ret_d1", "ret_d2", "ret_d3"]:
            r = ols_hac(etf[ret] * 1e4, etf[sig])       # coefficient in bp per US$1m
            if r:
                rows.append({"signal": sig, "return": ret, **r})
    a_ols = pd.DataFrame(rows)
    a_ols["bp_per_100m"] = a_ols["coef"] * 100
    save(a_ols, "a_etf_ols.csv")
    log("\nA1. OLS: forward BTC return (bp) on ETF flow (US$m), Newey-West t-stats")
    log(a_ols[["signal", "return", "n", "bp_per_100m", "t", "p", "r2", "ci_lo", "ci_hi"]]
        .round(3).to_string(index=False))

    log("\nA2. Contemporaneous vs predictive correlation (reverse-causality check)")
    corr_rows = []
    for sig in ["etf_flow", "etf_flow_5d"]:
        for ret in ["ret_prev_d1", "ret_d1", "ret_d2"]:
            d = etf[[sig, ret]].dropna()
            corr_rows.append({
                "signal": sig, "return": ret, "n": len(d),
                "pearson": d[sig].corr(d[ret]),
                "spearman": d[sig].corr(d[ret], method="spearman"),
            })
    a_corr = pd.DataFrame(corr_rows)
    save(a_corr, "a_etf_corr.csv")
    log(a_corr.round(4).to_string(index=False))

    log("\nA3. Next-day return by ETF-flow bucket (US$m; ties at zero make quantiles unusable)")
    bins = [-np.inf, -250, -50, 50, 250, np.inf]
    labels = ["strong outflow <-250", "outflow -250..-50", "flat -50..50",
              "inflow 50..250", "strong inflow >250"]
    e3 = etf.dropna(subset=["etf_flow", "ret_d1"]).copy()
    e3["bucket"] = pd.cut(e3["etf_flow"], bins=bins, labels=labels)
    a3 = e3.groupby("bucket", observed=True)["ret_d1_bp"].agg(
        n="count", mean_bp="mean", median_bp="median", std_bp="std")
    a3["hit%"] = e3.groupby("bucket", observed=True)["ret_d1"].apply(lambda s: (s > 0).mean() * 100)
    a3["mean_d3%"] = e3.groupby("bucket", observed=True)["ret_d3"].mean() * 100
    a3["mean_d7%"] = e3.groupby("bucket", observed=True)["ret_d7"].mean() * 100
    a3 = a3.reset_index()
    save(a3, "a_etf_quintiles.csv")
    log(a3.round(2).to_string(index=False))

    log("\nA4. Extreme flow days (top/bottom decile) -> forward returns")
    a_ext = decile_extremes(etf, "etf_flow", ["ret_d1", "ret_d2", "ret_d3", "ret_d7"])
    save(a_ext, "a_etf_extremes.csv")
    log(a_ext.round(5).to_string(index=False))

    # ---------------------------------------------------------------- B: COT
    section("B. CME COT — LEVERAGED FUNDS (HEDGE FUNDS) NET POSITION -> BTC")
    cot = p.dropna(subset=["lf_net"]).copy()
    cot["lf_net_ret_next"] = cot["ret_d7"]
    cot["lf_chg_next_week"] = cot["lf_net"].shift(-1) - cot["lf_net"]
    rows = []
    for sig, ret in [("lf_net", "ret_d7"), ("lf_net", "ret_d14"),
                     ("lf_net_chg", "ret_d7"), ("am_net", "ret_d7")]:
        r = ols_hac(cot[ret], cot[sig])
        if r:
            rows.append({"signal": sig, "return": ret, **r})
    b_ols = pd.DataFrame(rows)
    b_ols["coef_bp_per_1000"] = np.where(
        b_ols["signal"].str.startswith(("lf_net", "am_net")),
        b_ols["coef"] * 1000 * 100,  # contracts -> bp of return
        b_ols["coef"] * 1000 * 100)
    save(b_ols, "b_cot_ols.csv")
    log("\nB1. OLS: BTC forward return (bp) on COT position per 1000 contracts (NW t)")
    log(b_ols[["signal", "return", "n", "coef_bp_per_1000", "t", "p", "r2"]].round(4).to_string(index=False))

    log("\nB2. Next 1/2/4-week returns when leveraged funds are in top/bottom net-position decile")
    b_ext = decile_extremes(cot, "lf_net", ["ret_d7", "ret_d14", "ret_d28"])
    save(b_ext, "b_cot_extremes.csv")
    log(b_ext.round(5).to_string(index=False))

    log("\nB3. Weekly change in leveraged-fund net position (top/bottom decile) -> next-week return")
    cot2 = cot.dropna(subset=["lf_net_chg"])
    b_ext2 = decile_extremes(cot2, "lf_net_chg", ["ret_d7", "ret_d14"])
    save(b_ext2, "b_cot_changes.csv")
    log(b_ext2.round(5).to_string(index=False))

    # --------------------------------------------------------------- C: taker
    section("C. AGGRESSIVE TAKER BUY SHARE (Binance perp, daily) -> BTC RETURNS")
    t = p.dropna(subset=["taker_buy_share"]).copy()
    t["taker_pp"] = (t["taker_buy_share"] - 0.5) * 100  # per +1 percentage point vs 50%
    rows = []
    for sig in ["taker_pp"]:
        for ret in ["ret_prev_d1", "ret_d1", "ret_d2"]:
            r = ols_hac(t[ret] * 1e4, t[sig])
            if r:
                rows.append({"signal": sig, "return": ret, **r})
    c_ols = pd.DataFrame(rows)
    c_ols["bp_per_100m"] = c_ols["coef"]          # bp per +1pp taker share
    save(c_ols, "c_taker_ols.csv")
    log("\nC1. OLS: return (bp) on taker-buy-share (level), NW t-stats")
    log(c_ols[["signal", "return", "n", "bp_per_100m", "t", "p", "r2"]]
        .rename(columns={"bp_per_100m": "bp_per_+1pp_share"}).round(3).to_string(index=False))

    log("\nC2. Next-day return by taker-buy-share quintile")
    c_q = quintile_table(t, "taker_buy_share", "ret_d1_bp")
    if c_q is not None:
        save(c_q, "c_taker_quintiles.csv")
        log(c_q.round(2).to_string(index=False))

    log("\nC3. Extreme taker days (deciles)")
    c_ext = decile_extremes(t, "taker_buy_share", ["ret_d1", "ret_d2", "ret_d3"])
    save(c_ext, "c_taker_extremes.csv")
    log(c_ext.round(5).to_string(index=False))

    # ------------------------------------------------------------- D: funding
    section("D. FUNDING-RATE Z-SCORE (crowded positioning) -> BTC RETURNS")
    f = p.dropna(subset=["funding_z"]).copy()
    rows = []
    for ret in ["ret_d1", "ret_d7", "ret_d14"]:
        r = ols_hac(f[ret] * 1e4, f["funding_z"])
        if r:
            rows.append({"signal": "funding_z", "return": ret, **r})
    d_ols = pd.DataFrame(rows)
    d_ols["bp_per_100m"] = d_ols["coef"]
    save(d_ols, "d_funding_ols.csv")
    log("\nD1. OLS: return (bp) on funding z-score")
    log(d_ols[["signal", "return", "n", "bp_per_100m", "t", "p", "r2"]]
        .rename(columns={"bp_per_100m": "bp_per_1z"}).round(3).to_string(index=False))
    log("\nD2. Extreme funding weeks (z >= 2 vs z <= -2) -> forward returns")
    rows = []
    for name, m in [("z>=2 (crowded long)", f["funding_z"] >= 2),
                    ("z<=-2 (crowded short)", f["funding_z"] <= -2),
                    ("-1<z<1 (neutral)", f["funding_z"].abs() < 1)]:
        g = f[m]
        rows.append({"regime": name, "n": len(g),
                     "mean_d1%": g["ret_d1"].mean() * 100, "hit_d1%": (g["ret_d1"] > 0).mean() * 100,
                     "mean_d7%": g["ret_d7"].mean() * 100, "hit_d7%": (g["ret_d7"] > 0).mean() * 100,
                     "mean_d14%": g["ret_d14"].mean() * 100})
    d_reg = pd.DataFrame(rows)
    save(d_reg, "d_funding_regimes.csv")
    log(d_reg.round(3).to_string(index=False))

    # ---------------------------------------------------------- E: confluence
    section("E. DAILY-BIAS CONFLUENCE (ETF 5d flow x taker-buy share) -> next-day BTC")
    e = etf.dropna(subset=["taker_buy_share", "ret_d1"]).copy()
    e["etf_pos"] = e["etf_flow_5d"] > 0
    e["tak_pos"] = e["taker_buy_share"] > e["taker_buy_share"].median()
    rows = []
    for etf_v in [True, False]:
        for tak_v in [True, False]:
            g = e[(e["etf_pos"] == etf_v) & (e["tak_pos"] == tak_v)]
            if len(g) < 5:
                continue
            rows.append({
                "etf5d": "POS" if etf_v else "NEG",
                "taker": "POS" if tak_v else "NEG",
                "n": len(g),
                "mean_d1%": g["ret_d1"].mean() * 100,
                "median_d1%": g["ret_d1"].median() * 100,
                "hit_d1%": (g["ret_d1"] > 0).mean() * 100,
                "mean_d3%": g["ret_d3"].mean() * 100,
                "hit_d3%": (g["ret_d3"] > 0).mean() * 100,
            })
    e_tab = pd.DataFrame(rows)
    save(e_tab, "e_confluence.csv")
    log(e_tab.round(3).to_string(index=False))
    base = e["ret_d1"]
    log(f"\nBaseline (all ETF-era days): n={len(base)}, mean_d1={base.mean()*100:.3f}%, "
        f"hit_d1={(base>0).mean()*100:.1f}%")

    # ------------------------------------------------------------- F: sessions
    section("F. HOURLY SESSION STUDY — WHERE DOES BTC ACTUALLY MOVE? (2024-01 -> )")
    h = pd.read_csv(os.path.join(ROOT, "data", "btcusdt_hourly.csv"))
    h["dt"] = pd.to_datetime(h["open_time"], unit="ms", utc=True).dt.tz_convert(None)
    h["hour"] = h["dt"].dt.hour
    h["date"] = h["dt"].dt.normalize()
    for c in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
        h[c] = pd.to_numeric(h[c], errors="coerce")
    h["ret"] = h["close"].pct_change()
    h["absret"] = h["ret"].abs()
    h["taker_share"] = np.where(h["volume"] > 0, h["taker_buy_base"] / h["volume"], np.nan)

    def bucket(hour):
        if hour < 7:
            return "1 ASIA 00-07 UTC"
        if hour < 13:
            return "2 EU 07-13 UTC"
        if hour < 14:
            return "3 PRE-US 13-14 UTC"
        if hour < 21:
            return "4 US CASH / ETF 14-21 UTC"
        return "5 US AFTER 21-24 UTC"

    h["session"] = h["hour"].map(bucket)
    g = h.groupby("session").agg(
        hours=("ret", "size"),
        mean_ret_bp=("ret", lambda s: s.mean() * 1e4),
        mean_abs_bp=("absret", lambda s: s.mean() * 1e4),
        net_abs_share=("absret", lambda s: s.sum()),
        mean_taker=("taker_share", "mean"),
        up_share=("ret", lambda s: (s > 0).mean() * 100),
    )
    g["share_of_total_abs_move%"] = g["net_abs_share"] / g["net_abs_share"].sum() * 100
    g = g.drop(columns=["net_abs_share"]).reset_index()
    save(g, "f_sessions.csv")
    log("\nF1. By session (hours = count of hourly candles; share of total |move|):")
    log(g.round(4).to_string(index=False))

    log("\nF2. Hourly |return| by UTC hour (top 8 most volatile hours):")
    hh = h.groupby("hour").agg(mean_abs_bp=("absret", lambda s: s.mean() * 1e4),
                               taker=("taker_share", "mean"),
                               n=("ret", "size")).round(3)
    save(hh.reset_index(), "f_hours.csv")
    log(hh.sort_values("mean_abs_bp", ascending=False).head(8).to_string())

    # ------------------------------------------------------- G: case studies
    section("G. DATED CASE STUDIES (event -> what BTC did next)")
    events = [
        ("2025-04-08", "US tariff-tantrum bottom; whales 10k+ had been buying since ~$75k (Glassnode ATS)"),
        ("2025-11-07", "Whale ATS flip: 10k+ cohort back to accumulation after 3 months selling (Glassnode)"),
        ("2025-11-27", "Glassnode: whales ATS 0.8 strong accumulation, BTC reclaims $90k"),
        ("2026-01-30", "Mega-whales sole accumulators at ~$78k while retail sells (Glassnode)"),
        ("2026-08-10", "CME leveraged funds flip net long for first time in years (CryptoQuant/COT)"),
        ("2026-04-22", "All ETF rolling flow periods turn positive; IBIT +$246.9m day"),
        ("2026-10-07", "ETF outflow $484.9m (largest recent) -> BTC selloff next sessions"),
    ]
    rows = []
    for ds, desc in events:
        d = pd.Timestamp(ds)
        w = p[(p["date"] >= d - pd.Timedelta(days=2)) & (p["date"] <= d + pd.Timedelta(days=15))]
        if w.empty:
            continue
        base_row = p[p["date"] >= d]
        if base_row.empty:
            continue
        p0 = base_row["close"].iloc[0]
        r = {"date": ds, "event": desc, "close_at": p0}
        for hz in (1, 3, 7, 14):
            nxt = p[p["date"] >= d + pd.Timedelta(days=hz)]
            r[f"ret_d{hz}%"] = (nxt["close"].iloc[0] / p0 - 1) * 100 if len(nxt) else np.nan
        # local context
        rows.append(r)
    g_tab = pd.DataFrame(rows)
    save(g_tab, "g_events.csv")
    log(g_tab.round(2).to_string(index=False))


    # ------------------------------------------------------ H: robustness
    section("H. ROBUSTNESS & SIGNIFICANCE CHECKS")
    from scipy import stats as sps

    def binom_p(hit_pct, n, null=50.0):
        if n == 0:
            return np.nan
        k = round(hit_pct / 100 * n)
        return sps.binomtest(k, n, null / 100, alternative="greater" if null < 50 else "two-sided").pvalue

    log("\nH1. ETF outflow asymmetry: pooled outflow days (< -50m) vs all other days")
    e = etf.dropna(subset=["ret_d1"]).copy()
    out = e["etf_flow"] < -50
    r = {}
    for name, g in [("outflow<-50", e[out]), ("other", e[~out])]:
        r[name] = {"n": len(g), "mean_d1_bp": g["ret_d1"].mean() * 1e4,
                   "hit_d1%": (g["ret_d1"] > 0).mean() * 100,
                   "mean_d3%": g["ret_d3"].mean() * 100,
                   "mean_d7%": g["ret_d7"].mean() * 100}
    t, pv = welch(e[out]["ret_d1"], e[~out]["ret_d1"])
    h1 = pd.DataFrame(r).T
    h1["t_out_vs_rest_d1"] = t
    h1["p_out_vs_rest_d1"] = pv
    save(h1, "h1_etf_outflow_asymmetry.csv")
    log(h1.round(4).to_string())
    log(f"   binomial p(hit<50% | outflow) = {binom_p((e[out]['ret_d1']>0).mean()*100, out.sum()):.4f} "
        f"(one-sided: worse than coin-flip)")

    log("\nH2. Regime split of the ETF->next-day relation (bull vs bear sub-samples)")
    rows = []
    for name, lo, hi in [("2024-01..2024-12", "2024-01-11", "2024-12-31"),
                         ("2025-01..2025-12", "2025-01-01", "2025-12-31"),
                         ("2026-01..now", "2026-01-01", "2099-12-31")]:
        m = e[(e["date"] >= lo) & (e["date"] <= hi)]
        if len(m) < 50:
            continue
        rows.append({
            "period": name, "n": len(m),
            "same_day_corr": m["ret_prev_d1"].corr(m["etf_flow"]),
            "next_day_bp_per_100m": (m["ret_d1"] * 1e4).cov(m["etf_flow"]) / m["etf_flow"].var() * 100,
            "next_day_hit%": (m["ret_d1"] > 0).mean() * 100,
            "mean_next_d1%": m["ret_d1"].mean() * 100,
            "outflow_days": int((m["etf_flow"] < -50).sum()),
        })
    h2 = pd.DataFrame(rows)
    save(h2, "h2_etf_regimes.csv")
    log(h2.round(3).to_string(index=False))

    log("\nH3. Extreme taker-share day (top decile) x ETF-5d-flow sign -> forward returns")
    tt = etf.dropna(subset=["taker_buy_share", "ret_d1"]).copy()
    hi = tt["taker_buy_share"] >= tt["taker_buy_share"].quantile(0.9)
    lo = tt["taker_buy_share"] <= tt["taker_buy_share"].quantile(0.1)
    rows = []
    for tname, mask in [("taker TOP decile", hi), ("taker BOTTOM decile", lo)]:
        for ename, emask in [("etf5d>0", tt["etf_flow_5d"] > 0), ("etf5d<0", tt["etf_flow_5d"] <= 0)]:
            g = tt[mask & emask]
            if len(g) < 8:
                continue
            rows.append({"taker": tname, "etf": ename, "n": len(g),
                         "mean_d1%": g["ret_d1"].mean() * 100,
                         "hit_d1%": (g["ret_d1"] > 0).mean() * 100,
                         "mean_d3%": g["ret_d3"].mean() * 100,
                         "hit_d3%": (g["ret_d3"] > 0).mean() * 100})
    h3 = pd.DataFrame(rows)
    save(h3, "h3_taker_x_etf.csv")
    log(h3.round(3).to_string(index=False))

    log("\nH4. Is the E confluence (ETF5d<0 & taker<0.5) significantly worse than the rest?")
    e4 = etf.dropna(subset=["taker_buy_share", "ret_d1"]).copy()
    both_neg = (e4["etf_flow_5d"] <= 0) & (e4["taker_buy_share"] <= 0.5)
    t, pv = welch(e4[both_neg]["ret_d1"], e4[~both_neg]["ret_d1"])
    t3, p3 = welch(e4[both_neg]["ret_d3"], e4[~both_neg]["ret_d3"])
    h4 = pd.DataFrame([{
        "group": "etf5d<0 & taker<=0.5", "n": int(both_neg.sum()),
        "mean_d1%": e4[both_neg]["ret_d1"].mean() * 100, "hit_d1%": (e4[both_neg]["ret_d1"] > 0).mean() * 100,
        "mean_d3%": e4[both_neg]["ret_d3"].mean() * 100,
        "rest_mean_d1%": e4[~both_neg]["ret_d1"].mean() * 100,
        "t_d1": t, "p_d1": pv, "t_d3": t3, "p_d3": p3,
    }])
    save(h4, "h4_confluence_sig.csv")
    log(h4.round(4).to_string(index=False))

    log("\nH5. Lead-lag cross-correlation: ETF flow vs BTC return at +/- 3 days")
    rows = []
    for lag in range(-3, 4):
        a = etf["etf_flow"].shift(lag)
        rows.append({"lag_days(flow relative to return)": lag,
                     "corr_with_ret_prev_d1": a.corr(etf["ret_prev_d1"]),
                     "corr_with_ret_d1": a.corr(etf["ret_d1"])})
    h5 = pd.DataFrame(rows)
    save(h5, "h5_lag_corr.csv")
    log(h5.round(4).to_string(index=False))

    log("\nH6. Live 30-day positioning snapshot (Binance public /futures/data — free, rolling 30d)")
    try:
        b = pd.read_csv(os.path.join(ROOT, "data", "binance_30d_metrics.csv"))
        desc = b.describe().T[["count", "mean", "min", "max"]]
        save(desc.reset_index(names="metric"), "h6_binance_30d.csv")
        log(desc.round(4).to_string())
    except Exception as ex:  # noqa: BLE001
        log(f"  skipped: {ex}")

    # write everything to RESULTS.md
    with open(os.path.join(AN, "RESULTS.md"), "w") as f:
        f.write("\n".join(LINES) + "\n")
    print("\n-> analysis/RESULTS.md and analysis/results/*.csv written")


if __name__ == "__main__":
    main()
