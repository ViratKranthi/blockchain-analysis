"""Fetch Binance USDT-perp positioning data — free public endpoints, no key.

1) Funding rate history  : fapi.binance.com /fapi/v1/fundingRate   (full, since 2019)
2) 30-day rolling series : www.binance.com/futures/data/*
     - takerlongshortRatio       (aggressive taker buy vs sell volume)
     - openInterestHist          (OI snapshot)
     - globalLongShortAccountRatio (all accounts long/short)
     - topLongShortPositionRatio (top trader positioning)

NOTE: the /futures/data/* series only expose ~30 days of history (exchange limit).
      Funding history is deep (paginated 1000 records per call).

Output: data/funding_history.csv , data/binance_30d_metrics.csv
"""
import json
import os
import time
import urllib.request

FAPI = "https://fapi.binance.com/fapi/v1/fundingRate"
WWW = "https://www.binance.com/futures/data"
DATA = os.path.join(os.path.dirname(__file__), "..", "data")
MS_DAY = 86_400_000


def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise
            time.sleep(1.5 * (attempt + 1))


def fetch_funding():
    rows, end, stall = [], None, 0
    while True:
        url = f"{FAPI}?symbol=BTCUSDT&limit=1000"
        if end:
            url += f"&endTime={end}"
        batch = http_json(url)
        if not batch:
            break
        rows = batch + rows
        new_end = batch[0]["fundingTime"] - 1
        if new_end == end:  # no progress -> avoid infinite loop
            stall += 1
            if stall > 2:
                break
        else:
            stall = 0
        end = new_end
        print(f"  funding: {len(rows)} rows, back to "
              f"{time.strftime('%Y-%m-%d', time.gmtime(batch[0]['fundingTime'] / 1000))}")
        time.sleep(0.3)
    with open(os.path.join(DATA, "funding_history.csv"), "w") as f:
        f.write("funding_time_ms,date_utc,funding_rate,mark_price\n")
        for r in rows:
            f.write(f"{r['fundingTime']},{time.strftime('%Y-%m-%d %H:%M', time.gmtime(r['fundingTime']/1000))},"
                    f"{r['fundingRate']},{r['markPrice']}\n")
    print(f"funding_history.csv: {len(rows)} rows")


def fetch_metric(endpoint, symbol="BTCUSDT", period="1d", limit=30):
    url = f"{WWW}/{endpoint}?symbol={symbol}&period={period}&limit={limit}"
    return http_json(url)


def main():
    os.makedirs(DATA, exist_ok=True)
    fetch_funding()

    specs = {
        "takerlongshortRatio": ["buySellRatio", "buyVol", "sellVol"],
        "openInterestHist": ["sumOpenInterest", "sumOpenInterestValue"],
        "globalLongShortAccountRatio": ["longAccount", "shortAccount", "longShortRatio"],
        "topLongShortPositionRatio": ["longAccount", "shortAccount", "longShortRatio"],
    }
    frames = []
    for ep, cols in specs.items():
        try:
            data = fetch_metric(ep)
        except Exception as e:  # noqa: BLE001
            print(f"  {ep}: FAILED {e}")
            continue
        df = pd_from(data, ep, cols)
        frames.append(df)
        print(f"  {ep}: {len(df)} rows {df['date'].min()} -> {df['date'].max()}")
        time.sleep(0.5)

    if frames:
        merged = frames[0]
        for df in frames[1:]:
            merged = merged.merge(df, on="date", how="outer")
        merged = merged.sort_values("date")
        out = os.path.join(DATA, "binance_30d_metrics.csv")
        merged.to_csv(out, index=False)
        print(f"{out}: {len(merged)} rows")


def pd_from(data, ep, cols):
    import pandas as pd
    rows = [
        {"date": pd.to_datetime(r["timestamp"], unit="ms", utc=True).tz_convert(None).normalize(),
         **{f"{ep}_{c}": pd.to_numeric(r.get(c), errors="coerce") for c in cols}}
        for r in data
    ]
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main()
