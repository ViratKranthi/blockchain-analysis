"""Multi-asset configuration — BTC, ETH, SOL with the same 15-cohort framework.

Each asset has its own Binance symbols, ETF tickers (where applicable), and COT codes.
The cohort logic is identical; only the symbols change.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AssetConfig:
    """Everything needed to build a snapshot for one asset."""

    key: str                       # "BTC", "ETH", "SOL"
    name: str                      # "Bitcoin", "Ethereum", "Solana"
    binance_spot: str              # "BTCUSDT"
    binance_perp: str              # "BTCUSDT" (futures)
    binance_quarterly_prefix: str  # "BTCUSDT_" for basis
    bybit_symbol: str              # "BTCUSDT"
    okx_inst: str                  # "BTC-USDT"
    okx_ccy: str                   # "BTC"
    deribit_currency: str          # "BTC" (options/DVOL); "" if none
    coinbase_product: str          # "BTC-USD"
    stablecoin_product: str = "USDT-USD"
    # ETF (BTC only for now — ETH ETFs exist but flows are separate)
    etf_enabled: bool = False
    # COT (only BTC has CME futures contract)
    cot_code: str | None = None
    # display
    display_decimals: int = 0
    coingecko_id: str = ""
    # color accent for UI
    accent: str = "#c9a54c"


ASSETS: dict[str, AssetConfig] = {
    "BTC": AssetConfig(
        key="BTC", name="Bitcoin",
        binance_spot="BTCUSDT", binance_perp="BTCUSDT",
        binance_quarterly_prefix="BTCUSDT_",
        bybit_symbol="BTCUSDT", okx_inst="BTC-USDT", okx_ccy="BTC",
        deribit_currency="BTC", coinbase_product="BTC-USD",
        stablecoin_product="USDT-USD",
        etf_enabled=True, cot_code="133741",
        display_decimals=0, coingecko_id="bitcoin",
        accent="#c9a54c",
    ),
    "ETH": AssetConfig(
        key="ETH", name="Ethereum",
        binance_spot="ETHUSDT", binance_perp="ETHUSDT",
        binance_quarterly_prefix="ETHUSDT_",
        bybit_symbol="ETHUSDT", okx_inst="ETH-USDT", okx_ccy="ETH",
        deribit_currency="ETH", coinbase_product="ETH-USD",
        stablecoin_product="USDT-USD",
        etf_enabled=True, cot_code=None,   # no CME ETH COT in our set
        display_decimals=1, coingecko_id="ethereum",
        accent="#627eea",
    ),
    "SOL": AssetConfig(
        key="SOL", name="Solana",
        binance_spot="SOLUSDT", binance_perp="SOLUSDT",
        binance_quarterly_prefix="SOLUSDT_",
        bybit_symbol="SOLUSDT", okx_inst="SOL-USDT", okx_ccy="SOL",
        deribit_currency="", coinbase_product="SOL-USD",
        stablecoin_product="USDT-USD",
        etf_enabled=False, cot_code=None,
        display_decimals=2, coingecko_id="solana",
        accent="#9945ff",
    ),
}

DEFAULT_ASSET = "BTC"


def get_asset(key: str) -> AssetConfig:
    """Look up asset config; falls back to BTC."""
    return ASSETS.get(key.upper(), ASSETS[DEFAULT_ASSET])


def asset_keys() -> list[str]:
    return list(ASSETS.keys())
