"""
tests/test_reliability.py — Automated tests for VibeFinder 2.0

Tests cover:
- Guardrails (input validation)
- Confidence scoring
- Genre conflict detection
- Filter bubble detection
- Consistency checker
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from src.guardrails import validate_user_prefs, validate_songs, validate_scoring_mode
from src.reliability import (
    compute_confidence,
    detect_genre_conflict,
    detect_filter_bubble,
    run_consistency_check,
)


# ─── SAMPLE DATA ────────────────────────────────────────────────────────────

VALID_PREFS = {
    "preferred_genres": ["lofi", "ambient"],
    "preferred_moods": ["chill", "focused"],
    "target_energy": 0.40,
    "target_valence": 0.60,
    "target_danceability": 0.60,
    "target_acousticness": 0.80,
    "target_tempo_bpm": 75,
    "prefer_popular_songs": False,
    "preferred_release_decades": ["2020s", "2010s"],
    "preferred_mood_tags": ["chill", "nostalgic"],
    "target_artist_popularity": 70.0,
    "target_song_length_seconds": 200.0,
}

SAMPLE_SONGS = [
    {
        "id": 1, "title": "Midnight Coding", "artist": "LoRoom",
        "genre": "lofi", "mood": "chill", "energy": 0.38,
        "valence": 0.55, "danceability": 0.58, "acousticness": 0.82,
        "tempo_bpm": 78, "song_popularity": 60, "artist_popularity": 65,
        "release_decade": "2020s", "detailed_moods": "chill,nostalgic",
        "song_length_seconds": 195,
    },
    {
        "id": 2, "title": "Gym Hero", "artist": "Max Pulse",
        "genre": "pop", "mood": "intense", "energy": 0.93,
        "valence": 0.77, "danceability": 0.88, "acousticness": 0.05,
        "tempo_bpm": 132, "song_popularity": 85, "artist_popularity": 80,
        "release_decade": "2020s", "detailed_moods": "energetic,intense",
        "song_length_seconds": 210,
    },
    {
        "id": 3, "title": "Focus Flow", "artist": "NeuroBeat",
        "genre": "ambient", "mood": "focused", "energy": 0.35,
        "valence": 0.50, "danceability": 0.45, "acousticness": 0.90,
        "tempo_bpm": 70, "song_popularity": 55, "artist_popularity": 60,
        "release_decade": "2020s", "detailed_moods": "focused,calm",
        "song_length_seconds": 240,
    },
]


# ─── GUARDRAILS TESTS ────────────────────────────────────────────────────────

class TestGuardrails:

    def test_valid_prefs_pass(self):
        """Valid preferences should pass with no errors."""
        is_valid, errors = validate_user_prefs(VALID_PREFS)
        assert is_valid is True
        assert errors == []

    def test_missing_required_field(self):
        """Missing a required field should fail validation."""
        prefs = {k: v for k, v in VALID_PREFS.items() if k != "target_energy"}
        is_valid, errors = validate_user_prefs(prefs)
        assert is_valid is False
        assert any("target_energy" in e for e in errors)

    def test_energy_out_of_range(self):
        """Energy value above 1.0 should fail."""
        prefs = {**VALID_PREFS, "target_energy": 1.5}
        is_valid, errors = validate_user_prefs(prefs)
        assert is_valid is False
        assert any("target_energy" in e for e in errors)

    def test_empty_genre_list(self):
        """Empty preferred_genres list should fail."""
        prefs = {**VALID_PREFS, "preferred_genres": []}
        is_valid, errors = validate_user_prefs(prefs)
        assert is_valid is False
        assert any("preferred_genres" in e for e in errors)

    def test_invalid_tempo(self):
        """Tempo below 20 BPM should fail."""
        prefs = {**VALID_PREFS, "target_tempo_bpm": 5}
        is_valid, errors = validate_user_prefs(prefs)
        assert is_valid is False
        assert any("target_tempo_bpm" in e for e in errors)

    def test_empty_catalog_fails(self):
        """Empty song list should fail catalog validation."""
        is_valid, errors = validate_songs([])
        assert is_valid is False
        assert any("empty" in e.lower() for e in errors)

    def test_valid_songs_pass(self):
        """A catalog with enough songs should pass."""
        is_valid, errors = validate_songs(SAMPLE_SONGS * 3)
        assert is_valid is True

    def test_invalid_scoring_mode(self):
        """Unknown scoring mode should fail."""
        is_valid, errors = validate_scoring_mode("ultra-vibes")
        assert is_valid is False
        assert any("ultra-vibes" in e for e in errors)

    def test_valid_scoring_mode(self):
        """Known scoring mode should pass."""
        is_valid, errors = validate_scoring_mode("genre-first")
        assert is_valid is True
        assert errors == []


# ─── CONFIDENCE SCORING TESTS ────────────────────────────────────────────────

class TestConfidenceScoring:

    def test_perfect_score_full_match(self):
        """Score of 100 with both matches should give confidence near 1.0."""
        confidence = compute_confidence(100.0, genre_match=True, mood_match=True)
        assert confidence == 1.0

    def test_zero_score_no_confidence(self):
        """Score of 0 with no matches should give confidence 0.0."""
        confidence = compute_confidence(0.0, genre_match=False, mood_match=False)
        assert confidence == 0.0

    def test_bonus_for_genre_match(self):
        """Genre match should boost confidence above raw score alone."""
        base = compute_confidence(80.0, genre_match=False, mood_match=False)
        boosted = compute_confidence(80.0, genre_match=True, mood_match=False)
        assert boosted > base

    def test_confidence_capped_at_1(self):
        """Confidence should never exceed 1.0."""
        confidence = compute_confidence(95.0, genre_match=True, mood_match=True)
        assert confidence <= 1.0


# ─── CONFLICT DETECTION TESTS ────────────────────────────────────────────────

class TestConflictDetection:

    def test_genre_conflict_detected(self):
        """Pop song for a lofi-preferring user should flag a conflict."""
        conflict = detect_genre_conflict(SAMPLE_SONGS[1], VALID_PREFS)
        assert conflict is not None
        assert "pop" in conflict

    def test_no_conflict_for_matching_genre(self):
        """Lofi song for a lofi-preferring user should have no conflict."""
        conflict = detect_genre_conflict(SAMPLE_SONGS[0], VALID_PREFS)
        assert conflict is None

    def test_filter_bubble_same_genre(self):
        """All recommendations in same genre should flag filter bubble."""
        same_genre_recs = [(SAMPLE_SONGS[1], 80.0, "") for _ in range(3)]
        warning = detect_filter_bubble(same_genre_recs, catalog_size=18)
        assert warning is not None
        assert "bubble" in warning.lower()

    def test_no_bubble_diverse_genres(self):
        """Diverse genres across recommendations should not flag a bubble."""
        diverse_recs = [(song, 80.0, "") for song in SAMPLE_SONGS]
        warning = detect_filter_bubble(diverse_recs, catalog_size=18)
        assert warning is None

    def test_small_catalog_warning(self):
        """Catalog with fewer than 10 songs should flag a size warning."""
        recs = [(SAMPLE_SONGS[0], 90.0, ""), (SAMPLE_SONGS[2], 85.0, "")]
        warning = detect_filter_bubble(recs, catalog_size=3)
        assert warning is not None
        assert "small" in warning.lower() or "3" in warning


# ─── CONSISTENCY TESTS ───────────────────────────────────────────────────────

class TestConsistency:

    def test_deterministic_recommender_is_consistent(self):
        """A pure scoring function should produce identical results across runs."""
        from src.recommender import recommend_songs

        songs = SAMPLE_SONGS * 6  # expand catalog
        is_consistent, rate, msg = run_consistency_check(
            VALID_PREFS, songs, recommend_songs, runs=3, mode="balanced"
        )
        assert is_consistent is True
        assert rate == 1.0

    def test_empty_songs_fails_gracefully(self):
        """Empty catalog should return not-consistent with a clear message."""
        from src.recommender import recommend_songs

        is_consistent, rate, msg = run_consistency_check(
            VALID_PREFS, [], recommend_songs, runs=3
        )
        assert is_consistent is False
        assert "cannot" in msg.lower() or "no" in msg.lower()
