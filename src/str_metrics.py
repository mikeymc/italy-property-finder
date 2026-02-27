# ABOUTME: Aggregates per-zone short-term rental metrics from sampled Airbnb listings.
# ABOUTME: Computes median nightly rate, listing count, and quality signals per zone.

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def init_str_metrics_table(db_path: str) -> None:
    """Create zone_str_metrics table if it doesn't exist."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS zone_str_metrics (
            link_zona TEXT PRIMARY KEY,
            median_nightly_rate REAL,
            listing_count INTEGER,
            avg_bedrooms REAL,
            avg_rating REAL,
            computed_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def compute_zone_metrics(listings: list[dict]) -> Optional[dict]:
    """Compute aggregate STR metrics from a list of listing dicts.

    Each dict should have keys: nightly_rate, bedrooms, rating.
    Returns None if the list is empty.
    """
    if not listings:
        return None

    rates = sorted(r["nightly_rate"] for r in listings if r.get("nightly_rate") is not None)
    bedrooms = [r["bedrooms"] for r in listings if r.get("bedrooms") is not None]
    ratings = [r["rating"] for r in listings if r.get("rating") is not None]

    if rates:
        n = len(rates)
        mid = n // 2
        median_rate = rates[mid] if n % 2 else (rates[mid - 1] + rates[mid]) / 2
    else:
        median_rate = None

    return {
        "listing_count": len(listings),
        "median_nightly_rate": median_rate,
        "avg_bedrooms": sum(bedrooms) / len(bedrooms) if bedrooms else None,
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
    }


def update_zone_str_metrics(db_path: str, link_zona: str) -> None:
    """Recompute and persist STR metrics for a zone from its sampled listings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT nightly_rate, bedrooms, rating FROM airbnb_listings WHERE link_zona = ?",
        (link_zona,),
    ).fetchall()
    conn.close()

    if not rows:
        return

    listings = [dict(r) for r in rows]
    metrics = compute_zone_metrics(listings)
    if not metrics:
        return

    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO zone_str_metrics
           (link_zona, median_nightly_rate, listing_count, avg_bedrooms, avg_rating, computed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            link_zona,
            metrics["median_nightly_rate"],
            metrics["listing_count"],
            metrics["avg_bedrooms"],
            metrics["avg_rating"],
            now,
        ),
    )
    conn.commit()
    conn.close()
    logger.info("Updated STR metrics for zone %s: %s", link_zona, metrics)
