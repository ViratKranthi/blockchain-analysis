"""Fetch US spot BTC ETF daily net flows from Farside Investors — free, no key.

Source : https://farside.co.uk/bitcoin-etf-flow-all-data/  (all daily rows)
Output : data/etf_flows_daily.csv  (date, per-fund US$m, Total)

Note: Farside publishes T+1 (today's row is usually still a placeholder "-").
"""
import io
import os
import time

import pandas as pd
import requests

URL = "https://farside.co.uk/bitcoin-etf-flow-all-data/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
}
DATA = os.path.join(os.path.dirname(__file__), "..", "data")


def main():
    os.makedirs(DATA, exist_ok=True)
    for _ in range(4):
        r = requests.get(URL, headers=HEADERS, timeout=60)
        if r.status_code == 200:
            break
        time.sleep(2)
    r.raise_for_status()
    table = pd.read_html(io.StringIO(r.text))[0]
    table = table[table["Date"] != "Total"].copy()
    table["Date"] = pd.to_datetime(table["Date"], format="%d %b %Y", errors="coerce")
    table = table.dropna(subset=["Date"])
    for c in table.columns:
        if c == "Date":
            continue
        table[c] = (
            table[c]
            .astype(str)
            .str.strip()
            .str.replace("(", "-", regex=False)
            .str.replace(")", "", regex=False)
            .str.replace(",", "", regex=False)
        )
        table[c] = table[c].replace({"": 0.0, "-": 0.0, "nan": 0.0, "--": 0.0})
        table[c] = pd.to_numeric(table[c], errors="coerce").fillna(0.0)
    table = table.rename(columns={"Date": "date"}).sort_values("date")
    out = os.path.join(DATA, "etf_flows_daily.csv")
    table.to_csv(out, index=False)
    print(f"{out}: {len(table)} rows  {table['date'].min().date()} -> {table['date'].max().date()}")
    print(f"cumulative total (US$m): {table['Total'].sum():,.0f}")


if __name__ == "__main__":
    main()
