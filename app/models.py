"""Typed API models — every endpoint returns these shapes."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# ── primitives ────────────────────────────────────────────────────────────────

class SourceMeta(BaseModel):
    mode: Literal["cache", "live"] = "cache"
    at: datetime | None = None


class PriceInfo(BaseModel):
    date: str
    close: float
    open: float = 0
    high: float = 0
    low: float = 0
    ret_pct: float | None = None
    volume: float = 0
    taker_share: float | None = None
    taker_share_24h_hourly: list[dict[str, Any]] = Field(default_factory=list)
    mark: float | None = None
    next_funding_ts: int | None = None
    funding_rate_next: float | None = None


class FundingInfo(BaseModel):
    z: float | None = None
    rate: float | None = None
    spark: list[dict[str, Any]] = Field(default_factory=list)


class OIInfo(BaseModel):
    btc: float | None = None
    chg_24h_pct: float | None = None
    spark: list[dict[str, Any]] = Field(default_factory=list)


class EtfInfo(BaseModel):
    latest: dict[str, Any] | None = None
    flow_5d: float | None = None
    last10: list[dict[str, Any]] = Field(default_factory=list)
    published_through: str | None = None


class CotLatest(BaseModel):
    date: str = ""
    lf_long: int = 0
    lf_short: int = 0
    lf_net: int = 0
    am_long: int = 0
    am_short: int = 0
    am_net: int = 0
    oi: int = 0


class CotInfo(BaseModel):
    latest: CotLatest | None = None
    lf_net_chg_week: int | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


class Ratios(BaseModel):
    taker: list[dict[str, Any]] = Field(default_factory=list)
    global_ls: dict[str, Any] = Field(default_factory=dict)
    top_ls: dict[str, Any] = Field(default_factory=dict)


class CrossExchange(BaseModel):
    coinbase_premium: dict[str, Any] = Field(default_factory=dict)
    bybit: dict[str, Any] = Field(default_factory=dict)
    bybit_ls: dict[str, Any] = Field(default_factory=dict)
    okx: dict[str, Any] = Field(default_factory=dict)
    okx_ls: dict[str, Any] = Field(default_factory=dict)


class OptionsInfo(BaseModel):
    dvol: dict[str, Any] = Field(default_factory=dict)
    book: dict[str, Any] = Field(default_factory=dict)


class BiasFactor(BaseModel):
    name: str
    pts: int = 0
    reason: str = ""
    value: float | None = None
    unit: str = ""
    info: bool = False


class Bias(BaseModel):
    score: int
    state: str
    color: Literal["bull", "bear", "neutral"] = "neutral"
    rule: str = ""
    factors: list[BiasFactor] = Field(default_factory=list)


class Player(BaseModel):
    cohort: str
    side: str
    note: str = ""
    lag: str = ""
    weight: int = 1


class Players(BaseModel):
    bull_pts: int = 0
    bear_pts: int = 0
    winner: Literal["BUYERS", "SELLERS", "NOBODY"] = "NOBODY"
    color: Literal["bull", "bear", "neutral"] = "neutral"
    verdict: str = ""
    players: list[Player] = Field(default_factory=list)


class TapeDay(BaseModel):
    date: str
    close: float
    ret_pct: float | None = None
    taker: float | None = None
    etf: float | None = None
    volume: float = 0


class Snapshot(BaseModel):
    """Full /api/today response."""

    generated_at: datetime
    sources: dict[str, SourceMeta] = Field(default_factory=dict)
    errors: list[str] = Field(default_factory=list)
    price: PriceInfo
    funding: FundingInfo = Field(default_factory=FundingInfo)
    oi: OIInfo = Field(default_factory=OIInfo)
    etf: EtfInfo = Field(default_factory=EtfInfo)
    cot: CotInfo = Field(default_factory=CotInfo)
    ratios: Ratios = Field(default_factory=Ratios)
    cross: CrossExchange = Field(default_factory=CrossExchange)
    options: OptionsInfo = Field(default_factory=OptionsInfo)
    basis: dict[str, Any] = Field(default_factory=dict)
    obook: dict[str, Any] = Field(default_factory=dict)
    stable: dict[str, Any] = Field(default_factory=dict)
    whales: dict[str, Any] = Field(default_factory=dict)
    tape: list[TapeDay] = Field(default_factory=list)
    bias: Bias
    players: Players


# ── lightweight response wrappers ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    version: str = "0.3.1"
    snapshot_age_s: float | None = None
    errors: int = 0


class HistoryRow(BaseModel):
    date: str
    close: float
    ret_pct: float | None = None
    taker: float | None = None
    etf: float | None = None
    volume: float = 0
    bias_score: int | None = None
    winner: str | None = None


class HistoryResponse(BaseModel):
    days: int
    rows: list[HistoryRow]
