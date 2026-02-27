# ABOUTME: Orchestrates systematic Airbnb sampling across OMI zones by bounding box.
# ABOUTME: Tracks sampling state in SQLite and supports resumable sampling runs.

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Callable, Optional

from src.airbnb_scraper import AirbnbListing, search_by_bounds

logger = logging.getLogger(__name__)

# Default date range for sampling searches (representative summer peak)
DEFAULT_CHECKIN = "2025-07-01"
DEFAULT_CHECKOUT = "2025-07-06"


def init_sampling_tables(db_path: str) -> None:
    """Create zone_sampling_status table and add link_zona column to airbnb_listings."""
    conn = sqlite3.connect(db_path)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS zone_sampling_status (
            link_zona TEXT PRIMARY KEY,
            sampled_at TEXT,
            listing_count INTEGER,
            status TEXT
        )
    """)

    # Add link_zona to airbnb_listings if the table exists and column is absent
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "airbnb_listings" in tables:
        existing_cols = {
            row[1] for row in conn.execute("PRAGMA table_info(airbnb_listings)").fetchall()
        }
        if "link_zona" not in existing_cols:
            conn.execute("ALTER TABLE airbnb_listings ADD COLUMN link_zona TEXT")

    conn.commit()
    conn.close()


def get_zones_to_sample(
    db_path: str,
    province: Optional[str] = None,
    region: Optional[str] = None,
) -> list[dict]:
    """Return zones that have a bounding box and haven't been sampled yet."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT z.link_zona, z.region, z.province, z.comune_name, z.zona,
               z.ne_lat, z.ne_lng, z.sw_lat, z.sw_lng
        FROM omi_zones z
        LEFT JOIN zone_sampling_status s ON z.link_zona = s.link_zona
        WHERE z.ne_lat IS NOT NULL
          AND z.ne_lng IS NOT NULL
          AND z.sw_lat IS NOT NULL
          AND z.sw_lng IS NOT NULL
          AND s.link_zona IS NULL
    """
    params: list = []

    if province:
        query += " AND z.province = ?"
        params.append(province)
    if region:
        query += " AND z.region = ?"
        params.append(region)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_sampling_result(
    db_path: str,
    link_zona: str,
    status: str,
    listing_count: int,
) -> None:
    """Record the outcome of sampling a zone."""
    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT OR REPLACE INTO zone_sampling_status
           (link_zona, sampled_at, listing_count, status)
           VALUES (?, ?, ?, ?)""",
        (link_zona, now, listing_count, status),
    )
    conn.commit()
    conn.close()


def sample_zone(
    db_path: str,
    zone: dict,
    checkin: str = DEFAULT_CHECKIN,
    checkout: str = DEFAULT_CHECKOUT,
    scraper: Callable = None,
) -> list[AirbnbListing]:
    """Sample Airbnb listings for a single zone and persist results.

    The scraper parameter accepts the same signature as search_by_bounds and
    defaults to the real implementation. Injecting a fake scraper enables testing.
    """
    if scraper is None:
        scraper = search_by_bounds

    link_zona = zone["link_zona"]

    try:
        listings = scraper(
            ne_lat=zone["ne_lat"],
            ne_lng=zone["ne_lng"],
            sw_lat=zone["sw_lat"],
            sw_lng=zone["sw_lng"],
            checkin=checkin,
            checkout=checkout,
        )
    except Exception as e:
        logger.warning("Scraper failed for zone %s: %s", link_zona, e)
        record_sampling_result(db_path, link_zona, status="failed", listing_count=0)
        return []

    if listings:
        _save_zone_listings(db_path, link_zona, listings)
        status = "completed"
    else:
        status = "no_results"

    record_sampling_result(db_path, link_zona, status=status, listing_count=len(listings))
    logger.info("Zone %s: %s (%d listings)", link_zona, status, len(listings))
    return listings


def _save_zone_listings(db_path: str, link_zona: str, listings: list[AirbnbListing]) -> None:
    """Persist listings associated with a zone, replacing prior results for that zone."""
    conn = sqlite3.connect(db_path)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("DELETE FROM airbnb_listings WHERE link_zona = ?", (link_zona,))
    for listing in listings:
        conn.execute(
            """INSERT INTO airbnb_listings
               (query, link_zona, listing_id, title, name, nightly_rate, total_price,
                nights, latitude, longitude, bedrooms, rating, review_count,
                is_guest_favorite, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                None,
                link_zona,
                listing.listing_id,
                listing.title,
                listing.name,
                listing.nightly_rate,
                listing.total_price,
                listing.nights,
                listing.latitude,
                listing.longitude,
                listing.bedrooms,
                listing.rating,
                listing.review_count,
                int(listing.is_guest_favorite),
                now,
            ),
        )
    conn.commit()
    conn.close()
