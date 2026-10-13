"""Shared fixtures — mock snapshot with all 15 cohorts populated."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest


@pytest.fixture
def full_snapshot() -> dict[str, Any]:
    """A rich snapshot covering every cohort and bias factor."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {
            "daily": {"mode": "live", "at": "2026-10-13T17:00:00Z"},
            "etf": {"mode": "cache", "at": "2026-10-13T16:00:00Z"},
        },
        "errors": [],
        "price": {
            "date": "2026-10-13",
            "close": 83245.99,
            "open": 81800.0,
            "high": 84100.0,
            "low": 81500.0,
            "ret_pct": 1.71,
            "volume": 25000.0,
            "taker_share": 0.528,
            "taker_share_24h_hourly": [],
            "mark": 83250.0,
            "next_funding_ts": 1791920000000,
            "funding_rate_next": 0.000035,
        },
        "funding": {"z": 0.7, "rate": 0.000035, "spark": []},
        "oi": {"btc": 94316.0, "chg_24h_pct": -12.4, "spark": []},
        "etf": {
            "latest": {"date": "2026-10-10", "total": 0.0},
            "flow_5d": -773.0,
            "last10": [],
            "published_through": "2026-10-10",
        },
        "cot": {
            "latest": {
                "date": "2026-10-06",
                "lf_long": 1000,
                "lf_short": 7852,
                "lf_net": -6852,
                "am_long": 5000,
                "am_short": 2000,
                "am_net": 3000,
                "oi": 30000,
            },
            "lf_net_chg_week": 4,
            "history": [],
        },
        "ratios": {
            "taker": [],
            "global_ls": {"long_pct": 0.60, "short_pct": 0.40},
            "top_ls": {"long_pct": 0.62, "short_pct": 0.38},
        },
        "cross": {
            "coinbase_premium": {"cb": 83154.0, "bn": 83246.0, "premium_bp": -11.0},
            "bybit": {"price": 83250.0, "volume_24h": 100000},
            "bybit_ls": {"long_pct": 0.5938, "short_pct": 0.4062},
            "okx": {},
            "okx_ls": {},
        },
        "options": {
            "dvol": {"dvol": 37.45, "dvol_chg_24h": -1.2, "spark": []},
            "book": {
                "put_oi_btc": 12000,
                "call_oi_btc": 20000,
                "put_call_oi": 0.60,
                "put_call_vol": 0.55,
                "n_puts": 100,
                "n_calls": 120,
            },
        },
        "basis": {
            "symbol": "BTCUSDT_261225",
            "delivery": "2026-12-25",
            "days_to_expiry": 73,
            "mark": 84100.0,
            "index": 83245.0,
            "basis_bp": 102.8,
            "annualized_pct": 5.14,
        },
        "obook": {
            "bid_vol": 250.0,
            "ask_vol": 84.0,
            "imbalance": 2.973,
            "best_bid": 83240.0,
            "best_ask": 83245.0,
            "spread_bp": 0.6,
        },
        "stable": {"usdt_usd": 0.99883, "premium_bp": -11.7},
        "whales": {
            "count_24h": 3,
            "up": 2,
            "down": 1,
            "dir": "accumulation",
            "last3": [],
        },
        "tape": [],
        # bias and players will be computed by the functions under test
        "bias": {"score": 0, "state": "", "color": "neutral", "rule": "", "factors": []},
        "players": {"bull_pts": 0, "bear_pts": 0, "winner": "NOBODY",
                    "color": "neutral", "verdict": "", "players": []},
    }


@pytest.fixture
def minimal_snapshot() -> dict[str, Any]:
    """A sparse snapshot — only price, everything else empty."""
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": {},
        "errors": ["okx_ls: timeout"],
        "price": {
            "date": "2026-10-13",
            "close": 83000.0,
            "open": 82000.0,
            "high": 83500.0,
            "low": 81800.0,
            "ret_pct": 1.2,
            "volume": 20000.0,
            "taker_share": 0.50,
            "taker_share_24h_hourly": [],
            "mark": None,
            "next_funding_ts": None,
            "funding_rate_next": None,
        },
        "funding": {"z": None, "rate": None, "spark": []},
        "oi": {"btc": None, "chg_24h_pct": None, "spark": []},
        "etf": {"latest": None, "flow_5d": None, "last10": [], "published_through": None},
        "cot": {"latest": None, "lf_net_chg_week": None, "history": []},
        "ratios": {"taker": [], "global_ls": {}, "top_ls": {}},
        "cross": {"coinbase_premium": {}, "bybit": {}, "bybit_ls": {}, "okx": {}, "okx_ls": {}},
        "options": {"dvol": {}, "book": {}},
        "basis": {},
        "obook": {},
        "stable": {},
        "whales": {},
        "tape": [],
        "bias": {"score": 0, "state": "", "color": "neutral", "rule": "", "factors": []},
        "players": {"bull_pts": 0, "bear_pts": 0, "winner": "NOBODY",
                    "color": "neutral", "verdict": "", "players": []},
    }
