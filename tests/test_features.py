"""Tests for alerts engine, weights, and multi-asset support."""
from __future__ import annotations

from app.alerts import (
    DEFAULT_RULES,
    AlertRule,
    browser_notification_payload,
    evaluate_all,
    evaluate_rule,
)
from app.assets import ASSETS, asset_keys, get_asset
from app.weights import PRESETS, apply_weights

# ── assets ────────────────────────────────────────────────────────────────────

class TestAssets:
    def test_three_assets(self):
        assert len(ASSETS) == 3
        assert set(asset_keys()) == {"BTC", "ETH", "SOL"}

    def test_btc_defaults(self):
        cfg = get_asset("BTC")
        assert cfg.binance_spot == "BTCUSDT"
        assert cfg.etf_enabled is True
        assert cfg.cot_code == "133741"

    def test_eth_config(self):
        cfg = get_asset("ETH")
        assert cfg.binance_spot == "ETHUSDT"
        assert cfg.deribit_currency == "ETH"
        assert cfg.accent == "#627eea"

    def test_sol_no_options(self):
        cfg = get_asset("SOL")
        assert cfg.deribit_currency == ""
        assert cfg.etf_enabled is False

    def test_fallback_to_btc(self):
        cfg = get_asset("DOGE")
        assert cfg.key == "BTC"


# ── alerts ────────────────────────────────────────────────────────────────────

class TestAlertRules:
    def test_default_rules_exist(self):
        assert len(DEFAULT_RULES) >= 7
        types = {r.type for r in DEFAULT_RULES}
        assert "bias_flip" in types
        assert "bias_threshold" in types
        assert "etf_flow" in types

    def test_bias_flip_fires(self, full_snapshot, minimal_snapshot):
        rule = AlertRule(id="t", type="bias_flip")
        prev = dict(minimal_snapshot)
        prev["bias"] = {"state": "NEUTRAL / CHOP"}
        snap = dict(full_snapshot)
        snap["bias"] = {"state": "MILD BEAR", "score": -3}
        result = evaluate_rule(rule, snap, prev)
        assert result is not None
        assert "MILD BEAR" in result["message"]

    def test_bias_flip_no_change(self, full_snapshot):
        rule = AlertRule(id="t", type="bias_flip")
        snap = dict(full_snapshot)
        snap["bias"] = {"state": "MILD BULL", "score": 2}
        prev = dict(full_snapshot)
        prev["bias"] = {"state": "MILD BULL", "score": 2}
        assert evaluate_rule(rule, snap, prev) is None

    def test_bias_threshold_fires(self, full_snapshot):
        rule = AlertRule(id="t", type="bias_threshold", params={"abs_score": 2})
        snap = dict(full_snapshot)
        snap["bias"] = {"state": "STRONG BEAR", "score": -7}
        result = evaluate_rule(rule, snap, None)
        assert result is not None
        assert result["severity"] == "bear"

    def test_etf_flow_alert(self, full_snapshot):
        rule = AlertRule(id="t", type="etf_flow", params={"abs_flow_musd": 500})
        snap = dict(full_snapshot)
        snap["etf"] = {"flow_5d": -773.0}
        result = evaluate_rule(rule, snap, None)
        assert result is not None
        assert result["severity"] == "bear"

    def test_funding_squeeze(self, full_snapshot):
        rule = AlertRule(id="t", type="funding_extreme", params={"abs_z": 2.5})
        snap = dict(full_snapshot)
        snap["funding"] = {"z": -3.0}
        result = evaluate_rule(rule, snap, None)
        assert result is not None
        assert result["severity"] == "bull"  # short squeeze = bullish

    def test_taker_extreme(self, full_snapshot):
        rule = AlertRule(id="t", type="taker_extreme", params={"min": 0.58, "max": 0.42})
        snap = dict(full_snapshot)
        snap["price"] = dict(full_snapshot["price"])
        snap["price"]["taker_share"] = 0.60
        result = evaluate_rule(rule, snap, None)
        assert result is not None
        assert result["severity"] == "bull"

    def test_price_move(self, full_snapshot):
        rule = AlertRule(id="t", type="price_move", params={"abs_pct": 5.0})
        snap = dict(full_snapshot)
        snap["price"] = dict(full_snapshot["price"])
        snap["price"]["ret_pct"] = -6.2
        result = evaluate_rule(rule, snap, None)
        assert result is not None
        assert result["severity"] == "bear"

    def test_disabled_rule(self, full_snapshot):
        rule = AlertRule(id="t", type="bias_threshold", enabled=False)
        snap = dict(full_snapshot)
        snap["bias"] = {"state": "STRONG BEAR", "score": -7}
        assert evaluate_rule(rule, snap, None) is None

    def test_evaluate_all_returns_list(self, full_snapshot):
        result = evaluate_all(full_snapshot, None)
        assert isinstance(result, list)

    def test_browser_notification_payload(self):
        alerts = [
            {"asset": "BTC", "severity": "bull", "message": "test",
             "rule_id": "x", "rule_type": "manual", "data": {}, "ts": ""},
        ]
        payload = browser_notification_payload(alerts)
        assert len(payload) == 1
        assert "title" in payload[0]
        assert "body" in payload[0]


# ── weights ───────────────────────────────────────────────────────────────────

class TestWeights:
    def test_presets_exist(self):
        assert "balanced" in PRESETS
        assert "conservative" in PRESETS
        assert "aggressive" in PRESETS
        assert "institutional" in PRESETS

    def test_apply_empty_weights_is_noop(self, full_snapshot):
        bias = {"score": 3, "state": "MILD BULL", "color": "bull", "factors": [
            {"name": "f1", "pts": 1}, {"name": "f2", "pts": 2}
        ]}
        result = apply_weights(bias, {})
        assert result["score"] == 3

    def test_apply_doubles_weight(self):
        bias = {"score": 1, "state": "NEUTRAL", "color": "neutral", "factors": [
            {"name": "ETF 5-day flow (institutions)", "pts": 2},
            {"name": "Taker-buy share (aggressive flow)", "pts": 0},
        ]}
        weights = {"ETF 5-day flow (institutions)": 2.0}
        result = apply_weights(bias, weights)
        # 2*2 + 0*1 = 4 → MILD BULL
        assert result["score"] == 4
        assert result["state"] == "MILD BULL"
        assert result["weighted"] is True

    def test_save_and_load(self, tmp_path, monkeypatch):
        import app.weights as w
        test_file = tmp_path / "weights.json"
        monkeypatch.setattr(w, "_WEIGHTS_FILE", test_file)
        w.save_weights("aggressive", {"f1": 2.0})
        loaded = w.load_weights()
        assert loaded["preset"] == "aggressive"
        assert loaded["weights"]["f1"] == 2.0
