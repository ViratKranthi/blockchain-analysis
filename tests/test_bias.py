"""Tests for compute_bias — 10 factors, score range, state thresholds."""
from __future__ import annotations

from app.live_fetch import compute_bias


class TestComputeBias:
    def test_full_snapshot_has_10_factors(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        assert len(bias["factors"]) == 10

    def test_score_is_integer(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        assert isinstance(bias["score"], int)

    def test_state_matches_score(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        score = bias["score"]
        state = bias["state"]
        if score >= 6:
            assert state == "STRONG BULL"
        elif score >= 2:
            assert state == "MILD BULL"
        elif score <= -6:
            assert state == "STRONG BEAR"
        elif score <= -2:
            assert state == "MILD BEAR"
        else:
            assert state == "NEUTRAL / CHOP"

    def test_minimal_snapshot_is_neutral(self, minimal_snapshot):
        bias = compute_bias(minimal_snapshot)
        # all factors unavailable → score 0 → neutral
        assert bias["score"] == 0
        assert bias["state"] == "NEUTRAL / CHOP"
        assert bias["color"] == "neutral"

    def test_every_factor_has_required_keys(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        for f in bias["factors"]:
            assert "name" in f
            assert "pts" in f
            assert "reason" in f
            assert "value" in f
            assert "unit" in f

    def test_factors_have_nonempty_reasons(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        for f in bias["factors"]:
            assert f["reason"], f"empty reason for {f['name']}"

    def test_oi_is_informational(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        oi = next(f for f in bias["factors"] if "Open-interest" in f["name"])
        assert oi["info"] is True
        assert oi["pts"] == 0

    def test_coinbase_premium_negative_deduction(self, full_snapshot):
        # full_snapshot has premium_bp = -11 → should deduct 1
        bias = compute_bias(full_snapshot)
        cb = next(f for f in bias["factors"] if "Coinbase" in f["name"])
        assert cb["pts"] == -1

    def test_stablecoin_negative_deduction(self, full_snapshot):
        # full_snapshot has USDT premium -11.7bp → should deduct 1
        bias = compute_bias(full_snapshot)
        st = next(f for f in bias["factors"] if "Stablecoin" in f["name"])
        assert st["pts"] == -1

    def test_options_call_heavy_bonus(self, full_snapshot):
        # full_snapshot P/C = 0.60 → ≤ 0.7 → +1
        bias = compute_bias(full_snapshot)
        op = next(f for f in bias["factors"] if "Options" in f["name"])
        assert op["pts"] == 1

    def test_orderbook_bid_heavy_bonus(self, full_snapshot):
        # full_snapshot imbalance = 2.973 → ≥ 1.15 → +1
        bias = compute_bias(full_snapshot)
        ob = next(f for f in bias["factors"] if "Order-book" in f["name"])
        assert ob["pts"] == 1

    def test_has_rule(self, full_snapshot):
        bias = compute_bias(full_snapshot)
        assert bias["rule"], "bias must include an actionable rule"
