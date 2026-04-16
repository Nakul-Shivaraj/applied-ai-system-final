"""
guardrails.py — Input validation for VibeFinder 2.0

Validates user preference dictionaries before they reach the scoring engine.
Returns a list of error strings (empty = valid input).
"""

from typing import Dict, List, Tuple

VALID_SCORING_MODES = {"balanced", "genre-first", "mood-first", "energy-focused"}

REQUIRED_FIELDS = [
    "preferred_genres",
    "preferred_moods",
    "target_energy",
    "target_valence",
    "target_danceability",
    "target_acousticness",
    "target_tempo_bpm",
]


def validate_user_prefs(prefs: Dict) -> Tuple[bool, List[str]]:
    """
    Validate a user preferences dictionary.

    Checks:
    - Required fields are present and non-empty
    - Numerical targets are within valid ranges
    - Lists contain at least one item

    Args:
        prefs: User preferences dictionary

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
        is_valid is True only if errors list is empty.
    """
    errors: List[str] = []

    if not isinstance(prefs, dict):
        return False, ["User preferences must be a dictionary."]

    # Check required fields exist
    for field in REQUIRED_FIELDS:
        if field not in prefs:
            errors.append(f"Missing required field: '{field}'")

    if errors:
        return False, errors

    # Validate list fields
    for list_field in ["preferred_genres", "preferred_moods"]:
        val = prefs.get(list_field)
        if not isinstance(val, list) or len(val) == 0:
            errors.append(f"'{list_field}' must be a non-empty list.")

    # Validate 0-1 float fields
    for float_field in ["target_energy", "target_valence", "target_danceability", "target_acousticness"]:
        val = prefs.get(float_field)
        if not isinstance(val, (int, float)):
            errors.append(f"'{float_field}' must be a number.")
        elif not (0.0 <= val <= 1.0):
            errors.append(f"'{float_field}' must be between 0.0 and 1.0 (got {val}).")

    # Validate tempo
    tempo = prefs.get("target_tempo_bpm")
    if not isinstance(tempo, (int, float)):
        errors.append("'target_tempo_bpm' must be a number.")
    elif not (20 <= tempo <= 300):
        errors.append(f"'target_tempo_bpm' must be between 20 and 300 BPM (got {tempo}).")

    return len(errors) == 0, errors


def validate_songs(songs: List[Dict]) -> Tuple[bool, List[str]]:
    """
    Validate that the song catalog is usable.

    Args:
        songs: List of song dictionaries

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    errors: List[str] = []

    if not isinstance(songs, list):
        return False, ["Song catalog must be a list."]

    if len(songs) == 0:
        errors.append("Song catalog is empty. Cannot generate recommendations.")
        return False, errors

    if len(songs) < 5:
        errors.append(
            f"Song catalog has only {len(songs)} songs. "
            "Recommendations may lack diversity."
        )

    return len(errors) == 0, errors


def validate_scoring_mode(mode: str) -> Tuple[bool, List[str]]:
    """
    Validate that the requested scoring mode is supported.

    Args:
        mode: Scoring mode string

    Returns:
        Tuple of (is_valid: bool, errors: List[str])
    """
    if mode not in VALID_SCORING_MODES:
        return False, [
            f"Unknown scoring mode '{mode}'. "
            f"Valid options: {', '.join(sorted(VALID_SCORING_MODES))}"
        ]
    return True, []
