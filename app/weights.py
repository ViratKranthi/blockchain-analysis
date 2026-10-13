"""Custom bias weights — user-tunable factor weights + presets.

The default compute_bias() gives every factor equal weight.
This module lets users re-weight factors and persist their preferences.
"""
from __future__ import annotations

import json
from typing import Any

from app.config import CACHE_DIR

# factor name → default weight (1.0 = normal)
PRESETS: dict[str, dict[str, float]] = {
    "balanced": {},  # all 1.0 (default)
    "conservative": {
        "ETF 5-day flow (institutions)": 2.0,
        "CME hedge funds Δ (weekly)": 1.5,
        "CME lf_net level": 1.5,
        "Taker-buy share (aggressive flow)": 0.5,
        "Funding z-score (crowding)": 0.5,
        "Open-interest regime": 0.0,
        "US institutional (Coinbase premium)": 1.5,
        "Options positioning (Deribit P/C)": 1.0,
        "Order-book imbalance (L2)": 0.3,
        "Stablecoin / dry powder": 1.0,
    },
    "aggressive": {
        "ETF 5-day flow (institutions)": 0.5,
        "Taker-buy share (aggressive flow)": 2.0,
        "Funding z-score (crowding)": 2.0,
        "Open-interest regime": 1.0,
        "US institutional (Coinbase premium)": 0.5,
        "Options positioning (Deribit P/C)": 0.5,
        "Order-book imbalance (L2)": 1.5,
        "Stablecoin / dry powder": 0.5,
    },
    "institutional": {
        "ETF 5-day flow (institutions)": 3.0,
        "CME hedge funds Δ (weekly)": 2.0,
        "CME lf_net level": 2.0,
        "US institutional (Coinbase premium)": 2.0,
        "Stablecoin / dry powder": 1.5,
        "Taker-buy share (aggressive flow)": 0.3,
        "Funding z-score (crowding)": 0.3,
    },
}

_WEIGHTS_FILE = CACHE_DIR / "bias_weights.json"


def load_weights() -> dict[str, Any]:
    """Load user weights from disk. Returns {preset, weights}."""
    if _WEIGHTS_FILE.exists():
        try:
            with open(_WEIGHTS_FILE) as f:
                result: dict[str, Any] = json.load(f)
                return result
        except Exception:
            pass
    return {"preset": "balanced", "weights": {}}


def save_weights(preset: str, weights: dict[str, float]) -> None:
    """Persist user weights."""
    with open(_WEIGHTS_FILE, "w") as f:
        json.dump({"preset": preset, "weights": weights}, f, indent=1)


def apply_weights(bias: dict, weights: dict[str, float]) -> dict:
    """Re-weight the bias factors and recompute score/state.

    Takes a bias dict (from compute_bias) and returns a new one with
    weighted factors and an adjusted score/state.
    """
    if not weights:
        return bias

    factors = []
    score = 0.0
    for f in bias.get("factors", []):
        w = weights.get(f["name"], 1.0)
        weighted_pts = f["pts"] * w
        score += weighted_pts
        nf = dict(f)
        nf["weight"] = w
        nf["weighted_pts"] = weighted_pts
        factors.append(nf)

    score_int = int(round(score))
    if score_int >= 6:
        state, color = "STRONG BULL", "bull"
    elif score_int >= 2:
        state, color = "MILD BULL", "bull"
    elif score_int <= -6:
        state, color = "STRONG BEAR", "bear"
    elif score_int <= -2:
        state, color = "MILD BEAR", "bear"
    else:
        state, color = "NEUTRAL / CHOP", "neutral"

    out = dict(bias)
    out["score"] = score_int
    out["state"] = state
    out["color"] = color
    out["factors"] = factors
    out["weighted"] = True
    return out


def get_presets() -> dict[str, dict[str, float]]:
    return PRESETS
