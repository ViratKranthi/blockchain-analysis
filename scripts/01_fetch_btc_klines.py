"""Fetch BTCUSDT klines (daily / hourly) from Binance public REST — free, no key.

Daily  : full history since 2017-08 (BTC listing).
Hourly : since 2024-01-01 (US spot ETF era).
15m    : last 60 days (intraday session study).

Kline fields we keep: OHLCV + taker-buy base volume (field 9) which lets us
compute taker buy/sell split (aggressive takers) at any timeframe for free.

Usage: .venv/bin/python scripts/01_fetch_btc_klines.py
"""
import json
import os
import time
import urllib.request

BASE = "https://api.binance.com/api/v3/klines"
DATA = os.path.join(os.path.dirname(__file__), "..", "data")
MS = 86_400_000


def get(symbol, interval, start_ms=None, end_ms=None, limit=1000):
    q = f"symbol={symbol}&interval={interval}&limit={limit}"
    if start_ms:
        q += f"&startTime={start_ms}"
    if end_ms:
        q += f"&endTime={end_ms}"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(f"{BASE}?{q}", timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 4:
                raise
            print(f"  retry {attempt}: {e}")
            time.sleep(1.5 * (attempt + 1))


def fetch_range(interval, start_ms, end_ms, out_name, step_ms):
    rows, cursor = [], start_ms
    while cursor < end_ms:
        batch = get("BTCUSDT", interval, start_ms=cursor, end_ms=end_ms)
        if not batch:
            break
        rows.extend(batch)
        nxt = batch[-1][0] + step_ms
        if nxt <= cursor:
            break
        cursor = nxt
        time.sleep(0.25)
    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades", "taker_buy_base",
        "taker_buy_quote", "ignore",
    ]
    out = os.path.join(DATA, out_name)
    with open(out, "w") as f:
        f.write(",".join(cols) + "\n")
        for r in rows:
            f.write(",".join(str(x) for x in r) + "\n")
    print(f"{out_name}: {len(rows)} rows")


def main():
    os.makedirs(DATA, exist_ok=True)
    now = int(time.time() * 1000)
    # Daily: full history
    fetch_range("1d", 1_500_000_000_000, now, "btcusdt_daily.csv", MS)
    # Hourly: ETF era
    fetch_range("1h", 1_704_067_200_000, now, "btcusdt_hourly.csv", 3_600_000)
    # 15m: last 60 days
    fetch_range("15m", now - 60 * MS, now, "btcusdt_15m.csv", 900_000)


if __name__ == "__main__":
    main()
