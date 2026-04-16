# Model Card: VibeFinder 2.0

## Model Name
**VibeFinder 2.0** — Extended Music Recommender System

## Base Project
VibeFinder 1.0, built during Module 3 of AI110 at Northeastern University. Original system implemented content-based scoring across 12 song features with four scoring modes and a diversity penalty.

---

## Goal / Task
VibeFinder 2.0 predicts which songs from a music catalog best match a user's musical preferences, then explains *why* each song was chosen, flags when a recommendation conflicts with stated preferences, and logs a full audit trail of every decision.

---

## Algorithm Summary
Songs are scored using a point-weighting algorithm across 12 features (genre, mood, energy, valence, danceability, acousticness, tempo, song popularity, artist popularity, release decade, mood tags, song length), normalized to a 0–100 scale. A greedy diversity filter applies compounding artist (35%) and genre (20%) penalties. A self-critique agent then checks each result for genre conflicts. Confidence scores (0.0–1.0) are computed per recommendation based on normalized score plus categorical match bonuses.

---

## Limitations and Biases

**Catalog size**: 18 songs is far too small to evaluate diversity, filter bubbles, or edge cases meaningfully. Any finding from this catalog should be treated as directional, not conclusive.

**Feature dominance bias**: The 12 numerical features mathematically outweigh the single categorical genre label. A user who requests lofi but has high-energy targets will consistently receive pop music — not because the algorithm is broken, but because that is what the weights encode. This is a design choice that needs to be made explicit to users, not hidden behind a score.

**Popularity bias**: Songs with high `song_popularity` scores are surfaced more for users who prefer popular content, creating a "rich get richer" pattern where already-popular songs become more visible regardless of actual fit.

**Era bias**: Decade preferences create temporal filter bubbles. A user who prefers 1980s music may never see anything recorded after 1999, even if it would match all their other preferences perfectly.

**No semantic understanding**: The system cannot capture qualities like "nostalgic," "intimate," or "cinematic" — only quantifiable attributes. Mood tags are matched by string equality, not meaning.

**Genre over-simplification**: Adjacent genres (synthwave vs. lofi, indie folk vs. acoustic pop) are treated as completely unrelated if neither appears in the user's preference list.

---

## Could This AI Be Misused?

The system itself is low-risk — it recommends songs, not decisions that affect people's lives. However, the design patterns it demonstrates could be misused at scale:

**Filter bubble amplification**: A production recommender using only content-based scoring with no diversity intervention would progressively narrow a user's musical exposure. VibeFinder addresses this with the diversity penalty, but a bad actor could disable it to maximize engagement with familiar content at the cost of discovery.

**Popularity manipulation**: Artificially inflating `song_popularity` scores for specific tracks could cause them to surface more often for users who prefer popular content — a form of algorithmic payola.

**Prevention measures built into VibeFinder 2.0**: The diversity penalty is on by default and logged. The self-critique agent flags conflicts transparently. The reliability scorer detects filter bubble risk and includes it in the output. None of these can be silently disabled without leaving a trace in the log file.

---

## What Surprised Me During Reliability Testing

The most surprising finding was that the consistency checker confirmed the scoring engine is **fully deterministic** — identical inputs always produce identical outputs across all runs. This sounds obvious, but it is actually meaningful: it rules out any randomness or hidden state as a source of unexpected behavior. When the system gives a surprising recommendation, the cause is always traceable to the weights, not to non-determinism.

The second surprise was how useful the **confidence score gap** turned out to be as a diagnostic. Coherent profiles (Lofi Devotee) averaged 0.87 confidence. Conflicting profiles (Confused Party Animal) dropped to 0.64 — a 23-point gap that made the genre/feature tension immediately visible without having to read through the full scoring breakdown. A number that low is a reliable signal that something in the preference profile deserves a second look.

---

## AI Collaboration — How Claude Was Used

This project was built with substantial assistance from Claude (Anthropic). Claude helped design the module architecture, wrote the initial versions of `guardrails.py`, `reliability.py`, `logger.py`, and `test_reliability.py`, generated the system architecture diagram, and drafted sections of this README and model card.

**One instance where AI assistance was genuinely helpful:**
When designing the self-critique agent, Claude suggested computing a confidence score that combined the normalized recommendation score *with* categorical match bonuses for genre and mood. This was better than the original plan of just flagging binary pass/fail conflicts, because it produced a continuous signal (0.0–1.0) that made the severity of a conflict immediately readable rather than just its presence.

**One instance where AI assistance was flawed:**
Claude initially suggested integrating the RAG retrieval step *after* the scoring and diversity filter had already run — meaning the AI explanation would be generated from final ranked results but would have no ability to influence the ranking itself. This made RAG decorative rather than functional, which directly contradicted the project requirement that the feature "meaningfully change how the system behaves." The fix was to restructure the pipeline so retrieval happens in parallel with scoring, giving the AI layer access to both ranked candidates and their retrieved context simultaneously before producing explanations.

---

## Evaluation

23 automated tests pass across two test files covering input validation, confidence scoring, conflict detection, filter bubble detection, and consistency checking. 7 stress-test profiles were run across all 4 scoring modes. The weight-shift experiment (doubling energy weight, halving genre weight) confirmed that increasing feature dominance makes recommendations *worse* for users with conflicting preferences — a finding that directly informed the decision to keep genre weight at its original level and add the self-critique layer instead.

---

## Intended Use
Classroom demonstration of applied AI system design concepts including RAG, agentic self-critique, reliability testing, and responsible AI documentation. Not intended for production music recommendation to real users.

## Non-Intended Use
Should not be used to make real music recommendations without significant catalog expansion, collaborative filtering signals, and user feedback integration.

---

## Ideas for Improvement
1. Expand catalog to 500+ songs across all genres to make diversity metrics meaningful
2. Add collaborative filtering — surface what users with similar taste profiles enjoy
3. Implement user feedback loop — let the system adjust weights based on thumbs up/down
4. Replace string-equality mood matching with semantic similarity using embeddings
5. Increase genre weight or implement explicit conflict resolution logic so categorical preferences are not silently overridden by numerical features