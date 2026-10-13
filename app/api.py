"""FastAPI application — multi-asset, typed routes, WebSocket, alerts, weights."""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import alerts as alerts_mod
from app import db, live_fetch
from app import weights as weights_mod
from app.assets import ASSETS, DEFAULT_ASSET
from app.config import DATA_JS, settings
from app.models import HealthResponse, HistoryResponse, Snapshot

log = structlog.get_logger(__name__)

# ── per-asset snapshot cache ──────────────────────────────────────────────────
_snap_cache: dict[str, dict[str, Any]] = {}
_snap_at: dict[str, float] = {}
_snap_locks: dict[str, asyncio.Lock] = {}
_subscribers: set[WebSocket] = set()
_prev_snap: dict[str, dict[str, Any]] = {}
_last_alerts: dict[str, list[dict]] = {}


def _lock(asset: str) -> asyncio.Lock:
    if asset not in _snap_locks:
        _snap_locks[asset] = asyncio.Lock()
    return _snap_locks[asset]


def _age(asset: str) -> float:
    return time.time() - _snap_at.get(asset, 0)


async def _get_snapshot(asset: str = DEFAULT_ASSET, force: bool = False) -> dict[str, Any]:
    asset = asset.upper()
    if not force and asset in _snap_cache and _age(asset) < settings.ttl_snapshot:
        return _snap_cache[asset]

    async with _lock(asset):
        if not force and asset in _snap_cache and _age(asset) < settings.ttl_snapshot:
            return _snap_cache[asset]

        if asset in _snap_cache:
            _prev_snap[asset] = _snap_cache[asset]

        snap = await asyncio.to_thread(live_fetch.build_snapshot, asset)
        _snap_cache[asset] = snap
        _snap_at[asset] = time.time()

        with contextlib.suppress(Exception):
            await db.save_snapshot(snap)

        # alerts
        with contextlib.suppress(Exception):
            fired = alerts_mod.evaluate_all(snap, _prev_snap.get(asset))
            _last_alerts[asset] = fired
            if fired:
                await db.save_alerts(fired)
            if fired and settings.discord_webhook_url:
                asyncio.create_task(
                    alerts_mod.send_discord(fired, settings.discord_webhook_url)
                )

        # websocket push
        if settings.enable_websocket and _subscribers:
            msg = json.dumps(snap, default=str)
            dead: set[WebSocket] = set()
            for ws in _subscribers:
                try:
                    await ws.send_text(msg)
                    if _last_alerts.get(asset):
                        await ws.send_text(json.dumps({"_alerts": _last_alerts[asset]}))
                except Exception:
                    dead.add(ws)
            _subscribers.difference_update(dead)

        return snap


@asynccontextmanager
async def lifespan(app: FastAPI):
    for k in list(_snap_locks):
        del _snap_locks[k]
    log.info("starting", port=settings.port, db=str(settings.db_path))
    await db.init_db()
    asyncio.create_task(_get_snapshot(DEFAULT_ASSET, force=True))
    yield
    log.info("shutting down")


app = FastAPI(
    title="BTC Smart-Money API",
    version="0.3.1",
    description="Multi-asset smart-money dashboard — BTC/ETH/SOL, 15 cohorts, alerts.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── health ────────────────────────────────────────────────────────────────────

@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    snap = _snap_cache.get(DEFAULT_ASSET)
    return HealthResponse(
        status="ok" if snap else "degraded",
        snapshot_age_s=round(_age(DEFAULT_ASSET), 1) if snap else None,
        errors=len(snap.get("errors", [])) if snap else 0,
    )


# ── assets ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/assets")
async def list_assets() -> dict[str, Any]:
    """Available assets with metadata."""
    return {
        "default": DEFAULT_ASSET,
        "assets": [
            {
                "key": c.key,
                "name": c.name,
                "accent": c.accent,
                "etf": c.etf_enabled,
                "cot": bool(c.cot_code),
                "options": bool(c.deribit_currency),
            }
            for c in ASSETS.values()
        ],
    }


# ── today (per-asset) ─────────────────────────────────────────────────────────

@app.get("/api/v1/today", response_model=Snapshot)
async def today(
    asset: str = Query(DEFAULT_ASSET, description="BTC | ETH | SOL"),
    force: bool = Query(False),
) -> Snapshot:
    snap = await _get_snapshot(asset, force=force)
    try:
        return Snapshot.model_validate(snap)
    except Exception:
        return JSONResponse(content=snap)  # type: ignore[return-value]


@app.get("/api/v1/bias")
async def bias_only(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    snap = await _get_snapshot(asset)
    result: dict[str, Any] = snap.get("bias", {})
    return result


@app.get("/api/v1/players")
async def players_only(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    snap = await _get_snapshot(asset)
    result: dict[str, Any] = snap.get("players", {})
    return result


# ── weights ───────────────────────────────────────────────────────────────────

@app.get("/api/v1/weights")
async def get_weights() -> dict[str, Any]:
    """Current user weights + available presets."""
    current = weights_mod.load_weights()
    return {
        "preset": current.get("preset", "balanced"),
        "weights": current.get("weights", {}),
        "presets": weights_mod.get_presets(),
        "factor_names": [
            "ETF 5-day flow (institutions)",
            "Taker-buy share (aggressive flow)",
            "CME hedge funds Δ (weekly)",
            "CME lf_net level",
            "Funding z-score (crowding)",
            "Open-interest regime",
            "US institutional (Coinbase premium)",
            "Options positioning (Deribit P/C)",
            "Order-book imbalance (L2)",
            "Stablecoin / dry powder",
        ],
    }


@app.post("/api/v1/weights")
async def set_weights(body: dict[str, Any]) -> dict[str, Any]:
    """Save weights. Body: {"preset": "balanced", "weights": {factor: weight}}."""
    preset = body.get("preset", "balanced")
    weights = body.get("weights", {})
    weights_mod.save_weights(preset, weights)
    return {"ok": True, "preset": preset, "weights": weights}


@app.post("/api/v1/weights/apply")
async def apply_weights_endpoint(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    """Return the bias recomputed with current user weights."""
    snap = await _get_snapshot(asset)
    bias = snap.get("bias", {})
    saved = weights_mod.load_weights()
    weighted = weights_mod.apply_weights(bias, saved.get("weights", {}))
    return weighted


# ── alerts ────────────────────────────────────────────────────────────────────

@app.get("/api/v1/alerts")
async def get_alerts(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    """Last fired alerts for this asset."""
    return {
        "asset": asset.upper(),
        "alerts": _last_alerts.get(asset.upper(), []),
        "rules": [
            {"id": r.id, "type": r.type, "params": r.params,
             "cooldown_min": r.cooldown_min, "enabled": r.enabled}
            for r in alerts_mod.DEFAULT_RULES
        ],
    }


@app.post("/api/v1/alerts/test")
async def test_alert(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    """Fire a test alert (for webhook verification)."""
    test = {
        "rule_id": "test",
        "rule_type": "manual",
        "message": f"Test alert from {asset.upper()} dashboard",
        "data": {},
        "severity": "info",
        "ts": "2026-01-01T00:00:00Z",
        "asset": asset.upper(),
    }
    webhook = settings.discord_webhook_url
    sent = False
    if webhook:
        sent = await alerts_mod.send_discord([test], webhook)
    return {"ok": True, "discord_sent": sent, "payload": test}


# ── history / cache / refresh ─────────────────────────────────────────────────

@app.get("/api/v1/history", response_model=HistoryResponse)
async def history(days: int = Query(90, ge=1, le=730)) -> HistoryResponse:
    rows = await db.snapshot_history(days)
    mapped = [
        {
            "date": r.get("d", ""),
            "close": r.get("close") or 0,
            "ret_pct": r.get("ret_pct"),
            "taker": r.get("taker"),
            "etf": None,
            "volume": 0,
            "bias_score": r.get("bias_score"),
            "winner": r.get("winner"),
        }
        for r in rows
    ]
    return HistoryResponse(days=days, rows=mapped)  # type: ignore[arg-type]


@app.get("/api/v1/history/dates")
async def history_dates(asset: str = DEFAULT_ASSET, limit: int = 90) -> dict[str, Any]:
    """Available dates for historical playback."""
    dates = await db.get_available_dates(asset, limit)
    return {"asset": asset.upper(), "dates": dates}


@app.get("/api/v1/history/{date_str}")
async def history_snapshot(
    date_str: str,
    asset: str = Query(DEFAULT_ASSET, description="BTC | ETH | SOL"),
) -> Any:
    """Full snapshot for a given date (historical playback)."""
    snap = await db.get_snapshot_by_date(date_str, asset)
    if snap is None:
        raise HTTPException(status_code=404, detail=f"No snapshot for {date_str} ({asset})")
    return JSONResponse(content=snap)


# ── alerts (from SQLite) ──────────────────────────────────────────────────────

@app.get("/api/v1/alerts/history")
async def alerts_history(
    asset: str = DEFAULT_ASSET,
    limit: int = Query(50, ge=1, le=500),
) -> dict[str, Any]:
    """Persisted alert history from SQLite."""
    rows = await db.get_alerts(asset, limit)
    return {"asset": asset.upper(), "count": len(rows), "alerts": rows}


@app.post("/api/v1/refresh")
async def refresh(asset: str = DEFAULT_ASSET) -> dict[str, Any]:
    snap = await _get_snapshot(asset, force=True)
    return {
        "ok": True,
        "asset": asset.upper(),
        "generated_at": snap.get("generated_at"),
        "errors": snap.get("errors", []),
        "bias": snap.get("bias", {}).get("state"),
        "winner": snap.get("players", {}).get("winner"),
        "alerts": len(_last_alerts.get(asset.upper(), [])),
    }


@app.get("/api/v1/cache")
async def cache_info() -> dict[str, Any]:
    from app.config import CACHE_DIR

    cache_files = []
    total = 0
    if CACHE_DIR.is_dir():
        for f in sorted(CACHE_DIR.iterdir()):
            if f.suffix == ".json":
                sz = f.stat().st_size
                total += sz
                cache_files.append({"name": f.name, "bytes": sz})
    count = await db.snapshot_count()
    return {
        "disk_bytes": total,
        "disk_max": settings.cache_max_bytes,
        "files": cache_files,
        "db_snapshots": count,
        "db_path": str(settings.db_path),
        "assets_cached": list(_snap_cache.keys()),
    }


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/today")
async def ws_today(ws: WebSocket) -> None:
    await ws.accept()
    _subscribers.add(ws)
    try:
        snap = await _get_snapshot(DEFAULT_ASSET)
        await ws.send_text(json.dumps(snap, default=str))
        while True:
            await asyncio.sleep(30)
            await ws.send_text(json.dumps({"_ping": time.time()}))
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _subscribers.discard(ws)


# ── static ────────────────────────────────────────────────────────────────────

@app.get("/")
async def index() -> FileResponse:
    return FileResponse(DATA_JS.parent / "index.html")


@app.get("/data.js")
async def data_js() -> FileResponse:
    return FileResponse(DATA_JS, media_type="application/javascript")


# ── legacy routes ─────────────────────────────────────────────────────────────

@app.get("/api/today")
async def legacy_today(asset: str = DEFAULT_ASSET, force: bool = False) -> Any:
    snap = await _get_snapshot(asset, force=force)
    return JSONResponse(content=snap)


@app.get("/api/history")
async def legacy_history(days: int = 90) -> Any:
    rows = await db.snapshot_history(days)
    return JSONResponse(content={"days": days, "rows": rows})


@app.post("/api/refresh")
async def legacy_refresh() -> Any:
    snap = await _get_snapshot(DEFAULT_ASSET, force=True)
    return JSONResponse(content={"ok": True, "generated_at": snap.get("generated_at")})


@app.get("/api/cache")
async def legacy_cache() -> Any:
    info = await cache_info()
    return JSONResponse(content=info)
