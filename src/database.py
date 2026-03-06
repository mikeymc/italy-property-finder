# ABOUTME: Database layer for Airbnb listing cache and scrape job tracking.
# ABOUTME: Provides schema init, listing CRUD, and job state management over SQLite.

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

from src.airbnb_scraper import AirbnbListing


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str) -> None:
    """Create tables if they don't exist."""
    conn = _connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS airbnb_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            listing_id TEXT,
            title TEXT,
            name TEXT,
            nightly_rate REAL,
            total_price REAL,
            nights INTEGER,
            latitude REAL,
            longitude REAL,
            bedrooms INTEGER,
            rating REAL,
            review_count INTEGER,
            is_guest_favorite INTEGER,
            scraped_at TEXT NOT NULL
        )
    """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scrape_jobs (
            id TEXT PRIMARY KEY,
            query TEXT NOT NULL,
            checkin TEXT NOT NULL,
            checkout TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result_count INTEGER,
            error TEXT,
            created_at TEXT NOT NULL
        )
    """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_listings_query ON airbnb_listings(query)"
    )
    conn.commit()
    conn.close()


def save_listings(db_path: str, query: str, listings: list[AirbnbListing]) -> None:
    """Save listings for a query, replacing any previous results for that query."""
    conn = _connect(db_path)
    conn.execute("DELETE FROM airbnb_listings WHERE query = ?", (query,))
    now = datetime.now(timezone.utc).isoformat()
    for listing in listings:
        conn.execute(
            """INSERT INTO airbnb_listings
               (query, listing_id, title, name, nightly_rate, total_price, nights,
                latitude, longitude, bedrooms, rating, review_count, is_guest_favorite, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                query,
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


def get_listings(db_path: str, query: str) -> list[dict]:
    """Get cached listings for a query."""
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT * FROM airbnb_listings WHERE query = ? ORDER BY rating DESC, id",
        (query,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_job(db_path: str, query: str, checkin: str, checkout: str) -> str:
    """Create a new scrape job. Returns the job ID."""
    conn = _connect(db_path)
    job_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO scrape_jobs (id, query, checkin, checkout, status, created_at) VALUES (?, ?, ?, ?, 'pending', ?)",
        (job_id, query, checkin, checkout, now),
    )
    conn.commit()
    conn.close()
    return job_id


def update_job(
    db_path: str,
    job_id: str,
    status: Optional[str] = None,
    result_count: Optional[int] = None,
    error: Optional[str] = None,
) -> None:
    """Update a scrape job's status and/or results."""
    conn = _connect(db_path)
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if result_count is not None:
        updates.append("result_count = ?")
        params.append(result_count)
    if error is not None:
        updates.append("error = ?")
        params.append(error)
    if updates:
        params.append(job_id)
        conn.execute(
            f"UPDATE scrape_jobs SET {', '.join(updates)} WHERE id = ?", params
        )
        conn.commit()
    conn.close()


def get_job(db_path: str, job_id: str) -> Optional[dict]:
    """Get a scrape job by ID."""
    conn = _connect(db_path)
    row = conn.execute("SELECT * FROM scrape_jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None
