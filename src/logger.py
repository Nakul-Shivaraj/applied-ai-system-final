"""
logger.py — Run logging for VibeFinder 2.0

Writes a timestamped log entry for every recommendation run,
including profile name, scoring mode, top results, and any errors.
Log file is saved to logs/run_log.txt in the project root.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional


LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "run_log.txt"


def setup_logger() -> logging.Logger:
    """
    Set up and return the VibeFinder run logger.
    Creates the logs/ directory if it does not exist.
    """
    LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger("vibefinder")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        # File handler — full detail
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

        # Console handler — errors only
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.ERROR)
        console_fmt = logging.Formatter("[VibeFinder ERROR] %(message)s")
        console_handler.setFormatter(console_fmt)
        logger.addHandler(console_handler)

    return logger


def log_run(
    profile_name: str,
    scoring_mode: str,
    recommendations: List[Tuple[Dict, float, str]],
    errors: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
) -> None:
    """
    Write a structured log entry for one recommendation run.

    Args:
        profile_name:    Name of the user profile being evaluated.
        scoring_mode:    Scoring mode used (e.g., 'genre-first').
        recommendations: List of (song, score, explanation) tuples.
        errors:          Any validation errors that occurred.
        warnings:        Any non-fatal warnings (e.g., filter bubble risk).
    """
    logger = setup_logger()

    logger.info("=" * 60)
    logger.info(f"RUN START | Profile: {profile_name} | Mode: {scoring_mode}")
    logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if errors:
        for err in errors:
            logger.error(f"VALIDATION ERROR: {err}")

    if warnings:
        for warn in warnings:
            logger.warning(f"WARNING: {warn}")

    if recommendations:
        logger.info(f"Results ({len(recommendations)} recommendations):")
        for rank, (song, score, _) in enumerate(recommendations, 1):
            logger.info(
                f"  #{rank} | {song.get('title', 'Unknown')} "
                f"by {song.get('artist', 'Unknown')} "
                f"| Genre: {song.get('genre', '?')} "
                f"| Score: {score:.1f}/100"
            )
    else:
        logger.warning("No recommendations generated.")

    logger.info("RUN END")
    logger.info("=" * 60)


def log_error(message: str) -> None:
    """Log a standalone error message."""
    logger = setup_logger()
    logger.error(message)


def log_warning(message: str) -> None:
    """Log a standalone warning message."""
    logger = setup_logger()
    logger.warning(message)
