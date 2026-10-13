"""Tests for who_is_winning — 15 cohorts, verdict logic, price confirmation."""
from __future__ import annotations

from app.live_fetch import who_is_winning


class TestWhoIsWinning:
    def test_full_snapshot_has_15_players(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        assert len(result["players"]) == 15

    def test_minimal_has_few_players(self, minimal_snapshot):
        result = who_is_winning(minimal_snapshot)
        # only takers available (taker_share = 0.50 → neutral)
        assert len(result["players"]) <= 2

    def test_winner_is_valid(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        assert result["winner"] in ("BUYERS", "SELLERS", "NOBODY")

    def test_color_matches_winner(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        if result["winner"] == "BUYERS":
            assert result["color"] == "bull"
        elif result["winner"] == "SELLERS":
            assert result["color"] == "bear"
        else:
            assert result["color"] == "neutral"

    def test_bull_bear_counts_non_negative(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        assert result["bull_pts"] >= 0
        assert result["bear_pts"] >= 0

    def test_verdict_mentions_score(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        b, s = result["bull_pts"], result["bear_pts"]
        if b != s:
            assert f"{max(b,s)}–{min(b,s)}" in result["verdict"]

    def test_every_player_has_required_keys(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        for p in result["players"]:
            assert "cohort" in p
            assert "side" in p
            assert "note" in p
            assert "lag" in p
            assert "weight" in p

    def test_notes_are_nonempty(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        for p in result["players"]:
            assert p["note"], f"empty note for {p['cohort']}"

    def test_coinbase_premium_present(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        cohorts = [p["cohort"] for p in result["players"]]
        assert any("Coinbase" in c for c in cohorts)

    def test_deribit_options_present(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        cohorts = [p["cohort"] for p in result["players"]]
        assert any("Deribit" in c or "Options" in c for c in cohorts)

    def test_whale_prints_present(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        cohorts = [p["cohort"] for p in result["players"]]
        assert any("Whale" in c for c in cohorts)

    def test_stablecoin_present(self, full_snapshot):
        result = who_is_winning(full_snapshot)
        cohorts = [p["cohort"] for p in result["players"]]
        assert any("Stablecoin" in c or "dry powder" in c for c in cohorts)

    def test_full_snapshot_buyers_win(self, full_snapshot):
        # full_snapshot is configured to favor buyers (taker 52.8%, bid-heavy, etc.)
        result = who_is_winning(full_snapshot)
        assert result["winner"] == "BUYERS"
        assert result["bull_pts"] > result["bear_pts"]

    def test_minimal_is_nobody(self, minimal_snapshot):
        result = who_is_winning(minimal_snapshot)
        # taker_share = 0.50 → neutral, nothing else scores
        assert result["winner"] == "NOBODY"
        assert result["color"] == "neutral"
