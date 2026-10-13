"""Alert engine — rule evaluation, Discord webhook, browser notification payload.

Rules are JSON-defined and evaluated after each snapshot build.
When a rule fires, we:
  1. Record it in SQLite (`alerts` table)
  2. POST to a Discord webhook (if configured)
  3. Include it in the /api/v1/today response for the frontend to show

No paid services. Discord webhooks are free.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# ── rule types ────────────────────────────────────────────────────────────────
# Each rule: {"id", "type", "params", "cooldown_min", "enabled"}
# Types:
#   bias_flip          — bias state changed
#   bias_threshold     — score crossed ±N
#   etf_flow           — ETF 5d flow beyond ±$N million
#   funding_extreme    — funding z beyond ±N
#   taker_extreme      — taker share beyond threshold
#   player_control     — winner changed
#   whale_print        — N large candles in window
#   price_move         — price moved ±N% in a day


@dataclass
class AlertRule:
    id: str
    type: str
    params: dict[str, Any] = field(default_factory=dict)
    cooldown_min: int = 60
    enabled: bool = True


DEFAULT_RULES: list[AlertRule] = [
    AlertRule(id="bias_flip", type="bias_flip", cooldown_min=120),
    AlertRule(id="bias_strong", type="bias_threshold", params={"abs_score": 6}, cooldown_min=240),
    AlertRule(id="etf_big", type="etf_flow", params={"abs_flow_musd": 500}, cooldown_min=360),
    AlertRule(id="funding_squeeze", type="funding_extreme", params={"abs_z": 2.5}, cooldown_min=180),
    AlertRule(id="taker_extreme", type="taker_extreme", params={"min": 0.58, "max": 0.42}, cooldown_min=120),
    AlertRule(id="whale_burst", type="whale_print", params={"min_count": 5}, cooldown_min=90),
    AlertRule(id="price_move", type="price_move", params={"abs_pct": 5.0}, cooldown_min=60),
]


# ── evaluation ────────────────────────────────────────────────────────────────

def _get_path(snap: dict, path: str, default=None):
    """Dot-path lookup: 'bias.score', 'etf.flow_5d', 'price.ret_pct'."""
    cur: Any = snap
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part, default)
    return cur


def evaluate_rule(rule: AlertRule, snap: dict, prev: dict | None) -> dict | None:
    """Return an alert dict if the rule fires, else None."""
    if not rule.enabled:
        return None

    t = rule.type
    p = rule.params

    if t == "bias_flip":
        if prev is None:
            return None
        old = _get_path(prev, "bias.state")
        new = _get_path(snap, "bias.state")
        if old and new and old != new:
            return _alert(rule, f"Bias flipped: {old} → {new}",
                          {"from": old, "to": new}, "info")

    elif t == "bias_threshold":
        score = _get_path(snap, "bias.score", 0) or 0
        threshold = p.get("abs_score", 6)
        prev_score = _get_path(prev, "bias.score") if prev else None
        if abs(score) >= threshold and (prev_score is None or abs(prev_score) < threshold):
            state = _get_path(snap, "bias.state", "?")
            return _alert(rule, f"Bias score {score:+d} → {state}",
                          {"score": score, "state": state},
                          "bull" if score > 0 else "bear")

    elif t == "etf_flow":
        flow = _get_path(snap, "etf.flow_5d")
        if flow is not None:
            threshold = p.get("abs_flow_musd", 500)
            prev_flow = _get_path(prev, "etf.flow_5d") if prev else None
            if abs(flow) >= threshold and (prev_flow is None or abs(prev_flow) < threshold):
                side = "bullish inflow" if flow > 0 else "bearish outflow"
                return _alert(rule, f"ETF 5d flow ${flow:+,.0f}m — {side}",
                              {"flow_musd": flow}, "bull" if flow > 0 else "bear")

    elif t == "funding_extreme":
        z = _get_path(snap, "funding.z")
        if z is not None:
            threshold = p.get("abs_z", 2.5)
            if abs(z) >= threshold:
                prev_z = _get_path(prev, "funding.z") if prev else None
                if prev_z is None or abs(prev_z) < threshold:
                    note = "crowded shorts (squeeze fuel)" if z < 0 else "crowded longs (pullback fuel)"
                    return _alert(rule, f"Funding z={z:.1f} — {note}",
                                  {"z": z}, "bull" if z < 0 else "bear")

    elif t == "taker_extreme":
        ts = _get_path(snap, "price.taker_share")
        if ts is not None:
            hi = p.get("min", 0.58)
            lo = p.get("max", 0.42)
            prev_ts = _get_path(prev, "price.taker_share") if prev else None
            if ts >= hi and (prev_ts is None or prev_ts < hi):
                return _alert(rule, f"Taker-buy {ts*100:.1f}% — extreme buyers",
                              {"taker_share": ts}, "bull")
            if ts <= lo and (prev_ts is None or prev_ts > lo):
                return _alert(rule, f"Taker-buy {ts*100:.1f}% — extreme sellers",
                              {"taker_share": ts}, "bear")

    elif t == "whale_print":
        count = _get_path(snap, "whales.count_24h", 0) or 0
        if count >= p.get("min_count", 5):
            direction = _get_path(snap, "whales.dir", "mixed")
            prev_count = _get_path(prev, "whales.count_24h") if prev else None
            if prev_count is None or count > prev_count:
                return _alert(rule, f"Whale burst: {count} large candles ({direction})",
                              {"count": count, "dir": direction}, "info")

    elif t == "price_move":
        ret = _get_path(snap, "price.ret_pct", 0) or 0
        threshold = p.get("abs_pct", 5.0)
        if abs(ret) >= threshold:
            prev_ret = _get_path(prev, "price.ret_pct") if prev else None
            if prev_ret is None or abs(prev_ret) < threshold:
                return _alert(rule, f"Price {ret:+.1f}% today",
                              {"ret_pct": ret}, "bull" if ret > 0 else "bear")

    return None


def _alert(rule: AlertRule, message: str, data: dict, severity: str) -> dict:
    return {
        "rule_id": rule.id,
        "rule_type": rule.type,
        "message": message,
        "data": data,
        "severity": severity,   # "bull" | "bear" | "info"
        "ts": datetime.now(UTC).isoformat(),
        "asset": None,          # filled by caller
    }


# ── cooldown store ────────────────────────────────────────────────────────────
_last_fired: dict[str, float] = {}   # rule_id → epoch ts


def evaluate_all(snap: dict, prev: dict | None,
                 rules: list[AlertRule] | None = None) -> list[dict]:
    """Evaluate all rules, respect cooldowns, return fired alerts."""
    if rules is None:
        rules = DEFAULT_RULES
    now = time.time()
    fired = []
    asset = snap.get("asset", "BTC")
    for rule in rules:
        # cooldown check
        last = _last_fired.get(f"{asset}:{rule.id}", 0)
        if now - last < rule.cooldown_min * 60:
            continue
        result = evaluate_rule(rule, snap, prev)
        if result:
            result["asset"] = asset
            _last_fired[f"{asset}:{rule.id}"] = now
            fired.append(result)
            log.info("alert_fired", rule=rule.id, message=result["message"], asset=asset)
    return fired


# ── Discord webhook ───────────────────────────────────────────────────────────

async def send_discord(alerts: list[dict], webhook_url: str) -> bool:
    """POST alerts to a Discord webhook. Returns True on success."""
    if not alerts or not webhook_url:
        return False
    import httpx

    color_map = {"bull": 0x22c55e, "bear": 0xef4444, "info": 0xc9a54c}
    embeds = []
    for a in alerts[:5]:  # Discord max 10 embeds, keep 5
        embeds.append({
            "title": f"{'🟢' if a['severity']=='bull' else '🔴' if a['severity']=='bear' else '🟡'} {a['asset']} Alert",
            "description": a["message"],
            "color": color_map.get(a["severity"], 0xc9a54c),
            "timestamp": a["ts"],
            "footer": {"text": f"rule: {a['rule_id']}"},
        })
    payload = {"username": "Smart-Money Alerts", "embeds": embeds}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(webhook_url, json=payload)
            return r.status_code in (200, 204)
    except Exception as e:
        log.warning("discord_webhook_failed", error=str(e))
        return False


def browser_notification_payload(alerts: list[dict]) -> list[dict]:
    """Format alerts for the Notification API on the frontend."""
    return [
        {
            "title": f"{a['asset']} — {a['severity'].upper()}",
            "body": a["message"],
            "tag": f"{a['asset']}:{a['rule_id']}",
        }
        for a in alerts
    ]
