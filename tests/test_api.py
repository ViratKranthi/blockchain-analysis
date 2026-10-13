"""Tests for the FastAPI app — health, today, bias, players, cache."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


class TestHealth:
    def test_healthz_returns_ok(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("ok", "degraded")
        assert data["version"] == "0.2.0"


class TestToday:
    def test_today_returns_snapshot(self, client):
        r = client.get("/api/v1/today")
        assert r.status_code == 200
        data = r.json()
        assert "price" in data
        assert "bias" in data
        assert "players" in data

    def test_today_has_price(self, client):
        r = client.get("/api/v1/today")
        price = r.json()["price"]
        assert "close" in price
        assert "date" in price

    def test_today_players_is_list(self, client):
        r = client.get("/api/v1/today")
        players = r.json()["players"]["players"]
        assert isinstance(players, list)
        assert len(players) >= 7  # at least the original 7

    def test_today_bias_has_factors(self, client):
        r = client.get("/api/v1/today")
        factors = r.json()["bias"]["factors"]
        assert isinstance(factors, list)
        assert len(factors) >= 6

    def test_legacy_today_still_works(self, client):
        r = client.get("/api/today")
        assert r.status_code == 200
        assert "price" in r.json()


class TestBias:
    def test_bias_only_endpoint(self, client):
        r = client.get("/api/v1/bias")
        assert r.status_code == 200
        data = r.json()
        assert "score" in data
        assert "state" in data
        assert "factors" in data


class TestPlayers:
    def test_players_only_endpoint(self, client):
        r = client.get("/api/v1/players")
        assert r.status_code == 200
        data = r.json()
        assert "winner" in data
        assert "players" in data
        assert "verdict" in data


class TestRefresh:
    def test_refresh_returns_ok(self, client):
        r = client.post("/api/v1/refresh")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "generated_at" in data


class TestCache:
    def test_cache_info_structure(self, client):
        r = client.get("/api/v1/cache")
        assert r.status_code == 200
        data = r.json()
        assert "disk_bytes" in data
        assert "files" in data
        assert "db_snapshots" in data


class TestHistory:
    def test_history_returns_rows(self, client):
        r = client.get("/api/v1/history?days=7")
        assert r.status_code == 200
        data = r.json()
        assert "days" in data
        assert "rows" in data

    def test_history_rejects_bad_days(self, client):
        r = client.get("/api/v1/history?days=0")
        assert r.status_code == 422  # pydantic validation error


class TestIndex:
    def test_index_serves_html(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    def test_data_js_serves_js(self, client):
        r = client.get("/data.js")
        assert r.status_code == 200
        assert "javascript" in r.headers["content-type"]
