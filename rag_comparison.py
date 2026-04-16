"""
demo_rag.py — Stretch Feature 1: RAG Enhancement Demo

Runs a side-by-side comparison showing how RAG-grounded explanations
measurably improve over the baseline (no retrieval) for the same songs.

Run with: python demo_rag.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.recommender import load_songs, recommend_songs
from src.rag import compare_baseline_vs_rag

DEMO_PROFILE = {
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
}


def main():
    songs = load_songs("data/songs.csv")
    recommendations = recommend_songs(DEMO_PROFILE, songs, k=2, mode="genre-first")

    print("\n" + "=" * 70)
    print("  STRETCH FEATURE 1: RAG ENHANCEMENT — Baseline vs RAG Comparison")
    print("  Profile: Lofi Devotee")
    print("=" * 70)

    for rank, (song, score, _) in enumerate(recommendations, 1):
        baseline, rag = compare_baseline_vs_rag(song, score, DEMO_PROFILE)

        print(f"\n  Recommendation #{rank}: {song.get('title')} by {song.get('artist')}")
        print("\n  --- BASELINE (no retrieval) ---")
        for line in baseline.split("\n"):
            print(f"  {line}")

        print("\n  --- RAG-GROUNDED (with knowledge base retrieval) ---")
        for line in rag.split("\n"):
            print(f"  {line}")

        print("\n  " + "-" * 66)

    print("\n  RAG improvement: explanations now reference documented artist")
    print("  characteristics and genre traits instead of generic score language.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()