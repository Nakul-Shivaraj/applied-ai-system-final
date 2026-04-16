"""
reliability.py — Reliability scoring for VibeFinder 2.0

Tests consistency and quality of recommendations by:
1. Running the same profile multiple times and checking stability
2. Computing a confidence score (0.0-1.0) per recommendation
3. Detecting filter bubble risk when catalog coverage is too narrow
4. Flagging genre conflicts between user preferences and top result
"""

from typing import Dict, List, Tuple, Optional


def compute_confidence(
    score: float,
    genre_match: bool,
    mood_match: bool,
) -> float:
    """
    Compute a 0.0–1.0 confidence score for a single recommendation.

    Confidence = normalized score * category match bonus

    Args:
        score:       Normalized recommendation score (0–100).
        genre_match: True if the song's genre is in user's preferred genres.
        mood_match:  True if the song's mood is in user's preferred moods.

    Returns:
        Confidence score between 0.0 and 1.0.
    """
    base = score / 100.0

    # Bonus for categorical alignment — each match adds 5%
    bonus = 0.0
    if genre_match:
        bonus += 0.05
    if mood_match:
        bonus += 0.05

    return min(1.0, round(base + bonus, 3))


def detect_genre_conflict(
    song: Dict,
    user_prefs: Dict,
) -> Optional[str]:
    """
    Check if the recommended song's genre conflicts with user preferences.

    Returns a conflict message string if a conflict is detected, else None.

    Args:
        song:       Song dictionary.
        user_prefs: User preferences dictionary.

    Returns:
        Conflict description string, or None if no conflict.
    """
    song_genre = song.get("genre", "").strip().lower()
    preferred = [g.strip().lower() for g in user_prefs.get("preferred_genres", [])]

    if preferred and song_genre not in preferred:
        return (
            f"Genre conflict: user requested {preferred} "
            f"but got '{song_genre}'. "
            f"Likely cause: numerical feature targets (energy, tempo) "
            f"dominated the score."
        )
    return None


def detect_filter_bubble(
    recommendations: List[Tuple[Dict, float, str]],
    catalog_size: int,
) -> Optional[str]:
    """
    Detect filter bubble risk in the top-K recommendations.

    Flags when:
    - All top results share the same genre (genre bubble)
    - The catalog is too small to produce meaningful diversity

    Args:
        recommendations: List of (song, score, explanation) tuples.
        catalog_size:    Total number of songs in the catalog.

    Returns:
        Warning string if bubble risk detected, else None.
    """
    if not recommendations:
        return None

    genres = [r[0].get("genre", "") for r in recommendations]
    unique_genres = set(genres)

    if len(unique_genres) == 1:
        return (
            f"Filter bubble risk: all {len(recommendations)} recommendations "
            f"share the same genre ('{genres[0]}'). "
            f"Consider broadening genre preferences or expanding the catalog."
        )

    if catalog_size < 10:
        return (
            f"Catalog too small ({catalog_size} songs) to guarantee meaningful diversity. "
            f"Results may not reflect algorithm quality."
        )

    return None


def run_consistency_check(
    user_prefs: Dict,
    songs: List[Dict],
    recommend_fn,
    runs: int = 3,
    mode: str = "balanced",
) -> Tuple[bool, float, str]:
    """
    Run the recommender multiple times and check if top result is stable.

    A recommender is considered consistent if the top recommendation
    is identical across all runs (deterministic scoring).

    Args:
        user_prefs:    User preferences dictionary.
        songs:         Song catalog.
        recommend_fn:  The recommend_songs function to call.
        runs:          Number of times to repeat the run (default 3).
        mode:          Scoring mode to use.

    Returns:
        Tuple of (is_consistent: bool, stability_rate: float, message: str)
        stability_rate = fraction of runs matching the first run's top result.
    """
    top_results = []

    for _ in range(runs):
        result = recommend_fn(user_prefs, songs, k=1, mode=mode)
        if result:
            top_results.append(result[0][0].get("id"))
        else:
            top_results.append(None)

    if not top_results or top_results[0] is None:
        return False, 0.0, "No recommendations generated — cannot assess consistency."

    reference = top_results[0]
    matches = sum(1 for r in top_results if r == reference)
    stability_rate = matches / runs

    if stability_rate == 1.0:
        msg = f"Consistent across all {runs} runs. Top result always: ID {reference}."
    else:
        msg = (
            f"Inconsistent results across {runs} runs "
            f"(stability: {stability_rate:.0%}). "
            f"Non-determinism may indicate a scoring bug."
        )

    return stability_rate == 1.0, round(stability_rate, 2), msg


def summarize_reliability(
    profile_name: str,
    recommendations: List[Tuple[Dict, float, str]],
    user_prefs: Dict,
    catalog_size: int,
    consistency_result: Optional[Tuple[bool, float, str]] = None,
) -> str:
    """
    Generate a human-readable reliability summary for one profile run.

    Args:
        profile_name:        Name of the user profile.
        recommendations:     Top-K recommendation tuples.
        user_prefs:          User preferences dictionary.
        catalog_size:        Total songs in catalog.
        consistency_result:  Output of run_consistency_check (optional).

    Returns:
        Multi-line reliability report string.
    """
    lines = [f"\n  RELIABILITY REPORT — {profile_name}"]
    lines.append("  " + "-" * 50)

    if not recommendations:
        lines.append("  No recommendations to evaluate.")
        return "\n".join(lines)

    # Per-recommendation confidence + conflict check
    total_confidence = 0.0
    preferred_genres = [g.lower() for g in user_prefs.get("preferred_genres", [])]
    preferred_moods = [m.lower() for m in user_prefs.get("preferred_moods", [])]

    for rank, (song, score, _) in enumerate(recommendations, 1):
        genre_match = song.get("genre", "").lower() in preferred_genres
        mood_match = song.get("mood", "").lower() in preferred_moods
        confidence = compute_confidence(score, genre_match, mood_match)
        total_confidence += confidence

        conflict = detect_genre_conflict(song, user_prefs)
        conflict_tag = " ⚠ CONFLICT" if conflict else ""
        lines.append(
            f"  #{rank} {song.get('title', '?')} | "
            f"Score: {score:.1f} | Confidence: {confidence:.2f}{conflict_tag}"
        )
        if conflict and rank == 1:
            lines.append(f"      → {conflict}")

    avg_confidence = total_confidence / len(recommendations)
    lines.append(f"\n  Average confidence: {avg_confidence:.2f} / 1.00")

    # Filter bubble check
    bubble = detect_filter_bubble(recommendations, catalog_size)
    if bubble:
        lines.append(f"  ⚠ {bubble}")

    # Consistency check
    if consistency_result:
        is_consistent, stability_rate, msg = consistency_result
        status = "✓" if is_consistent else "⚠"
        lines.append(f"  {status} Consistency: {msg}")

    return "\n".join(lines)
