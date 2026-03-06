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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS zone_str_metrics (
            link_zona TEXT PRIMARY KEY,
            median_nightly_rate REAL,
            listing_count INTEGER,
            avg_bedrooms REAL,
            avg_rating REAL,
            computed_at TEXT
        )
    """
    )
    conn.commit()
    conn.close()


def compute_zone_metrics(
    listings: list[dict],
    min_reviews: int = 3,
    min_rating: float = 4.85,
    trim_pct: float = 0.1,
) -> Optional[dict]:
    """Compute aggregate STR metrics from a list of listing dicts.

    Filters listings to those with at least `min_reviews` and `min_rating`.
    Trims the top and bottom `trim_pct` of nightly rates before computing the median.
    Each dict should have keys: nightly_rate, bedrooms, rating, review_count.
    Returns None if the filtered list is empty.
    """
    if not listings:
        return None

    # Filter out listings with too few reviews or low ratings
    valid_listings = [
        r
        for r in listings
        if r.get("review_count") is not None
        and r["review_count"] >= min_reviews
        and r.get("rating") is not None
        and r["rating"] >= min_rating
    ]

    if not valid_listings:
        logger.info(
            "compute_zone_metrics: No listings met the min_reviews >= %d criteria out of %d total.",
            min_reviews,
            len(listings),
        )
        return None

    rates = sorted(
        r["nightly_rate"] for r in valid_listings if r.get("nightly_rate") is not None
    )
    bedrooms = [r["bedrooms"] for r in valid_listings if r.get("bedrooms") is not None]
    ratings = [r["rating"] for r in valid_listings if r.get("rating") is not None]

    if rates:
        n = len(rates)
        trim_count = int(n * trim_pct)

        # Strip outliers from top and bottom
        if trim_count > 0 and n > trim_count * 2:
            rates = rates[trim_count:-trim_count]

        n_trimmed = len(rates)
        mid = n_trimmed // 2
        median_rate = rates[mid] if n_trimmed % 2 else (rates[mid - 1] + rates[mid]) / 2
    else:
        median_rate = None

    return {
        "listing_count": len(valid_listings),
        "median_nightly_rate": median_rate,
        "avg_bedrooms": sum(bedrooms) / len(bedrooms) if bedrooms else None,
        "avg_rating": sum(ratings) / len(ratings) if ratings else None,
    }


def update_zone_str_metrics(db_path: str, link_zona: str) -> None:
    """Recompute and persist STR metrics for a zone from its sampled listings."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT nightly_rate, bedrooms, rating, review_count FROM airbnb_listings WHERE link_zona = ?",
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
