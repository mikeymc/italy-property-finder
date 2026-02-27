# ABOUTME: Tests for per-zone STR metric aggregation.
# ABOUTME: Validates median rate calculation, listing aggregation, and storage.

import sqlite3
import pytest
from datetime import datetime, timezone

from src.str_metrics import compute_zone_metrics, update_zone_str_metrics, init_str_metrics_table


def make_db_with_listings(tmp_path, listings_data):
    """Create a test DB with airbnb_listings pre-populated."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE airbnb_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            link_zona TEXT,
            listing_id TEXT,
            nightly_rate REAL,
            bedrooms INTEGER,
            rating REAL,
            review_count INTEGER,
            is_guest_favorite INTEGER,
            scraped_at TEXT NOT NULL
        )
    """)
    now = datetime.now(timezone.utc).isoformat()
    for row in listings_data:
        conn.execute(
            "INSERT INTO airbnb_listings (link_zona, listing_id, nightly_rate, bedrooms, rating, scraped_at) VALUES (?,?,?,?,?,?)",
            (*row, now),
        )
    conn.commit()
    conn.close()
    return db_path


class TestComputeZoneMetrics:
    def test_median_nightly_rate_odd_count(self):
        rates = [100.0, 120.0, 80.0, 150.0, 90.0]
        listings = [{"nightly_rate": r, "bedrooms": 2, "rating": 4.5} for r in rates]
        metrics = compute_zone_metrics(listings)
        assert metrics["median_nightly_rate"] == pytest.approx(100.0)

    def test_median_nightly_rate_even_count(self):
        rates = [80.0, 100.0, 120.0, 140.0]
        listings = [{"nightly_rate": r, "bedrooms": 2, "rating": 4.5} for r in rates]
        metrics = compute_zone_metrics(listings)
        assert metrics["median_nightly_rate"] == pytest.approx(110.0)

    def test_listing_count(self):
        listings = [{"nightly_rate": 100.0, "bedrooms": 2, "rating": 4.5}] * 7
        metrics = compute_zone_metrics(listings)
        assert metrics["listing_count"] == 7

    def test_avg_bedrooms(self):
        listings = [
            {"nightly_rate": 100.0, "bedrooms": 1, "rating": 4.0},
            {"nightly_rate": 100.0, "bedrooms": 2, "rating": 4.0},
            {"nightly_rate": 100.0, "bedrooms": 3, "rating": 4.0},
        ]
        metrics = compute_zone_metrics(listings)
        assert metrics["avg_bedrooms"] == pytest.approx(2.0)

    def test_avg_rating(self):
        listings = [
            {"nightly_rate": 100.0, "bedrooms": 2, "rating": 4.0},
            {"nightly_rate": 100.0, "bedrooms": 2, "rating": 5.0},
        ]
        metrics = compute_zone_metrics(listings)
        assert metrics["avg_rating"] == pytest.approx(4.5)

    def test_ignores_null_nightly_rates_for_median(self):
        listings = [
            {"nightly_rate": None, "bedrooms": 2, "rating": 4.5},
            {"nightly_rate": 100.0, "bedrooms": 2, "rating": 4.5},
            {"nightly_rate": 200.0, "bedrooms": 2, "rating": 4.5},
        ]
        metrics = compute_zone_metrics(listings)
        assert metrics["median_nightly_rate"] == pytest.approx(150.0)
        assert metrics["listing_count"] == 3

    def test_ignores_null_bedrooms_for_avg(self):
        listings = [
            {"nightly_rate": 100.0, "bedrooms": None, "rating": 4.5},
            {"nightly_rate": 100.0, "bedrooms": 2, "rating": 4.5},
            {"nightly_rate": 100.0, "bedrooms": 4, "rating": 4.5},
        ]
        metrics = compute_zone_metrics(listings)
        assert metrics["avg_bedrooms"] == pytest.approx(3.0)

    def test_returns_none_for_empty(self):
        metrics = compute_zone_metrics([])
        assert metrics is None


class TestUpdateZoneStrMetrics:
    def test_computes_and_stores_metrics(self, tmp_path):
        db_path = make_db_with_listings(tmp_path, [
            ("SA00000001", "L1", 100.0, 2, 4.5),
            ("SA00000001", "L2", 120.0, 3, 4.8),
            ("SA00000001", "L3", 80.0, 1, 4.2),
        ])
        init_str_metrics_table(db_path)

        update_zone_str_metrics(db_path, "SA00000001")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT median_nightly_rate, listing_count, avg_bedrooms, avg_rating FROM zone_str_metrics WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == pytest.approx(100.0)  # median of [80, 100, 120]
        assert row[1] == 3
        assert row[2] == pytest.approx(2.0)
        assert row[3] == pytest.approx(4.5)

    def test_replaces_existing_metrics(self, tmp_path):
        db_path = make_db_with_listings(tmp_path, [
            ("SA00000001", "L1", 50.0, 1, 4.0),
        ])
        init_str_metrics_table(db_path)
        update_zone_str_metrics(db_path, "SA00000001")

        # Now add more listings and recompute
        conn = sqlite3.connect(db_path)
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO airbnb_listings (link_zona, listing_id, nightly_rate, bedrooms, rating, scraped_at) VALUES (?,?,?,?,?,?)",
            ("SA00000001", "L2", 150.0, 2, 4.8, now),
        )
        conn.commit()
        conn.close()

        update_zone_str_metrics(db_path, "SA00000001")

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT COUNT(*) FROM zone_str_metrics WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert rows[0] == 1  # Only one row, updated in place

    def test_no_op_for_zone_with_no_listings(self, tmp_path):
        db_path = make_db_with_listings(tmp_path, [])
        init_str_metrics_table(db_path)

        update_zone_str_metrics(db_path, "SA99999999")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT * FROM zone_str_metrics WHERE link_zona = ?", ("SA99999999",)
        ).fetchone()
        conn.close()
        assert row is None
