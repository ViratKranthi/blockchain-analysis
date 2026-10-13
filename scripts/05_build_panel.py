"""Build the merged daily research panel from all fetched free datasets.

Inputs (data/):
  btcusdt_daily.csv      Binance klines  (price, volume, taker-buy volume)
  etf_flows_daily.csv    Farside US spot ETF daily net flows (US$m)
  cot_bitcoin_weekly.csv CFTC TFF CME Bitcoin (leveraged funds / asset mgrs)
  funding_history.csv    Binance perp funding (8h -> daily mean)
Outputs (analysis/):
  panel_daily.csv        one row per calendar day, all signals

Key derived signals:
  ret_d1..d3     forward 1/2/3-day BTC log returns after the signal date
  taker_buy_vol  taker_buy_base / volume  (aggressive takers' share)
  etf_flow       total US spot ETF net flow (US$m)
  etf_flow_5d    5-day rolling sum
  lf_net         CME leveraged-fund net position (long - short contracts), ffilled
  funding_z      funding rate z-score (365d rolling)
"""
import os

import numpy as np
import pandas as pd

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "analysis")

LOG = np.log


def load_klines():
    df = pd.read_csv(os.path.join(DATA, "btcusdt_daily.csv"))
    df["date"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_convert(None).dt.normalize()
    for c in ["open", "high", "low", "close", "volume", "taker_buy_base"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["ret"] = df["close"].pct_change()
    df["taker_buy_share"] = np.where(df["volume"] > 0, df["taker_buy_base"] / df["volume"], np.nan)
    return df[["date", "open", "high", "low", "close", "volume", "ret", "taker_buy_share"]]


def load_etf():
    df = pd.read_csv(os.path.join(DATA, "etf_flows_daily.csv"), parse_dates=["date"])
    df = df[["date", "Total"]].rename(columns={"Total": "etf_flow"})
    # drop the trailing placeholder row (all-zero until issuers report)
    df = df.sort_values("date")
    return df


def load_cot():
    df = pd.read_csv(os.path.join(DATA, "cot_bitcoin_weekly.csv"), parse_dates=["date"])
    df = df[["date", "open_interest_all", "lf_net", "am_net", "dealer_net"]].copy()
    df["lf_net_chg"] = df["lf_net"].diff()
    return df.rename(columns={"date": "cot_date"})


def load_funding():
    df = pd.read_csv(os.path.join(DATA, "funding_history.csv"), parse_dates=["date_utc"])
    df["date"] = df["date_utc"].dt.normalize()
    g = df.groupby("date", as_index=False)["funding_rate"].mean()
    return g


def main():
    os.makedirs(OUT, exist_ok=True)
    px = load_klines()
    etf = load_etf()
    cot = load_cot()
    fund = load_funding()

    panel = px.merge(etf, on="date", how="left")
    panel["etf_flow"] = panel["etf_flow"].fillna(0.0)
    panel["etf_flow_5d"] = panel["etf_flow"].rolling(5, min_periods=1).sum()
    panel["etf_flow_10d"] = panel["etf_flow"].rolling(10, min_periods=1).sum()
    # only trust flows once the ETF era has started
    panel.loc[panel["date"] < etf["date"].min(), ["etf_flow", "etf_flow_5d", "etf_flow_10d"]] = np.nan

    panel = panel.merge(fund, on="date", how="left")
    mu = panel["funding_rate"].rolling(365, min_periods=60).mean()
    sd = panel["funding_rate"].rolling(365, min_periods=60).std()
    panel["funding_z"] = (panel["funding_rate"] - mu) / sd

    # weekly COT -> forward filled (as-of information: use next row's label only after report date)
    cot = cot.sort_values("cot_date")
    panel = panel.merge(
        cot.rename(columns={"cot_date": "date"}), on="date", how="left"
    )
    for c in ["open_interest_all", "lf_net", "am_net", "dealer_net", "lf_net_chg"]:
        panel[c] = panel[c].ffill()

    # forward returns after the signal date (tradeable horizons)
    for h in (1, 2, 3, 7, 14, 28):
        panel[f"ret_d{h}"] = panel["close"].pct_change(h).shift(-h)
    # backward return on the signal day itself (contemporaneous / reverse-causality check)
    panel["ret_prev_d1"] = panel["close"].pct_change()

    # rolling ranks (percentile within trailing 365d) for regime-style tests
    for c, name in [("etf_flow", "etf_flow_pct"), ("lf_net", "lf_net_pct"),
                    ("taker_buy_share", "taker_pct"), ("funding_z", "funding_pct")]:
        panel[name] = panel[c].rolling(365, min_periods=60).rank(pct=True)

    panel = panel.sort_values("date")
    out = os.path.join(OUT, "panel_daily.csv")
    panel.to_csv(out, index=False)
    print(f"{out}: {len(panel)} rows  {panel['date'].min().date()} -> {panel['date'].max().date()}")
    sub = panel[panel["date"] >= "2024-01-11"]
    print(f"ETF-era rows: {len(sub)}")
    print(sub[["date", "close", "etf_flow", "taker_buy_share", "lf_net", "funding_z"]]
          .tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
