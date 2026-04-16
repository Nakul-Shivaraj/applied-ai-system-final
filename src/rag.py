"""
rag.py — Retrieval-Augmented Generation for VibeFinder 2.0

Retrieves relevant facts from a local knowledge base (knowledge_base.json)
about artists and genres before generating a recommendation explanation.

This measurably improves explanation quality over a baseline (no retrieval)
by grounding every claim in documented artist/genre characteristics rather
than generating generic descriptions.

Stretch Feature 1: RAG Enhancement
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# Path to knowledge base — sits in project root /data/ folder
_KB_PATH = Path(__file__).parent.parent / "data" / "knowledge_base.json"


def load_knowledge_base(path: Optional[Path] = None) -> Dict:
    """
    Load the knowledge base from disk.

    Args:
        path: Optional custom path. Defaults to data/knowledge_base.json.

    Returns:
        Knowledge base dictionary with 'artists' and 'genres' keys.
        Returns empty dict if file not found.
    """
    kb_path = path or _KB_PATH
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[RAG] Warning: Knowledge base not found at {kb_path}. Using empty KB.")
        return {"artists": {}, "genres": {}}
    except json.JSONDecodeError as e:
        print(f"[RAG] Warning: Could not parse knowledge base: {e}")
        return {"artists": {}, "genres": {}}


def retrieve_context(
    song: Dict,
    knowledge_base: Dict,
) -> Tuple[Optional[Dict], Optional[Dict]]:
    """
    Retrieve artist and genre facts from the knowledge base for a given song.

    Lookup is case-insensitive. Returns None for each if not found.

    Args:
        song:           Song dictionary with 'artist' and 'genre' keys.
        knowledge_base: Loaded knowledge base dictionary.

    Returns:
        Tuple of (artist_facts, genre_facts) — either can be None if not found.
    """
    artist_key = song.get("artist", "").strip().lower()
    genre_key = song.get("genre", "").strip().lower()

    artist_facts = knowledge_base.get("artists", {}).get(artist_key)
    genre_facts = knowledge_base.get("genres", {}).get(genre_key)

    return artist_facts, genre_facts


def generate_explanation(
    song: Dict,
    score: float,
    user_prefs: Dict,
    artist_facts: Optional[Dict],
    genre_facts: Optional[Dict],
    conflict_message: Optional[str] = None,
) -> str:
    """
    Generate a grounded natural language explanation for a recommendation.

    When artist_facts and genre_facts are available (RAG), the explanation
    references specific documented characteristics. Without retrieval (baseline),
    the explanation falls back to generic score-based language.

    Args:
        song:             Song dictionary.
        score:            Normalized recommendation score (0-100).
        user_prefs:       User preferences dictionary.
        artist_facts:     Retrieved artist facts from knowledge base (or None).
        genre_facts:      Retrieved genre facts from knowledge base (or None).
        conflict_message: Optional conflict string from self-critique agent.

    Returns:
        Multi-line explanation string.
    """
    title = song.get("title", "Unknown")
    artist = song.get("artist", "Unknown")
    genre = song.get("genre", "Unknown")
    energy = song.get("energy", 0.0)
    target_energy = user_prefs.get("target_energy", 0.5)

    lines = []

    # --- RAG-grounded explanation (when context is retrieved) ---
    if artist_facts or genre_facts:
        lines.append(f"'{title}' by {artist} — Score: {score:.1f}/100")

        if artist_facts:
            lines.append(f"  Artist context: {artist_facts['description']}")
            style = ", ".join(artist_facts.get("style_tags", []))
            if style:
                lines.append(f"  Known for: {style}")

        if genre_facts:
            lines.append(f"  Genre context: {genre_facts['description']}")
            common_moods = ", ".join(genre_facts.get("common_moods", []))
            if common_moods:
                lines.append(f"  Typical moods: {common_moods}")

        # Energy alignment note
        energy_diff = abs(energy - target_energy)
        if energy_diff <= 0.10:
            lines.append(
                f"  Energy alignment: Song energy ({energy:.2f}) is a strong match "
                f"for your target ({target_energy:.2f})."
            )
        elif energy_diff <= 0.30:
            lines.append(
                f"  Energy alignment: Song energy ({energy:.2f}) is close to "
                f"your target ({target_energy:.2f})."
            )
        else:
            lines.append(
                f"  Energy alignment: Song energy ({energy:.2f}) differs significantly "
                f"from your target ({target_energy:.2f})."
            )

    # --- Baseline explanation (no retrieval context available) ---
    else:
        lines.append(f"'{title}' by {artist} ({genre}) — Score: {score:.1f}/100")
        lines.append(
            f"  Recommended based on feature matching. "
            f"No additional artist or genre context available."
        )

    # --- Conflict warning from self-critique agent ---
    if conflict_message:
        lines.append(f"  ⚠ CONFLICT: {conflict_message}")

    return "\n".join(lines)


def explain_recommendations(
    recommendations: List[Tuple[Dict, float, str]],
    user_prefs: Dict,
    conflicts: Optional[List[Optional[str]]] = None,
    kb_path: Optional[Path] = None,
) -> List[str]:
    """
    Generate RAG-grounded explanations for a full list of recommendations.

    Args:
        recommendations: List of (song, score, explanation) tuples.
        user_prefs:      User preferences dictionary.
        conflicts:       Optional list of conflict messages (one per recommendation).
        kb_path:         Optional custom path to knowledge base.

    Returns:
        List of explanation strings, one per recommendation.
    """
    kb = load_knowledge_base(kb_path)
    explanations = []

    for i, (song, score, _) in enumerate(recommendations):
        artist_facts, genre_facts = retrieve_context(song, kb)
        conflict = conflicts[i] if conflicts and i < len(conflicts) else None

        explanation = generate_explanation(
            song=song,
            score=score,
            user_prefs=user_prefs,
            artist_facts=artist_facts,
            genre_facts=genre_facts,
            conflict_message=conflict,
        )
        explanations.append(explanation)

    return explanations


def compare_baseline_vs_rag(
    song: Dict,
    score: float,
    user_prefs: Dict,
    kb_path: Optional[Path] = None,
) -> Tuple[str, str]:
    """
    Generate both a baseline explanation and a RAG-grounded explanation
    for the same song. Used to demonstrate measurable improvement.

    Args:
        song:       Song dictionary.
        score:      Normalized score.
        user_prefs: User preferences dictionary.
        kb_path:    Optional custom path to knowledge base.

    Returns:
        Tuple of (baseline_explanation, rag_explanation).
    """
    # Baseline — no retrieval
    baseline = generate_explanation(
        song=song,
        score=score,
        user_prefs=user_prefs,
        artist_facts=None,
        genre_facts=None,
    )

    # RAG — with retrieval
    kb = load_knowledge_base(kb_path)
    artist_facts, genre_facts = retrieve_context(song, kb)
    rag = generate_explanation(
        song=song,
        score=score,
        user_prefs=user_prefs,
        artist_facts=artist_facts,
        genre_facts=genre_facts,
    )

    return baseline, rag