#!/usr/bin/env python3
"""Bundle all research data into app/data.js for the static dashboard.

Run from repo root:  .venv/bin/python app/build_data.py
Then open:           app/index.html   (no server needed)
"""
from __future__ import annotations

import json
import os

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "app", "data.js")
RESULTS = os.path.join(ROOT, "analysis", "results")


def records(df: pd.DataFrame) -> list[dict]:
    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_float_dtype(df[col]):
            df[col] = df[col].round(6)
    return json.loads(df.to_json(orient="records"))


def main() -> None:
    panel = pd.read_csv(os.path.join(ROOT, "analysis", "panel_daily.csv"), parse_dates=["date"])
    etf = pd.read_csv(os.path.join(ROOT, "data", "etf_flows_daily.csv"), parse_dates=["date"])
    cot = pd.read_csv(os.path.join(ROOT, "data", "cot_bitcoin_weekly.csv"), parse_dates=["date"])
    hourly = pd.read_csv(os.path.join(ROOT, "data", "btcusdt_hourly.csv"))
    hourly["date"] = pd.to_datetime(hourly["open_time"], unit="ms")
    hourly = hourly.sort_values("date")
    hourly["ret"] = hourly["close"].pct_change()

    # ---- unified daily panel (compact arrays, ETF-era rows first-class) ----
    p = panel.sort_values("date").copy()
    daily = {
        "date": p["date"].dt.strftime("%Y-%m-%d").tolist(),
        "close": [None if pd.isna(v) else round(float(v), 1) for v in p["close"]],
        "ret_d1": [None if pd.isna(v) else round(float(v) * 100, 4) for v in p["ret_d1"]],
        "etf_flow": [None if pd.isna(v) else round(float(v), 1) for v in p["etf_flow"]],
        "etf_flow_5d": [None if pd.isna(v) else round(float(v), 1) for v in p["etf_flow_5d"]],
        "taker": [None if pd.isna(v) else round(float(v), 4) for v in p["taker_buy_share"]],
        "funding_z": [None if pd.isna(v) else round(float(v), 3) for v in p["funding_z"]],
        "lf_net": [None if pd.isna(v) else round(float(v), 0) for v in p["lf_net"]],
    }

    # latest snapshot for bias-console defaults
    last = p.dropna(subset=["taker_buy_share"]).iloc[-1]
    latest = {
        "date": last["date"].strftime("%Y-%m-%d"),
        "close": round(float(last["close"]), 1),
        "taker": round(float(last["taker_buy_share"]), 4),
        "funding_z": None if pd.isna(last["funding_z"]) else round(float(last["funding_z"]), 3),
        "etf_flow": None if pd.isna(last["etf_flow"]) else round(float(last["etf_flow"]), 1),
        "etf_flow_5d": None if pd.isna(last["etf_flow_5d"]) else round(float(last["etf_flow_5d"]), 1),
        "lf_net": None if pd.isna(last["lf_net"]) else round(float(last["lf_net"]), 0),
    }

    # ---- ETF: per-fund daily + cumulative total ----
    e = etf.sort_values("date").copy()
    e["cum_total"] = e["Total"].cumsum().round(1)
    etf_ts = {
        "date": e["date"].dt.strftime("%Y-%m-%d").tolist(),
        "total": [None if pd.isna(v) else round(float(v), 1) for v in e["Total"]],
        "cum": e["cum_total"].tolist(),
        "ibit": [None if pd.isna(v) else round(float(v), 1) for v in e["IBIT"]],
    }
    # latest non-zero flow day (skip all-zero rows e.g. holidays/pre-open)
    nz = e[e["Total"].fillna(0) != 0]
    last_etf = (nz.iloc[-1] if len(nz) else e.iloc[-1])
    etf_latest_date = last_etf["date"].strftime("%Y-%m-%d")
    etf_latest_funds = [
        {"fund": col, "flow": round(float(last_etf[col]), 1)}
        for col in e.columns if col not in ("date", "cum_total")
        if not pd.isna(last_etf[col])
    ]

    # ---- COT ----
    c = cot.sort_values("date")
    cot_ts = {
        "date": c["date"].dt.strftime("%Y-%m-%d").tolist(),
        "lf_net": [None if pd.isna(v) else round(float(v), 0) for v in c["lf_net"]],
        "am_net": [None if pd.isna(v) else round(float(v), 0) for v in c["am_net"]],
        "oi": [None if pd.isna(v) else round(float(v), 0) for v in c["open_interest_all"]],
    }

    # ---- hourly: mean |move| by UTC hour + session stats ----
    h = hourly.dropna(subset=["ret"]).copy()
    h["abs_bp"] = (h["ret"].abs() * 1e4)
    by_hour = (h.groupby(h["date"].dt.hour)["abs_bp"].mean().round(1))
    hour_abs = [float(by_hour.get(hr, 0)) for hr in range(24)]

    # ---- results tables ----
    tables = {}
    for fn in sorted(os.listdir(RESULTS)):
        if fn.endswith(".csv"):
            key = fn[:-4]
            tables[key] = records(pd.read_csv(os.path.join(RESULTS, fn)))

    payload = {
        "meta": {
            "as_of": "2026-10-13",
            "panel_days": int(len(panel)),
            "etf_days": int(len(etf)),
            "cot_weeks": int(len(cot)),
            "hourly_rows": int(len(hourly)),
            "total_flow_musd": round(float(e["Total"].sum()), 1),
        },
        "latest": latest,
        "daily": daily,
        "etf": etf_ts,
        "etf_latest_date": etf_latest_date,
        "etf_latest_funds": etf_latest_funds,
        "cot": cot_ts,
        "hour_abs": hour_abs,
        "tables": tables,
    }

    js = "window.DASH = " + json.dumps(payload, separators=(",", ":"), allow_nan=False) + ";\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(js)
    print(f"wrote {OUT}  ({len(js) / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
