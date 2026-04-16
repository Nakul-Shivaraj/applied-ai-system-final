"""
agent.py — Agentic Workflow for VibeFinder 2.0

Implements a multi-step reasoning chain with observable intermediate steps.
Each step prints its status as it runs, making the agent's decision-making
process fully transparent and auditable.

Steps:
  1. VALIDATE   — Run guardrails on user input
  2. RETRIEVE   — Fetch artist/genre context from knowledge base
  3. SCORE      — Run scoring engine + diversity filter
  4. CRITIQUE   — Check each result for conflicts and bubble risk
  5. EXPLAIN    — Generate RAG-grounded explanation per song
  6. LOG        — Write full audit trail to run_log.txt

Stretch Feature 2: Agentic Workflow Enhancement
"""

import time
from typing import Dict, List, Optional, Tuple

from src.guardrails import validate_user_prefs, validate_songs, validate_scoring_mode
from src.recommender import load_songs, recommend_songs
from src.rag import load_knowledge_base, retrieve_context, generate_explanation
from src.reliability import detect_genre_conflict, detect_filter_bubble, compute_confidence
from src.logger import log_run, setup_logger


# ─── AGENT STEP PRINTER ──────────────────────────────────────────────────────

def _step(number: int, total: int, label: str, status: str, detail: str = "") -> None:
    """Print a formatted agent step line."""
    detail_str = f"  {detail}" if detail else ""
    print(f"  [AGENT] Step {number}/{total} — {label:<28} {status}{detail_str}")


# ─── AGENT RESULT ────────────────────────────────────────────────────────────

class AgentResult:
    """
    Container for the full output of one agent run.

    Attributes:
        profile_name:    Name of the user profile.
        recommendations: Scored and ranked song tuples.
        explanations:    RAG-grounded explanation strings.
        conflicts:       Conflict message per recommendation (or None).
        confidence:      Confidence score per recommendation.
        warnings:        Non-fatal warnings (filter bubble, etc.).
        errors:          Validation errors that stopped the run.
        success:         True if the run completed without fatal errors.
    """
    def __init__(self):
        self.profile_name: str = ""
        self.recommendations: List[Tuple[Dict, float, str]] = []
        self.explanations: List[str] = []
        self.conflicts: List[Optional[str]] = []
        self.confidence: List[float] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.success: bool = False


# ─── MAIN AGENT ──────────────────────────────────────────────────────────────

def run_agent(
    user_prefs: Dict,
    songs_path: str = "data/songs.csv",
    scoring_mode: str = "genre-first",
    k: int = 5,
    verbose: bool = True,
) -> AgentResult:
    """
    Run the full 6-step agentic reasoning chain for one user profile.

    Args:
        user_prefs:    User preferences dictionary.
        songs_path:    Path to the song catalog CSV.
        scoring_mode:  Scoring strategy to use.
        k:             Number of recommendations to return.
        verbose:       Print step-by-step status (default True).

    Returns:
        AgentResult containing all outputs and intermediate state.
    """
    TOTAL_STEPS = 6
    result = AgentResult()
    result.profile_name = user_prefs.get("name", "Unknown Profile")

    if verbose:
        print(f"\n  {'=' * 62}")
        print(f"  AGENT RUN — {result.profile_name}")
        print(f"  Mode: {scoring_mode} | Top-K: {k}")
        print(f"  {'=' * 62}")

    # ── STEP 1: VALIDATE ─────────────────────────────────────────────────────
    prefs_valid, prefs_errors = validate_user_prefs(user_prefs)
    mode_valid, mode_errors = validate_scoring_mode(scoring_mode)

    all_errors = prefs_errors + mode_errors
    if not prefs_valid or not mode_valid:
        result.errors = all_errors
        result.success = False
        if verbose:
            _step(1, TOTAL_STEPS, "Validating input...", "✗ FAILED")
            for err in all_errors:
                print(f"    → {err}")
        return result

    if verbose:
        _step(1, TOTAL_STEPS, "Validating input...", "✓ passed")

    # ── STEP 2: RETRIEVE ─────────────────────────────────────────────────────
    songs = load_songs(songs_path)
    songs_valid, songs_errors = validate_songs(songs)

    if not songs_valid:
        result.errors = songs_errors
        result.success = False
        if verbose:
            _step(2, TOTAL_STEPS, "Retrieving context...", "✗ FAILED", songs_errors[0])
        return result

    kb = load_knowledge_base()
    kb_hits = 0
    for song in songs[:k]:
        artist_facts, genre_facts = retrieve_context(song, kb)
        if artist_facts or genre_facts:
            kb_hits += 1

    if verbose:
        _step(
            2, TOTAL_STEPS, "Retrieving context...", "✓ done",
            f"({kb_hits}/{min(k, len(songs))} songs have KB entries)"
        )

    # ── STEP 3: SCORE ────────────────────────────────────────────────────────
    recommendations = recommend_songs(user_prefs, songs, k=k, mode=scoring_mode)
    result.recommendations = recommendations

    if verbose:
        _step(
            3, TOTAL_STEPS, "Scoring songs...", "✓ done",
            f"(top-{len(recommendations)} selected from {len(songs)} songs)"
        )

    # ── STEP 4: CRITIQUE ─────────────────────────────────────────────────────
    conflicts: List[Optional[str]] = []
    warnings: List[str] = []
    conflict_count = 0

    for song, score, _ in recommendations:
        conflict = detect_genre_conflict(song, user_prefs)
        conflicts.append(conflict)
        if conflict:
            conflict_count += 1

    bubble_warning = detect_filter_bubble(recommendations, len(songs))
    if bubble_warning:
        warnings.append(bubble_warning)

    result.conflicts = conflicts
    result.warnings = warnings

    critique_status = "✓ no conflicts" if conflict_count == 0 else f"⚠ {conflict_count} conflict(s) detected"
    if bubble_warning:
        critique_status += " + bubble risk"

    if verbose:
        _step(4, TOTAL_STEPS, "Running self-critique...", critique_status)

    # ── STEP 5: EXPLAIN ──────────────────────────────────────────────────────
    explanations: List[str] = []
    confidence_scores: List[float] = []

    preferred_genres = [g.lower() for g in user_prefs.get("preferred_genres", [])]
    preferred_moods = [m.lower() for m in user_prefs.get("preferred_moods", [])]

    for i, (song, score, _) in enumerate(recommendations):
        artist_facts, genre_facts = retrieve_context(song, kb)
        explanation = generate_explanation(
            song=song,
            score=score,
            user_prefs=user_prefs,
            artist_facts=artist_facts,
            genre_facts=genre_facts,
            conflict_message=conflicts[i],
        )
        explanations.append(explanation)

        genre_match = song.get("genre", "").lower() in preferred_genres
        mood_match = song.get("mood", "").lower() in preferred_moods
        confidence = compute_confidence(score, genre_match, mood_match)
        confidence_scores.append(confidence)

    result.explanations = explanations
    result.confidence = confidence_scores
    avg_conf = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    if verbose:
        _step(
            5, TOTAL_STEPS, "Generating explanations...", "✓ done",
            f"(avg confidence: {avg_conf:.2f})"
        )

    # ── STEP 6: LOG ──────────────────────────────────────────────────────────
    log_run(
        profile_name=result.profile_name,
        scoring_mode=scoring_mode,
        recommendations=recommendations,
        errors=result.errors if result.errors else None,
        warnings=warnings if warnings else None,
    )

    if verbose:
        _step(6, TOTAL_STEPS, "Logging run...", "✓ saved to logs/run_log.txt")
        print(f"  {'=' * 62}\n")

    result.success = True
    return result


def print_agent_results(result: AgentResult) -> None:
    """
    Print a formatted summary of agent results including
    explanations, confidence scores, and any warnings.
    """
    if not result.success:
        print(f"\n  Agent run failed for '{result.profile_name}':")
        for err in result.errors:
            print(f"  → {err}")
        return

    print(f"\n  RESULTS — {result.profile_name}")
    print("  " + "-" * 60)

    for i, (song, score, _) in enumerate(result.recommendations):
        conf = result.confidence[i] if i < len(result.confidence) else 0.0
        print(f"\n  #{i+1} {song.get('title')} by {song.get('artist')}")
        print(f"      Score: {score:.1f}/100  |  Confidence: {conf:.2f}")
        if result.explanations and i < len(result.explanations):
            for line in result.explanations[i].split("\n")[1:]:
                print(f"  {line}")

    if result.warnings:
        print("\n  Warnings:")
        for w in result.warnings:
            print(f"  ⚠ {w}")

    print()