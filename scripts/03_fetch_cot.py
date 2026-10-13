"""Fetch CFTC Commitments of Traders — Traders in Financial Futures (TFF)
for CME Bitcoin futures (CFTC contract code 133741) — free public Socrata API.

Fields used:
  lev_money_positions_long/short  -> "leveraged funds" (hedge funds / basis traders)
  asset_mgr_positions_long/short  -> asset managers (pensions, wealth, institutions)
  dealer_positions_long/short     -> dealers / liquidity providers
  other_rept_positions_long/short -> other reportables (large speculators)
  open_interest_all

Weekly snapshot (as-of Tuesday, published Friday) since 2018-04-10.
Output: data/cot_bitcoin_weekly.csv
"""
import os
import time
import urllib.parse
import urllib.request

import pandas as pd

API = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
WHERE = "cftc_contract_market_code='133741'"
DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def fetch_all():
    rows, offset = [], 0
    while True:
        params = {
            "$where": WHERE,
            "$order": "report_date_as_yyyy_mm_dd ASC",
            "$limit": "5000",
            "$offset": str(offset),
        }
        url = API + "?" + urllib.parse.urlencode(params)
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    batch = pd.DataFrame(__import__("json").load(r))
                break
            except Exception as e:  # noqa: BLE001
                if attempt == 3:
                    raise
                print(f"  retry {attempt}: {e}")
                time.sleep(2 * (attempt + 1))
        if batch.empty:
            break
        rows.append(batch)
        offset += len(batch)
        print(f"  fetched {offset} rows")
        if len(batch) < 5000:
            break
        time.sleep(0.4)
    return pd.concat(rows, ignore_index=True)


def main():
    os.makedirs(DATA, exist_ok=True)
    df = fetch_all()
    num_cols = [
        "open_interest_all",
        "lev_money_positions_long", "lev_money_positions_short", "lev_money_positions_spread",
        "asset_mgr_positions_long", "asset_mgr_positions_short",
        "dealer_positions_long_all", "dealer_positions_short_all",
        "other_rept_positions_long", "other_rept_positions_short",
        "nonrept_positions_long_all", "nonrept_positions_short_all",
        "change_in_lev_money_long", "change_in_lev_money_short",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df["date"] = pd.to_datetime(df["report_date_as_yyyy_mm_dd"]).dt.tz_localize(None)
    df["lf_net"] = df["lev_money_positions_long"] - df["lev_money_positions_short"]
    df["am_net"] = df["asset_mgr_positions_long"] - df["asset_mgr_positions_short"]
    df["dealer_net"] = df["dealer_positions_long_all"] - df["dealer_positions_short_all"]
    out = os.path.join(DATA, "cot_bitcoin_weekly.csv")
    df.to_csv(out, index=False)
    print(f"{out}: {len(df)} weeks  {df['date'].min().date()} -> {df['date'].max().date()}")
    print(df[["date", "open_interest_all", "lf_net", "am_net"]].tail(4).to_string(index=False))


if __name__ == "__main__":
    main()
