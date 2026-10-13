#!/usr/bin/env python3
"""Live daily data pull with on-disk cache — free endpoints only.

Sources (all $0):
  Binance spot klines, Binance futures funding/OI/taker ratios, Farside ETF flows, CFTC COT.

Cache TTLs:
  intraday stuff (klines, funding, OI, ratios)  ~5 min
  ETF flows (T+1 publish)                       ~6 h
  COT (weekly)                                  ~24 h

Used by app/server.py. Can also be run standalone:
  .venv/bin/python -m app.live_fetch          # or: .venv/bin/python app/live_fetch.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.config import settings  # noqa: E402

CACHE = str(settings.db_path.parent)  # app/cache
os.makedirs(CACHE, exist_ok=True)

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}
TTL_INTRADAY = settings.ttl_intraday   # 5 min
TTL_ETF = settings.ttl_etf             # 6 h
TTL_COT = settings.ttl_cot             # 24 h


# ---------------------------------------------------------------- cache helpers
def _cache_path(name: str) -> str:
    return os.path.join(CACHE, name + ".json")


def cache_get(name: str, max_age: int):
    p = _cache_path(name)
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            blob = json.load(f)
        if time.time() - blob.get("_ts", 0) > max_age:
            return None
        return blob["data"]
    except Exception:
        return None


def cache_set(name: str, data) -> None:
    p = _cache_path(name)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump({"_ts": time.time(), "_at": datetime.now(UTC).isoformat(), "data": data}, f)
    os.replace(tmp, p)


def cache_meta(name: str):
    p = _cache_path(name)
    try:
        with open(p) as f:
            blob = json.load(f)
        return blob.get("_at")
    except Exception:
        return None


# ---------------------------------------------------------------- HTTP
def _get(url: str, params=None, timeout=15, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, headers=h, timeout=timeout)
    r.raise_for_status()
    return r


def _ak(asset: str, name: str) -> str:
    """Asset-prefixed cache key: 'BTC:daily', 'ETH:funding', etc."""
    return f"{asset}:{name}" if asset and asset != "BTC" else name


# ---------------------------------------------------------------- fetchers
def fetch_daily_klines(limit=420, asset="BTC"):
    """Binance spot daily klines → compact rows."""
    from app.assets import get_asset
    sym = get_asset(asset).binance_spot
    rows = []
    end = None
    while len(rows) < limit:
        params = {"symbol": sym, "interval": "1d", "limit": min(1000, limit - len(rows))}
        if end:
            params["endTime"] = end
        data = _get("https://api.binance.com/api/v3/klines", params).json()
        if not data:
            break
        for k in data:
            rows.append({
                "t": k[0],
                "date": datetime.fromtimestamp(k[0] / 1000, tz=UTC).strftime("%Y-%m-%d"),
                "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
                "close": float(k[4]), "volume": float(k[5]),
                "taker_buy": float(k[9]),
            })
        end = data[0][0] - 1
        if len(data) < params["limit"]:
            break
    rows.sort(key=lambda r: r["t"])
    return rows


def fetch_hourly_klines(limit=72, asset="BTC"):
    from app.assets import get_asset
    sym = get_asset(asset).binance_spot
    data = _get("https://api.binance.com/api/v3/klines",
                {"symbol": sym, "interval": "1h", "limit": limit}).json()
    return [{
        "t": k[0],
        "date": datetime.fromtimestamp(k[0] / 1000, tz=UTC).strftime("%Y-%m-%d %H:%M"),
        "open": float(k[1]), "high": float(k[2]), "low": float(k[3]),
        "close": float(k[4]), "volume": float(k[5]), "taker_buy": float(k[9]),
    } for k in data]


def fetch_funding_history(limit=500, asset="BTC"):
    from app.assets import get_asset
    sym = get_asset(asset).binance_perp
    data = _get("https://fapi.binance.com/fapi/v1/fundingRate",
                {"symbol": sym, "limit": limit}).json()
    return [{"t": r["fundingTime"], "rate": float(r["fundingRate"])} for r in data]


def fetch_premium(asset="BTC"):
    from app.assets import get_asset
    sym = get_asset(asset).binance_perp
    d = _get("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": sym}).json()
    return {
        "mark": float(d["markPrice"]),
        "last": float(d.get("lastPrice") or d["markPrice"]),
        "funding_rate": float(d["lastFundingRate"]),
        "next_funding": int(d["nextFundingTime"]),
    }


def fetch_open_interest(asset="BTC"):
    from app.assets import get_asset
    sym = get_asset(asset).binance_perp
    d = _get("https://fapi.binance.com/fapi/v1/openInterest", {"symbol": sym}).json()
    return {"oi_btc": float(d["openInterest"])}


def _futures_data(endpoint, limit=30, asset="BTC"):
    from app.assets import get_asset
    sym = get_asset(asset).binance_perp
    data = _get(
        f"https://www.binance.com/futures/data/{endpoint}",
        {"symbol": sym, "period": "1d", "limit": limit},
    ).json()
    return data  # list of dicts with string numbers


def fetch_oi_hist(asset="BTC"):
    out = []
    for r in _futures_data("openInterestHist", asset=asset):
        out.append({"t": int(r["timestamp"]), "oi": float(r["sumOpenInterest"]),
                    "oi_value": float(r["sumOpenInterestValue"])})
    return out


def fetch_taker_ratio(asset="BTC"):
    out = []
    for r in _futures_data("takerlongshortRatio", asset=asset):
        out.append({"t": int(r["timestamp"]),
                    "buy_sell": float(r["buySellRatio"]),
                    "buy_vol": float(r["buyVol"]), "sell_vol": float(r["sellVol"])})
    return out


def fetch_global_ls(asset="BTC"):
    out = []
    for r in _futures_data("globalLongShortAccountRatio", asset=asset):
        out.append({"t": int(r["timestamp"]),
                    "long_pct": float(r["longAccount"]), "short_pct": float(r["shortAccount"]),
                    "ratio": float(r["longShortRatio"])})
    return out


def fetch_top_ls(asset="BTC"):
    out = []
    for r in _futures_data("topLongShortPositionRatio", asset=asset):
        out.append({"t": int(r["timestamp"]),
                    "long_pct": float(r["longAccount"]), "short_pct": float(r["shortAccount"]),
                    "ratio": float(r["longShortRatio"])})
    return out


def fetch_etf_flows(asset="BTC"):
    """Farside full daily table. BTC only — ETH has separate Farside page."""
    from io import StringIO
    r = _get("https://farside.co.uk/bitcoin-etf-flow-all-data/")
    tables = pd.read_html(StringIO(r.text), flavor="lxml")
    df = None
    for t in tables:
        cols = [str(c).strip() for c in t.columns]
        flat = []
        for c in cols:
            if isinstance(c, tuple):
                flat.append(str(c[-1]).strip())
            else:
                flat.append(c)
        if "Total" in flat and "Date" in flat:
            df = t.copy()
            df.columns = flat
            break
    if df is None:
        raise RuntimeError("Farside table with Date/Total not found")

    def _num(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return np.nan
        s = str(x).strip().replace(",", "")
        if s in ("", "-", "nan", "NaN"):
            return 0.0 if s == "-" else np.nan
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        try:
            return float(s)
        except ValueError:
            return np.nan

    fund_cols = [c for c in df.columns if c not in ("Date", "Total")]
    rows = []
    for _, r0 in df.iterrows():
        raw = str(r0["Date"]).strip()
        # Farside dates look like "11 Jan 2024" or similar
        try:
            d = pd.to_datetime(raw, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            continue
        rec = {"date": d, "total": _num(r0.get("Total"))}
        for c in fund_cols:
            rec[c.lower()] = _num(r0.get(c))
        rows.append(rec)
    rows.sort(key=lambda x: x["date"])
    return rows


def fetch_cot_latest(asset="BTC"):
    """Latest 60 weekly COT reports. BTC only (CME 133741)."""
    from app.assets import get_asset
    cfg = get_asset(asset)
    if not cfg.cot_code:
        raise RuntimeError(f"no COT code for {asset}")
    url = "https://publicreporting.cftc.gov/resource/gpe5-46if.json"
    params = {
        "$where": f"cftc_contract_market_code='{cfg.cot_code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": 60,
    }
    data = _get(url, params).json()
    out = []
    for r in data:
        def _i(key, _row=r):
            try:
                return int(float(_row.get(key, 0) or 0))
            except Exception:
                return 0
        lf_l, lf_s = _i("lev_money_positions_long"), _i("lev_money_positions_short")
        am_l, am_s = _i("asset_mgr_positions_long"), _i("asset_mgr_positions_short")
        out.append({
            "date": str(r.get("report_date_as_yyyy_mm_dd", ""))[:10],
            "lf_long": lf_l, "lf_short": lf_s, "lf_net": lf_l - lf_s,
            "am_long": am_l, "am_short": am_s, "am_net": am_l - am_s,
            "oi": _i("open_interest_all"),
        })
    out.sort(key=lambda x: x["date"])
    return out


# ═══════════════════════════════════════════════════════════════════
#  EXPANDED WHALE COHORTS — all free, no keys, storage-aware
# ═══════════════════════════════════════════════════════════════════

def fetch_coinbase_price(asset="BTC"):
    """Coinbase spot (US institutional venue) — tiny response."""
    from app.assets import get_asset
    prod = get_asset(asset).coinbase_product
    d = _get(f"https://api.exchange.coinbase.com/products/{prod}/ticker").json()
    return {"price": float(d["price"]), "volume_24h": float(d.get("volume_24h") or 0)}


def fetch_coinbase_premium(asset="BTC"):
    """Coinbase vs Binance spot spread — US institutional flow proxy.
    Positive premium = US buyers paying up (bullish institutional signal)."""
    from app.assets import get_asset
    cfg = get_asset(asset)
    cb = fetch_coinbase_price(asset)
    bn_cache = _ak(asset, "bn_spot")
    bn = cache_get(bn_cache, 60)
    if bn is None:
        d = _get("https://api.binance.com/api/v3/ticker/price",
                 {"symbol": cfg.binance_spot}).json()
        bn = {"price": float(d["price"])}
        cache_set(bn_cache, bn)
    prem_bp = (cb["price"] / bn["price"] - 1.0) * 10000.0  # basis points
    return {"cb": cb["price"], "bn": bn["price"], "premium_bp": round(prem_bp, 2)}


def fetch_bybit_ticker(asset="BTC"):
    """Bybit linear — cross-exchange perp price + 24h volume."""
    from app.assets import get_asset
    sym = get_asset(asset).bybit_symbol
    d = _get("https://api.bybit.com/v5/market/tickers",
             {"category": "linear", "symbol": sym}).json()
    r = d["result"]["list"][0]
    return {
        "price": float(r["lastPrice"]),
        "volume_24h": float(r["volume24h"]),
        "turnover_24h": float(r["turnover24h"]),
    }


def fetch_bybit_ls(asset="BTC"):
    """Bybit top-trader long/short account ratio (5m)."""
    from app.assets import get_asset
    sym = get_asset(asset).bybit_symbol
    d = _get("https://api.bybit.com/v5/market/account-ratio",
             {"category": "linear", "symbol": sym, "period": "5min", "limit": 1}).json()
    r = d["result"]["list"][0]
    return {"long_pct": float(r["buyRatio"]), "short_pct": float(r["sellRatio"]),
            "t": int(r["timestamp"])}


def fetch_okx_ticker(asset="BTC"):
    """OKX spot — third venue for cross-check."""
    from app.assets import get_asset
    inst = get_asset(asset).okx_inst
    d = _get("https://www.okx.com/api/v5/market/ticker",
             {"instId": inst}, timeout=6).json()
    r = d["data"][0]
    return {"price": float(r["last"]), "vol_24h": float(r["volCcy24h"])}


def fetch_okx_ls(asset="BTC"):
    """OKX long/short account ratio (retail-ish, 5m)."""
    from app.assets import get_asset
    ccy = get_asset(asset).okx_ccy
    d = _get("https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio",
             {"ccy": ccy, "period": "5m"}, timeout=6).json()
    r = d["data"][0]
    # ratio = long_accounts / short_accounts
    ratio = float(r[1])
    long_pct = ratio / (1 + ratio) if ratio > 0 else 0.5
    return {"ratio": ratio, "long_pct": round(long_pct, 4), "short_pct": round(1 - long_pct, 4),
            "t": int(r[0])}


def fetch_deribit_dvol(asset="BTC"):
    """Deribit DVOL implied vol index — last 24h of hourly points."""
    from app.assets import get_asset
    ccy = get_asset(asset).deribit_currency
    if not ccy:
        raise RuntimeError(f"no Deribit DVOL for {asset}")
    now = int(time.time() * 1000)
    d = _get("https://www.deribit.com/api/v2/public/get_volatility_index_data",
             {"currency": ccy, "start_timestamp": now - 24 * 3600 * 1000,
              "end_timestamp": now, "resolution": 3600}).json()
    pts = d["result"]["data"]
    if not pts:
        raise RuntimeError("no DVOL data")
    latest = pts[-1]
    # 24h change
    first = pts[0]
    chg = latest[1] - first[1]
    return {"dvol": round(latest[1], 2), "dvol_chg_24h": round(chg, 2),
            "spark": [{"t": p[0], "v": round(p[1], 2)} for p in pts[-24:]]}


def fetch_deribit_options(asset="BTC"):
    """Deribit options — put/call OI + volume aggregates only (tiny cache).
    We fetch the full book but immediately reduce to 6 numbers."""
    from app.assets import get_asset
    ccy = get_asset(asset).deribit_currency
    if not ccy:
        raise RuntimeError(f"no Deribit options for {asset}")
    d = _get("https://www.deribit.com/api/v2/public/get_book_summary_by_currency",
             {"currency": ccy, "kind": "option"}).json()
    rows = d["result"]
    put_oi = call_oi = put_vol = call_vol = 0.0
    n_puts = n_calls = 0
    for r in rows:
        oi = float(r.get("open_interest") or 0)
        vol = float(r.get("volume_usd") or 0)  # sometimes volume
        if not vol:
            vol = float(r.get("volume") or 0) * float(r.get("mark_price") or 0)
        instrument = r.get("instrument_name", "")
        if instrument.startswith("BTC-PERPETUAL"):
            continue
        is_put = "-P" in instrument
        is_call = "-C" in instrument
        if is_put:
            put_oi += oi
            put_vol += vol
            n_puts += 1
        elif is_call:
            call_oi += oi
            call_vol += vol
            n_calls += 1
    pc_oi = (put_oi / call_oi) if call_oi > 0 else None
    pc_vol = (put_vol / call_vol) if call_vol > 0 else None
    return {
        "put_oi_btc": round(put_oi, 1), "call_oi_btc": round(call_oi, 1),
        "put_call_oi": round(pc_oi, 3) if pc_oi is not None else None,
        "put_call_vol": round(pc_vol, 3) if pc_vol is not None else None,
        "n_puts": n_puts, "n_calls": n_calls,
    }


def fetch_quarterly_basis(asset="BTC"):
    """Nearest Binance quarterly futures vs spot — arb-desk basis signal.
    High annualized basis = carry desks long spot / short perp (range regime)."""
    from app.assets import get_asset
    prefix = get_asset(asset).binance_quarterly_prefix
    info = _get("https://fapi.binance.com/fapi/v1/exchangeInfo").json()
    quarters = []
    for s in info["symbols"]:
        sym = s["symbol"]
        if sym.startswith(prefix) and s["status"] == "TRADING":
            # symbol like BTCUSDT_251226
            try:
                yy = int(sym[-6:-4])
                mm = int(sym[-4:-2])
                dd = int(sym[-2:])
                year = 2000 + yy
                from datetime import date
                delivery = date(year, mm, dd)
                quarters.append((delivery, sym))
            except Exception:
                continue
    now_date = datetime.now(UTC).date()
    future = sorted([(d, s) for d, s in quarters if d > now_date])
    if not future:
        raise RuntimeError(f"no quarterly contracts found for {asset}")
    delivery, sym = future[0]
    prem = _get("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol": sym}).json()
    index_price = float(prem["indexPrice"])
    mark_price = float(prem["markPrice"])
    days = (delivery - now_date).days
    basis_bp = (mark_price / index_price - 1.0) * 10000.0
    # annualize roughly
    ann_pct = (basis_bp / 10000.0) * (365.0 / max(days, 1)) * 100.0
    return {
        "symbol": sym, "delivery": delivery.isoformat(), "days_to_expiry": days,
        "mark": mark_price, "index": index_price,
        "basis_bp": round(basis_bp, 1), "annualized_pct": round(ann_pct, 2),
    }


def fetch_orderbook_imbalance(asset="BTC"):
    """Binance L2 depth snapshot — bid/ask volume in top 100 levels.
    >1 = bids stacked (support); <1 = asks stacked (resistance)."""
    from app.assets import get_asset
    sym = get_asset(asset).binance_spot
    d = _get("https://api.binance.com/api/v3/depth",
             {"symbol": sym, "limit": 100}).json()
    bids = sum(float(q) for _, q in d["bids"])
    asks = sum(float(q) for _, q in d["asks"])
    ratio = bids / asks if asks > 0 else None
    # also mid + spread
    best_bid = float(d["bids"][0][0])
    best_ask = float(d["asks"][0][0])
    spread_bp = (best_ask / best_bid - 1.0) * 10000.0
    return {
        "bid_vol": round(bids, 2), "ask_vol": round(asks, 2),
        "imbalance": round(ratio, 3) if ratio is not None else None,
        "best_bid": best_bid, "best_ask": best_ask,
        "spread_bp": round(spread_bp, 2),
    }


def fetch_stablecoin_premium(asset="BTC"):
    """USDT-USD premium on Coinbase — proxy for stablecoin demand / dry powder.
    >1.001 = people paying up for USDT (risk-on, capital entering).
    <0.999 = USDT discount (risk-off, redemptions)."""
    from app.assets import get_asset
    prod = get_asset(asset).stablecoin_product
    try:
        d = _get(f"https://api.exchange.coinbase.com/products/{prod}/ticker").json()
        px = float(d["price"])
    except Exception:
        # fallback: Binance USDCUSDT as rough proxy
        d = _get("https://api.binance.com/api/v3/ticker/price",
                 {"symbol": "USDCUSDT"}).json()
        px = 1.0 / float(d["price"])  # invert: USDC per USDT ~ inverse
    prem_bp = (px - 1.0) * 10000.0
    return {"usdt_usd": round(px, 5), "premium_bp": round(prem_bp, 2)}


def derive_whale_prints(hourly_rows):
    """Large-body hourly candles as OTC/whale print proxy (no extra API call).
    Body > 1.8× recent median body AND volume > 1.5× median → flag."""
    if not hourly_rows or len(hourly_rows) < 24:
        return {"count_24h": 0, "dir": "flat", "notional_hint": None}
    bodies = [abs(r["close"] - r["open"]) for r in hourly_rows]
    vols = [r["volume"] for r in hourly_rows]
    med_body = float(np.median(bodies[-48:])) if len(bodies) >= 48 else float(np.median(bodies))
    med_vol = float(np.median(vols[-48:])) if len(vols) >= 48 else float(np.median(vols))
    prints = []
    for r in hourly_rows[-24:]:
        body = abs(r["close"] - r["open"])
        if med_body > 0 and body > 1.8 * med_body and r["volume"] > 1.5 * med_vol:
            direction = "up" if r["close"] > r["open"] else "down"
            prints.append({"t": r["t"], "dir": direction, "body": round(body, 0),
                           "vol": round(r["volume"], 1)})
    up = sum(1 for p in prints if p["dir"] == "up")
    down = len(prints) - up
    if up > down:
        direction = "accumulation"
    elif down > up:
        direction = "distribution"
    else:
        direction = "mixed"
    return {"count_24h": len(prints), "up": up, "down": down,
            "dir": direction, "last3": prints[-3:]}


# ---------------------------------------------------------------- metrics
def taker_share_series(rows):
    return [None if r["volume"] <= 0 else r["taker_buy"] / r["volume"] for r in rows]


def funding_z(funding_rows, window=7):
    """z-score of latest funding rate vs rolling mean/std of prior window days (3 funding periods/day)."""
    if not funding_rows or len(funding_rows) < 30:
        return None, None
    rates = pd.Series([r["rate"] for r in funding_rows])
    # 3 periods/day → window days ≈ 3*window samples
    w = max(9, window * 3)
    hist = rates.iloc[:-1]
    if len(hist) < w:
        return None, float(rates.iloc[-1])
    mean = hist.iloc[-w:].mean()
    std = hist.iloc[-w:].std(ddof=0)
    last = float(rates.iloc[-1])
    z = 0.0 if std == 0 else float((last - mean) / std)
    return z, last


def _pct(a, b):
    if a is None or b is None or b == 0:
        return None
    return (a / b - 1.0) * 100.0


def build_snapshot(asset: str = "BTC") -> dict:
    """Pull (or reuse cache for) everything and assemble the 'today' payload."""
    from app.assets import get_asset
    cfg = get_asset(asset)
    ak = lambda n: _ak(asset, n)  # noqa: E731
    fetched = {"at": datetime.now(UTC).isoformat(), "sources": {}, "asset": cfg.key}
    errors = []

    def run(name, ttl, fn, *args):
        ckey = ak(name)
        cached = cache_get(ckey, ttl)
        if cached is not None:
            fetched["sources"][name] = {"mode": "cache", "at": cache_meta(ckey)}
            return cached
        try:
            data = fn(*args)
            cache_set(ckey, data)
            fetched["sources"][name] = {"mode": "live", "at": cache_meta(ckey)}
            return data
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
            stale = cache_get(ckey, max_age=30 * 24 * 3600)  # allow very stale fallback
            fetched["sources"][name] = {"mode": "error", "error": str(e)}
            return stale

    with ThreadPoolExecutor(max_workers=12) as ex:
        futs = {
            ex.submit(run, "daily", TTL_INTRADAY, fetch_daily_klines, 420, asset): "daily",
            ex.submit(run, "hourly", TTL_INTRADAY, fetch_hourly_klines, 72, asset): "hourly",
            ex.submit(run, "funding", TTL_INTRADAY, fetch_funding_history, 500, asset): "funding",
            ex.submit(run, "premium", TTL_INTRADAY, fetch_premium, asset): "premium",
            ex.submit(run, "oi", TTL_INTRADAY, fetch_open_interest, asset): "oi",
            ex.submit(run, "oi_hist", TTL_INTRADAY, fetch_oi_hist, asset): "oi_hist",
            ex.submit(run, "taker_ratio", TTL_INTRADAY, fetch_taker_ratio, asset): "taker_ratio",
            ex.submit(run, "global_ls", TTL_INTRADAY, fetch_global_ls, asset): "global_ls",
            ex.submit(run, "top_ls", TTL_INTRADAY, fetch_top_ls, asset): "top_ls",
            ex.submit(run, "etf", TTL_ETF, fetch_etf_flows, asset): "etf",
            ex.submit(run, "cot", TTL_COT, fetch_cot_latest, asset): "cot",
            # --- expanded whale cohorts ---
            ex.submit(run, "cb_premium", TTL_INTRADAY, fetch_coinbase_premium, asset): "cb_premium",
            ex.submit(run, "bybit_ls", TTL_INTRADAY, fetch_bybit_ls, asset): "bybit_ls",
            ex.submit(run, "bybit_tk", TTL_INTRADAY, fetch_bybit_ticker, asset): "bybit_tk",
            ex.submit(run, "okx_ls", TTL_INTRADAY, fetch_okx_ls, asset): "okx_ls",
            ex.submit(run, "okx_tk", TTL_INTRADAY, fetch_okx_ticker, asset): "okx_tk",
            ex.submit(run, "dvol", TTL_INTRADAY, fetch_deribit_dvol, asset): "dvol",
            ex.submit(run, "options", TTL_INTRADAY, fetch_deribit_options, asset): "options",
            ex.submit(run, "basis", TTL_INTRADAY, fetch_quarterly_basis, asset): "basis",
            ex.submit(run, "obook", TTL_INTRADAY // 3, fetch_orderbook_imbalance, asset): "obook",
            ex.submit(run, "stable", TTL_INTRADAY, fetch_stablecoin_premium, asset): "stable",
        }
        res = {}
        for fut in as_completed(futs):
            key = futs[fut]
            try:
                res[key] = fut.result()
            except Exception as e:  # noqa: BLE001
                res[key] = None
                errors.append(f"{key}: {e}")

    daily = res.get("daily") or []
    hourly = res.get("hourly") or []
    funding = res.get("funding") or []
    premium = res.get("premium") or {}
    oi = res.get("oi") or {}
    oi_hist = res.get("oi_hist") or []
    taker_ratio = res.get("taker_ratio") or []
    global_ls = res.get("global_ls") or []
    top_ls = res.get("top_ls") or []
    etf_rows = res.get("etf") or []
    cot = res.get("cot") or []
    # expanded cohorts
    cb_premium = res.get("cb_premium") or {}
    bybit_ls = res.get("bybit_ls") or {}
    bybit_tk = res.get("bybit_tk") or {}
    okx_ls = res.get("okx_ls") or {}
    okx_tk = res.get("okx_tk") or {}
    dvol = res.get("dvol") or {}
    options = res.get("options") or {}
    basis = res.get("basis") or {}
    obook = res.get("obook") or {}
    stable = res.get("stable") or {}

    if not daily:
        raise RuntimeError("no price data — " + "; ".join(errors[:3]))

    # ---- enrich daily rows ----
    for i, r in enumerate(daily):
        prev = daily[i - 1]["close"] if i else None
        r["ret_pct"] = _pct(r["close"], prev)
        r["taker_share"] = None if r["volume"] <= 0 else r["taker_buy"] / r["volume"]

    # ETF map
    etf_by_date = {r["date"]: r for r in etf_rows}
    etf_dates = sorted(etf_by_date)
    for r in daily:
        etf_row = etf_by_date.get(r["date"])
        r["etf_total"] = etf_row["total"] if etf_row else None
        r["etf_ibit"] = etf_row.get("ibit") if etf_row else None
    # rolling 5 published flow days
    etf_series = [(d, etf_by_date[d]["total"]) for d in etf_dates
                  if etf_by_date[d]["total"] is not None and not np.isnan(etf_by_date[d]["total"])]
    etf_5d = sum(v for _, v in etf_series[-5:]) if etf_series else None
    etf_latest = {"date": etf_series[-1][0], "total": etf_series[-1][1]} if etf_series else None
    # last 10 flow days for spark
    etf_last10 = [{"date": d, "total": v} for d, v in etf_series[-10:]]

    fz, last_funding = funding_z(funding)

    # COT latest + weekly change
    cot_latest = cot[-1] if cot else None
    cot_prev = cot[-2] if len(cot) > 1 else None
    lf_chg = (cot_latest["lf_net"] - cot_prev["lf_net"]) if cot_latest and cot_prev else None

    # OI change
    oi_now = oi.get("oi_btc")
    oi_prev = oi_hist[-2]["oi"] if len(oi_hist) >= 2 else None
    oi_prev_day = oi_hist[-24]["oi"] if len(oi_hist) >= 24 else oi_prev
    oi_chg_pct_24h = _pct(oi_now, oi_prev_day)

    # taker ratio latest (futures endpoint, official)
    tr = taker_ratio[-1] if taker_ratio else None
    gls = global_ls[-1] if global_ls else None
    tls = top_ls[-1] if top_ls else None

    today = daily[-1]
    hourly_today = hourly[-24:] if hourly else []
    h_taker = (sum(h["taker_buy"] for h in hourly_today) / sum(h["volume"] for h in hourly_today)
               if hourly_today and sum(h["volume"] for h in hourly_today) > 0 else None)

    # funding z history spark (last 30 days worth)
    fz_series = []
    if funding and len(funding) > 60:
        rates = pd.Series([r["rate"] for r in funding])
        w = 21
        for i in range(len(rates) - 30, len(rates)):
            hist = rates.iloc[max(0, i - w):i]
            if len(hist) < 9 or hist.std(ddof=0) == 0:
                fz_series.append({"t": funding[i]["t"], "z": 0.0})
            else:
                fz_series.append({"t": funding[i]["t"],
                                  "z": float((rates.iloc[i] - hist.mean()) / hist.std(ddof=0))})

    # whale prints from hourly (no extra API)
    whales = derive_whale_prints(hourly)

    snap = {
        "generated_at": fetched["at"],
        "asset": cfg.key,
        "asset_name": cfg.name,
        "sources": fetched["sources"],
        "errors": errors,
        "price": {
            "date": today["date"],
            "close": today["close"], "open": today["open"],
            "high": today["high"], "low": today["low"],
            "ret_pct": today["ret_pct"],
            "volume": today["volume"],
            "taker_share": today["taker_share"],
            "taker_share_24h_hourly": h_taker,
            "mark": premium.get("mark"),
            "next_funding_ts": premium.get("next_funding"),
            "funding_rate_next": premium.get("funding_rate"),
        },
        "funding": {"z": fz, "rate": last_funding, "spark": fz_series[-40:]},
        "oi": {"btc": oi_now, "chg_24h_pct": oi_chg_pct_24h, "spark": oi_hist[-30:]},
        "etf": {"latest": etf_latest, "flow_5d": etf_5d, "last10": etf_last10,
                "published_through": etf_latest["date"] if etf_latest else None},
        "cot": {"latest": cot_latest, "lf_net_chg_week": lf_chg, "history": cot},
        "ratios": {
            "taker": tr,
            "global_ls": gls,
            "top_ls": tls,
        },
        # --- expanded whale cohorts ---
        "cross": {
            "coinbase_premium": cb_premium,
            "bybit": bybit_tk,
            "bybit_ls": bybit_ls,
            "okx": okx_tk,
            "okx_ls": okx_ls,
        },
        "options": {"dvol": dvol, "book": options},
        "basis": basis,
        "obook": obook,
        "stable": stable,
        "whales": whales,
        "tape": {  # last 14 trading days, ready-to-render
            "rows": [
                {
                    "date": r["date"],
                    "close": r["close"],
                    "ret_pct": r["ret_pct"],
                    "taker": r["taker_share"],
                    "etf": r.get("etf_total"),
                    "volume": r["volume"],
                }
                for r in daily[-14:]
            ][::-1]
        },
        "hourly_last24": [
            {"date": h["date"], "close": h["close"], "volume": h["volume"],
             "taker": None if h["volume"] <= 0 else h["taker_buy"] / h["volume"],
             "ret_pct": None}
            for h in hourly_today
        ],
    }
    # hourly returns
    prev = None
    for h in snap["hourly_last24"]:
        if prev is not None and prev > 0:
            h["ret_pct"] = (h["close"] / prev - 1) * 100
        prev = h["close"]

    snap["bias"] = compute_bias(snap)
    snap["players"] = who_is_winning(snap)
    return snap


# ---------------------------------------------------------------- bias + narrative
def compute_bias(snap: dict) -> dict:
    """0–10 daily-bias score from live inputs (report §5.1)."""
    factors = []

    # 1 ETF 5d
    e5 = snap["etf"]["flow_5d"]
    pts = 0
    reason = "ETF flow unavailable"
    if e5 is not None:
        if e5 > 1000:
            pts, reason = 3, f"Institutions bought ${e5:,.0f}m over 5 published days — strong demand"
        elif e5 > 0:
            pts, reason = 2, f"Institutions net buyers (+${e5:,.0f}m over 5 days)"
        elif e5 < -500:
            pts, reason = -3, f"Institutions sold ${abs(e5):,.0f}m over 5 days — strong supply"
        elif e5 < 0:
            pts, reason = -2, f"Institutions net sellers (−${abs(e5):,.0f}m over 5 days)"
        else:
            reason = "ETF flow flat"
    factors.append({"name": "ETF 5-day flow (institutions)", "pts": pts, "reason": reason,
                    "value": e5, "unit": "US$m"})

    # 2 taker share
    ts = snap["price"]["taker_share"]
    pts = 0
    reason = "Taker share unavailable"
    if ts is not None:
        if ts >= 0.55:
            pts, reason = 2, f"Aggressive buyers took {ts*100:.1f}% of volume — extreme (d2/d3 continuation edge)"
        elif ts <= 0.45:
            pts, reason = -2, f"Aggressive sellers hit {100-ts*100:.1f}% of volume — extreme"
        elif ts > 0.51:
            reason = f"Buyers slightly dominant ({ts*100:.1f}%)"
        elif ts < 0.49:
            reason = f"Sellers slightly dominant ({ts*100:.1f}%)"
        else:
            reason = f"Takers balanced ({ts*100:.1f}%)"
    factors.append({"name": "Taker-buy share (aggressive flow)", "pts": pts, "reason": reason,
                    "value": None if ts is None else ts * 100, "unit": "%"})

    # 3 CME lf weekly change
    chg = snap["cot"]["lf_net_chg_week"]
    pts = 0
    reason = "COT weekly change unavailable"
    if chg is not None:
        # rough top-decile threshold in contracts (historical ~+1500)
        if chg >= 1000:
            pts, reason = 1, f"Hedge funds added {chg:+,.0f} lf contracts last week (top-decile adds: 60% up next wk)"
        elif chg <= -1500:
            reason = f"Hedge funds cut {chg:+,.0f} lf contracts last week"
        else:
            reason = f"Hedge-fund lf_net change {chg:+,.0f} (neutral)"
    factors.append({"name": "CME hedge funds Δ (weekly)", "pts": pts, "reason": reason,
                    "value": chg, "unit": "contracts"})

    # 4 lf_net level percentile vs history in snap
    lf = snap["cot"]["latest"]["lf_net"] if snap["cot"]["latest"] else None
    hist = [c["lf_net"] for c in snap["cot"]["history"]]
    pts = 0
    reason = "COT level unavailable"
    pctile = None
    if lf is not None and len(hist) >= 5:
        pctile = 100.0 * sum(1 for h in hist if h <= lf) / len(hist)
        if pctile <= 15:
            pts, reason = 2, f"Hedge funds near max net-short ({pctile:.0f}th pctile) — contrarian long (p=0.003 at 4wk)"
        elif pctile >= 90:
            pts, reason = -1, f"Hedge funds least short in years ({pctile:.0f}th pctile) — worst forward month historically"
        else:
            reason = f"lf_net at {pctile:.0f}th pctile of history"
    factors.append({"name": "CME lf_net level", "pts": pts, "reason": reason,
                    "value": pctile, "unit": "pctile"})

    # 5 funding z
    fz = snap["funding"]["z"]
    pts = 0
    reason = "Funding z unavailable"
    if fz is not None:
        if fz <= -2:
            pts, reason = 2, f"Funding z={fz:.1f} — crowded shorts, squeeze regime (+3.2%/wk historically, n=30)"
        elif fz >= 2:
            reason = f"Funding z={fz:.1f} — crowded longs (no crash premium in our sample)"
        else:
            reason = f"Funding z={fz:.1f} — neutral leverage"
    factors.append({"name": "Funding z-score (crowding)", "pts": pts, "reason": reason,
                    "value": fz, "unit": "z"})

    # 6 OI direction (informational tilt)
    oi_c = snap["oi"]["chg_24h_pct"]
    pts = 0
    reason = "OI change unavailable"
    if oi_c is not None:
        ret = snap["price"]["ret_pct"] or 0
        if oi_c > 1 and ret > 0:
            reason = f"OI +{oi_c:.1f}% with price up — new longs entering"
        elif oi_c > 1 and ret < 0:
            reason = f"OI +{oi_c:.1f}% with price down — new shorts entering / longs trapped"
        elif oi_c < -1 and ret < 0:
            reason = f"OI {oi_c:.1f}% with price down — longs closing (capitulation)"
        elif oi_c < -1 and ret > 0:
            reason = f"OI {oi_c:.1f}% with price up — shorts covering"
        else:
            reason = f"OI change {oi_c:+.1f}% — flat positioning"
    factors.append({"name": "Open-interest regime", "pts": pts, "reason": reason,
                    "value": oi_c, "unit": "%", "info": True})

    # 7 Coinbase premium (US institutional)
    cbp = snap.get("cross", {}).get("coinbase_premium", {}).get("premium_bp")
    pts = 0
    reason = "Coinbase premium unavailable"
    if cbp is not None:
        if cbp >= 8:
            pts, reason = 1, f"Coinbase +{cbp:.1f}bp — US institutions paying up"
        elif cbp <= -8:
            pts, reason = -1, f"Coinbase {cbp:.1f}bp — US sellers hitting bid"
        else:
            reason = f"Coinbase premium {cbp:+.1f}bp — US flow balanced"
    factors.append({"name": "US institutional (Coinbase premium)", "pts": pts, "reason": reason,
                    "value": cbp, "unit": "bp"})

    # 8 Deribit put/call OI
    pcr = snap.get("options", {}).get("book", {}).get("put_call_oi")
    pts = 0
    reason = "Options P/C unavailable"
    if pcr is not None:
        if pcr >= 1.3:
            pts, reason = -1, f"Put/Call {pcr:.2f} — heavy hedging / downside protection"
        elif pcr <= 0.7:
            pts, reason = 1, f"Put/Call {pcr:.2f} — call-heavy, complacent or bullish skew"
        else:
            reason = f"Put/Call {pcr:.2f} — balanced"
    factors.append({"name": "Options positioning (Deribit P/C)", "pts": pts, "reason": reason,
                    "value": pcr, "unit": "ratio"})

    # 9 Order-book imbalance
    imb = snap.get("obook", {}).get("imbalance")
    pts = 0
    reason = "Order-book imbalance unavailable"
    if imb is not None:
        if imb >= 1.15:
            pts, reason = 1, f"Depth {imb:.2f}× bid-heavy — passive support"
        elif imb <= 0.87:
            pts, reason = -1, f"Depth {imb:.2f}× ask-heavy — passive supply"
        else:
            reason = f"Depth {imb:.2f}× — balanced"
    factors.append({"name": "Order-book imbalance (L2)", "pts": pts, "reason": reason,
                    "value": imb, "unit": "×"})

    # 10 stablecoin premium
    sp = snap.get("stable", {}).get("premium_bp")
    pts = 0
    reason = "Stablecoin premium unavailable"
    if sp is not None:
        if sp >= 3:
            pts, reason = 1, f"USDT +{sp:.1f}bp — dry powder / capital entering"
        elif sp <= -3:
            pts, reason = -1, f"USDT {sp:.1f}bp — redemptions, risk-off"
        else:
            reason = f"USDT {sp:+.1f}bp vs $1 — flat"
    factors.append({"name": "Stablecoin / dry powder", "pts": pts, "reason": reason,
                    "value": sp, "unit": "bp"})

    score = sum(f["pts"] for f in factors)
    if score >= 6:
        state, color, rule = "STRONG BULL", "bull", "Longs only (or stand aside on shorts). Expect continuation."
    elif score >= 2:
        state, color, rule = "MILD BULL", "bull", "Longs with tighter invalidation. Prefer dips into US session."
    elif score <= -6:
        state, color, rule = "STRONG BEAR", "bear", "Shorts only (or stand aside on longs). Outflow asymmetry helps."
    elif score <= -2:
        state, color, rule = "MILD BEAR", "bear", "Only shorts. Aligned-bear is the one negative-expectancy state."
    else:
        state, color, rule = "NEUTRAL / CHOP", "neutral", "Coin-flip baseline (50.8% hit). No daily-bias trades — drop to intraday or stand aside."

    return {"score": score, "state": state, "color": color, "rule": rule, "factors": factors}


def who_is_winning(snap: dict) -> dict:
    """Plain-English: who controls the tape today, and why. 15 cohorts."""
    players = []
    bull = bear = 0

    # --- 1. aggressive takers (Binance perps, realtime)
    ts = snap["price"]["taker_share"]
    if ts is not None:
        if ts >= 0.52:
            side, bull = "BUYERS", bull + 1
            note = f"Taker-buy {ts*100:.1f}% — aggressive flow hitting asks"
        elif ts <= 0.48:
            side, bear = "SELLERS", bear + 1
            note = f"Taker-buy {ts*100:.1f}% — aggressive flow hitting bids"
        else:
            side = "NEUTRAL"
            note = f"Taker-buy {ts*100:.1f}% — balanced aggressive flow"
        players.append({"cohort": "Aggressive takers (Binance perps)", "side": side, "note": note,
                        "lag": "real-time", "weight": 2})

    # --- 2. institutions via ETF (T+1)
    e5 = snap["etf"]["flow_5d"]
    el = snap["etf"]["latest"]
    if e5 is not None:
        if e5 > 100:
            side, bull = "BUYERS", bull + 1
            note = f"ETFs +${e5:,.0f}m in 5d (thru {el['date'] if el else '?'}) — APs buying spot"
        elif e5 < -100:
            side, bear = "SELLERS", bear + 1
            note = f"ETFs shed ${abs(e5):,.0f}m in 5d — supply into US cash"
        else:
            side = "NEUTRAL"
            note = f"ETF 5d flow {e5:+,.0f}m — no institutional edge"
        players.append({"cohort": "Institutions (US spot ETFs)", "side": side, "note": note,
                        "lag": "T+1 (yesterday's print)", "weight": 2})

    # --- 3. CME hedge funds (COT weekly, 3–5d lag)
    chg = snap["cot"]["lf_net_chg_week"]
    if chg is not None:
        if chg >= 800:
            side, bull = "BUYERS", bull + 1
            note = f"Hedge funds added {chg:+,.0f} lf contracts — short-cover / new longs"
        elif chg <= -800:
            side, bear = "SELLERS", bear + 1
            note = f"Hedge funds cut {chg:+,.0f} lf contracts — more CME shorts"
        else:
            side = "NEUTRAL"
            note = f"Hedge-fund lf_net Δ {chg:+,.0f} — quiet week"
        players.append({"cohort": "CME hedge funds (COT)", "side": side, "note": note,
                        "lag": "3–5 days (Tue snapshot)", "weight": 1})

    # --- 4. leverage / funding (8h)
    fz = snap["funding"]["z"]
    fr = snap["funding"]["rate"]
    if fz is not None:
        if fz <= -2:
            side, bull = "SHORTS PAIN", bull + 1
            note = f"Funding z={fz:.1f} — shorts crowded, squeeze fuel"
        elif fz >= 2:
            side, bear = "LONGS PAIN", bear + 1
            note = f"Funding z={fz:.1f} — longs crowded, pullback fuel"
        else:
            side = "NEUTRAL"
            note = f"Funding z={fz:.1f}, next {fr:.6f} — leverage not stretched"
        players.append({"cohort": "Leveraged perp book (funding)", "side": side, "note": note,
                        "lag": "8h settlement", "weight": 1})

    # --- 5. retail accounts (Binance global L/S)
    gls = snap["ratios"]["global_ls"]
    if gls and gls.get("long_pct") is not None:
        lp = gls["long_pct"]
        if lp >= 0.60:
            side, bear = "RETAIL LONG", bear + 1
            note = f"{lp*100:.0f}% accounts long — retail usually wrong at extremes"
        elif lp <= 0.40:
            side, bull = "RETAIL SHORT", bull + 1
            note = f"Only {lp*100:.0f}% accounts long — retail flushed / short"
        else:
            side = "NEUTRAL"
            note = f"Accounts {lp*100:.0f}% long / {(1-lp)*100:.0f}% short"
        players.append({"cohort": "Retail accounts (Binance L/S)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 6. top trader positions (Binance)
    tls = snap["ratios"]["top_ls"]
    if tls and tls.get("long_pct") is not None:
        lp = tls["long_pct"]
        if lp >= 0.60:
            side, bull = "TOP LONG", bull + 1
            note = f"Top traders {lp*100:.0f}% long by position — large accounts leaning long"
        elif lp <= 0.40:
            side, bear = "TOP SHORT", bear + 1
            note = f"Top traders {lp*100:.0f}% long — large accounts leaning short"
        else:
            side = "NEUTRAL"
            note = f"Top traders {lp*100:.0f}% long"
        players.append({"cohort": "Top trader positions (Binance)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 7. new money (OI regime)
    oi_c = snap["oi"]["chg_24h_pct"]
    ret = snap["price"]["ret_pct"] or 0
    if oi_c is not None:
        if oi_c > 1 and ret > 0:
            regime = "NEW LONGS"
            note = f"OI {oi_c:+.1f}% with price {ret:+.1f}% — fresh longs pushing"
        elif oi_c > 1 and ret < 0:
            regime = "NEW SHORTS"
            note = f"OI {oi_c:+.1f}% with price {ret:+.1f}% — shorts building into weakness"
        elif oi_c < -1 and ret < 0:
            regime = "LONGS OUT"
            note = f"OI {oi_c:+.1f}% with price {ret:+.1f}% — longs closing / stopped"
        elif oi_c < -1 and ret > 0:
            regime = "SHORTS OUT"
            note = f"OI {oi_c:+.1f}% with price {ret:+.1f}% — short covering"
        else:
            regime = "FLAT"
            note = f"OI {oi_c:+.1f}% — positioning quiet"
        players.append({"cohort": "New money (OI regime)", "side": regime, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 8. Coinbase–Binance premium (US institutional flow)
    cb = snap.get("cross", {}).get("coinbase_premium", {})
    pbp = cb.get("premium_bp")
    if pbp is not None:
        if pbp >= 5:
            side, bull = "US BUYERS", bull + 1
            note = f"Coinbase +{pbp:.1f}bp over Binance — US institutions paying up"
        elif pbp <= -5:
            side, bear = "US SELLERS", bear + 1
            note = f"Coinbase −{abs(pbp):.1f}bp — US sellers hitting bid"
        else:
            side = "NEUTRAL"
            note = f"Coinbase premium {pbp:+.1f}bp — US flow balanced"
        players.append({"cohort": "US institutions (Coinbase premium)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 9. Bybit top traders L/S
    bls = snap.get("cross", {}).get("bybit_ls", {})
    if bls and bls.get("long_pct") is not None:
        lp = bls["long_pct"]
        if lp >= 0.65:
            side, bull = "BYBIT LONG", bull + 1
            note = f"Bybit top traders {lp*100:.0f}% long by accounts"
        elif lp <= 0.35:
            side, bear = "BYBIT SHORT", bear + 1
            note = f"Bybit top traders {lp*100:.0f}% long — leaning short"
        else:
            side = "NEUTRAL"
            note = f"Bybit top traders {lp*100:.0f}% long"
        players.append({"cohort": "Bybit top traders", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 10. OKX retail L/S
    ols = snap.get("cross", {}).get("okx_ls", {})
    if ols and ols.get("long_pct") is not None:
        lp = ols["long_pct"]
        if lp >= 0.62:
            side, bear = "OKX RETAIL LONG", bear + 1
            note = f"OKX retail {lp*100:.0f}% long — often a fade signal"
        elif lp <= 0.38:
            side, bull = "OKX RETAIL SHORT", bull + 1
            note = f"OKX retail {lp*100:.0f}% long — flushed"
        else:
            side = "NEUTRAL"
            note = f"OKX retail {lp*100:.0f}% long"
        players.append({"cohort": "OKX retail accounts", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 11. Deribit options — put/call OI
    pcr = snap.get("options", {}).get("book", {}).get("put_call_oi")
    if pcr is not None:
        if pcr >= 1.2:
            side, bear = "OPTIONS HEDGING", bear + 1
            note = f"Put/Call OI {pcr:.2f} — heavy downside protection / hedging demand"
        elif pcr <= 0.7:
            side, bull = "OPTIONS SKEW CALL", bull + 1
            note = f"Put/Call OI {pcr:.2f} — call-heavy positioning"
        else:
            side = "NEUTRAL"
            note = f"Put/Call OI {pcr:.2f} — balanced options book"
        players.append({"cohort": "Options desks (Deribit P/C)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 12. DVOL implied volatility
    dvol = snap.get("options", {}).get("dvol", {})
    dv = dvol.get("dvol")
    dvc = dvol.get("dvol_chg_24h")
    if dv is not None:
        if dv >= 65:
            note = f"DVOL {dv:.1f} ({dvc:+.1f} in 24h) — high fear, options expensive"
            players.append({"cohort": "Vol traders (DVOL)", "side": "HIGH FEAR", "note": note,
                            "lag": "real-time", "weight": 1})
        elif dv <= 40:
            note = f"DVOL {dv:.1f} ({dvc:+.1f}) — complacent vol, cheap options"
            players.append({"cohort": "Vol traders (DVOL)", "side": "COMPLACENT", "note": note,
                            "lag": "real-time", "weight": 1})
        else:
            note = f"DVOL {dv:.1f} ({dvc:+.1f}) — moderate vol"
            players.append({"cohort": "Vol traders (DVOL)", "side": "NEUTRAL", "note": note,
                            "lag": "real-time", "weight": 1})

    # --- 13. Quarterly basis / arb desks
    bas = snap.get("basis", {})
    ann = bas.get("annualized_pct")
    if ann is not None:
        if ann >= 8:
            side, bull = "CARRY LONGS", bull + 1
            note = f"Quarterly basis {ann:.1f}% ann. — arb desks long spot / short perp (range)"
        elif ann <= 2:
            side, bear = "CARRY FLAT", bear + 1
            note = f"Basis {ann:.1f}% ann. — carry compressed, no arb demand"
        else:
            side = "NEUTRAL"
            note = f"Basis {ann:.1f}% ann. — moderate carry"
        players.append({"cohort": "Basis / carry desks", "side": side, "note": note,
                        "lag": f"expiry {bas.get('days_to_expiry', '?')}d", "weight": 1})

    # --- 14. Order book imbalance
    ob = snap.get("obook", {})
    imb = ob.get("imbalance")
    if imb is not None:
        if imb >= 1.15:
            side, bull = "BIDS STACKED", bull + 1
            note = f"Depth imbalance {imb:.2f}× — heavy bids (support)"
        elif imb <= 0.87:
            side, bear = "ASKS STACKED", bear + 1
            note = f"Depth imbalance {imb:.2f}× — heavy asks (resistance)"
        else:
            side = "NEUTRAL"
            note = f"Depth imbalance {imb:.2f}× — balanced book"
        players.append({"cohort": "Market makers (L2 depth)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 15. stablecoin premium / dry powder
    st = snap.get("stable", {})
    sp = st.get("premium_bp")
    if sp is not None:
        if sp >= 3:
            side, bull = "DRY POWDER", bull + 1
            note = f"USDT +{sp:.1f}bp over $1 — capital entering, risk-on"
        elif sp <= -3:
            side, bear = "REDEMPTIONS", bear + 1
            note = f"USDT −{abs(sp):.1f}bp discount — redemptions, risk-off"
        else:
            side = "NEUTRAL"
            note = f"USDT {sp:+.1f}bp vs $1 — stablecoin demand flat"
        players.append({"cohort": "Stablecoin / dry powder", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- 16. whale prints (large-body candles, OTC proxy)
    wh = snap.get("whales", {})
    if wh and wh.get("count_24h", 0) > 0:
        d = wh["dir"]
        if d == "accumulation":
            side, bull = "WHALE ACCUM", bull + 1
            note = f"{wh['count_24h']} large up-bodies in 24h — OTC / whale accumulation"
        elif d == "distribution":
            side, bear = "WHALE DISTRIB", bear + 1
            note = f"{wh['count_24h']} large down-bodies in 24h — distribution"
        else:
            side = "NEUTRAL"
            note = f"{wh['count_24h']} large bodies ({wh.get('up',0)}↑/{wh.get('down',0)}↓) — mixed"
        players.append({"cohort": "Whale prints (large candles)", "side": side, "note": note,
                        "lag": "real-time", "weight": 1})

    # --- verdict
    directional_sides = ("BUYERS", "SELLERS", "US BUYERS", "US SELLERS",
                         "BYBIT LONG", "BYBIT SHORT", "OKX RETAIL LONG", "OKX RETAIL SHORT",
                         "OPTIONS SKEW CALL", "CARRY LONGS", "CARRY FLAT", "DRY POWDER", "REDEMPTIONS",
                         "BIDS STACKED", "ASKS STACKED", "WHALE ACCUM", "WHALE DISTRIB")
    directional = [p for p in players if p["side"] in directional_sides]
    if bull > bear:
        winner, win_side = "BUYERS", "bull"
        verdict = (f"Buyers control the tape ({bull}–{bear} on {len(directional)} directional cohorts). "
                   f"Price tends to follow aggressive + institutional flow when they agree.")
    elif bear > bull:
        winner, win_side = "SELLERS", "bear"
        verdict = (f"Sellers control the tape ({bear}–{bull} on {len(directional)} directional cohorts). "
                   f"Outflow + aggressive selling is the historically asymmetric side.")
    else:
        winner, win_side = "NOBODY", "neutral"
        verdict = "No side in control — mixed signals across cohorts. Baseline is a coin flip; stand aside on bias trades."

    # price confirmation
    if ret is not None:
        if (win_side == "bull" and ret > 0.3) or (win_side == "bear" and ret < -0.3):
            verdict += f" Price today {ret:+.1f}% confirms the flow."
        elif (win_side == "bull" and ret < -0.5) or (win_side == "bear" and ret > 0.5):
            verdict += f" Price today {ret:+.1f}% is FIGHTING the flow — wait for alignment."
        else:
            verdict += f" Price today {ret:+.1f}% — watch the US session for confirmation."

    return {"bull_pts": bull, "bear_pts": bear, "winner": winner, "color": win_side,
            "verdict": verdict, "players": players}


def history_panel(limit=90) -> list:
    """Last N enriched daily rows for the history table (cached daily)."""
    cached = cache_get("daily", TTL_INTRADAY)
    if not cached:
        cached = fetch_daily_klines(limit)
        cache_set("daily", cached)
    etf = cache_get("etf", TTL_ETF) or []
    etf_by = {r["date"]: r.get("total") for r in etf}
    out = []
    for r in cached[-limit:]:
        prev = None
        # find previous row in full series
        idx = cached.index(r)
        if idx > 0:
            prev = cached[idx - 1]["close"]
        ret = _pct(r["close"], prev)
        ts = None if r["volume"] <= 0 else r["taker_buy"] / r["volume"]
        out.append({
            "date": r["date"], "close": r["close"], "ret_pct": ret,
            "taker": None if ts is None else ts * 100,
            "etf": etf_by.get(r["date"]),
            "volume": r["volume"],
        })
    return out[::-1]


def _trim_cache(max_total_bytes: int = 900_000):
    """Keep app/cache under max_total_bytes by removing oldest / largest files."""
    cache_dir = CACHE
    if not os.path.isdir(cache_dir):
        return
    files = [os.path.join(cache_dir, f) for f in os.listdir(cache_dir) if f.endswith(".json")]
    total = sum(os.path.getsize(f) for f in files)
    if total <= max_total_bytes:
        return
    # sort by mtime ascending (oldest first)
    files.sort(key=lambda f: os.path.getsize(f), reverse=True)  # biggest first
    for f in files:
        if total <= max_total_bytes:
            break
        sz = os.path.getsize(f)
        try:
            os.remove(f)
            total -= sz
        except OSError:
            pass


# ---------------------------------------------------------------- entry
def main():
    t0 = time.time()
    snap = build_snapshot()
    print(f"snapshot ok in {time.time()-t0:.1f}s  bias={snap['bias']['score']} ({snap['bias']['state']})  "
          f"winner={snap['players']['winner']}  price={snap['price']['close']}")
    if snap["errors"]:
        print("partial errors:", snap["errors"][:5])
    out = os.path.join(CACHE, "latest_snapshot.json")
    with open(out, "w") as f:
        json.dump(snap, f, indent=1)
    print("wrote", out)
    _trim_cache()
    print("cache trimmed:", sum(os.path.getsize(os.path.join(CACHE, f))
                                for f in os.listdir(CACHE) if f.endswith(".json")), "bytes")


if __name__ == "__main__":
    # allow `python app/live_fetch.py` as well as `-m app.live_fetch`
    sys.path.insert(0, ROOT)
    main()
