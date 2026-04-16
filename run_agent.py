"""
agentic_demo.py — Stretch Feature 2: Agentic Workflow Demo

Runs the full 6-step agentic reasoning chain across three user profiles,
showing observable intermediate steps for each run.

Run with: python agentic_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent import run_agent, print_agent_results

PROFILES = [
    {
        "name": "Lofi Devotee",
        "preferred_genres": ["lofi", "ambient"],
        "preferred_moods": ["chill", "focused"],
        "target_energy": 0.40,
        "target_valence": 0.60,
        "target_danceability": 0.60,
        "target_acousticness": 0.80,
        "target_tempo_bpm": 75,
        "prefer_popular_songs": False,
        "preferred_release_decades": ["2020s", "2010s"],
        "preferred_mood_tags": ["chill", "nostalgic", "peaceful"],
        "target_artist_popularity": 70.0,
        "target_song_length_seconds": 200.0,
    },
    {
        "name": "Confused Party Animal",
        "preferred_genres": ["lofi", "ambient"],
        "preferred_moods": ["intense", "happy"],
        "target_energy": 0.90,
        "target_valence": 0.85,
        "target_danceability": 0.85,
        "target_acousticness": 0.05,
        "target_tempo_bpm": 140,
        "prefer_popular_songs": True,
        "preferred_release_decades": ["2010s", "2020s"],
        "preferred_mood_tags": ["energetic", "intense", "happy"],
        "target_artist_popularity": 80.0,
        "target_song_length_seconds": 240.0,
    },
    {
        "name": "Jazz Snob",
        "preferred_genres": ["jazz"],
        "preferred_moods": ["relaxed"],
        "target_energy": 0.35,
        "target_valence": 0.70,
        "target_danceability": 0.50,
        "target_acousticness": 0.90,
        "target_tempo_bpm": 92,
        "prefer_popular_songs": False,
        "preferred_release_decades": ["1980s", "1970s"],
        "preferred_mood_tags": ["relaxed", "sophisticated", "smooth"],
        "target_artist_popularity": 60.0,
        "target_song_length_seconds": 260.0,
    },
]


def main():
    print("\n" + "=" * 66)
    print("  STRETCH FEATURE 2: AGENTIC WORKFLOW DEMO")
    print("  6-step reasoning chain with observable intermediate steps")
    print("=" * 66)

    for profile in PROFILES:
        result = run_agent(
            user_prefs=profile,
            songs_path="data/songs.csv",
            scoring_mode="genre-first",
            k=3,
            verbose=True,
        )
        print_agent_results(result)

    print("=" * 66)
    print("  All agent runs complete. See logs/run_log.txt for full audit trail.")
    print("=" * 66 + "\n")


if __name__ == "__main__":
    main()