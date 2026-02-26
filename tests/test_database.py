# ABOUTME: Tests for the database layer (airbnb_listings and scrape_jobs tables).
# ABOUTME: Validates schema creation, listing CRUD, and job state tracking.

import sqlite3
import pytest
from src.database import init_db, save_listings, get_listings, create_job, update_job, get_job
from src.airbnb_scraper import AirbnbListing


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _sample_listing(**overrides):
    defaults = dict(
        listing_id="123",
        title="Cozy Flat",
        name="Cozy Flat in Rome",
        nightly_rate=80.0,
        total_price=400.0,
        nights=5,
        latitude=41.9,
        longitude=12.5,
        bedrooms=2,
        rating=4.5,
        review_count=100,
        is_guest_favorite=False,
    )
    defaults.update(overrides)
    return AirbnbListing(**defaults)


class TestInitDb:
    def test_creates_tables(self, db_path):
        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        assert "airbnb_listings" in tables
        assert "scrape_jobs" in tables
        conn.close()

    def test_idempotent(self, db_path):
        # Calling init_db again should not error
        init_db(db_path)


class TestListings:
    def test_save_and_get(self, db_path):
        listings = [_sample_listing(), _sample_listing(listing_id="456", title="Beach House")]
        save_listings(db_path, "Rome, Italy", listings)

        results = get_listings(db_path, "Rome, Italy")
        assert len(results) == 2
        assert results[0]["listing_id"] == "123"
        assert results[1]["listing_id"] == "456"

    def test_get_empty(self, db_path):
        results = get_listings(db_path, "Nowhere")
        assert results == []

    def test_save_overwrites_same_query(self, db_path):
        save_listings(db_path, "Rome", [_sample_listing()])
        save_listings(db_path, "Rome", [_sample_listing(listing_id="999")])
        results = get_listings(db_path, "Rome")
        assert len(results) == 1
        assert results[0]["listing_id"] == "999"

    def test_different_queries_independent(self, db_path):
        save_listings(db_path, "Rome", [_sample_listing()])
        save_listings(db_path, "Milan", [_sample_listing(listing_id="456")])
        assert len(get_listings(db_path, "Rome")) == 1
        assert len(get_listings(db_path, "Milan")) == 1

    def test_handles_none_fields(self, db_path):
        listing = _sample_listing(nightly_rate=None, latitude=None)
        save_listings(db_path, "Rome", [listing])
        results = get_listings(db_path, "Rome")
        assert results[0]["nightly_rate"] is None


class TestJobs:
    def test_create_and_get(self, db_path):
        job_id = create_job(db_path, "Rome, Italy", "2025-06-01", "2025-06-06")
        job = get_job(db_path, job_id)
        assert job["status"] == "pending"
        assert job["query"] == "Rome, Italy"

    def test_update_status(self, db_path):
        job_id = create_job(db_path, "Rome", "2025-06-01", "2025-06-06")
        update_job(db_path, job_id, status="running")
        assert get_job(db_path, job_id)["status"] == "running"

    def test_update_with_result_count(self, db_path):
        job_id = create_job(db_path, "Rome", "2025-06-01", "2025-06-06")
        update_job(db_path, job_id, status="completed", result_count=42)
        job = get_job(db_path, job_id)
        assert job["status"] == "completed"
        assert job["result_count"] == 42

    def test_update_with_error(self, db_path):
        job_id = create_job(db_path, "Rome", "2025-06-01", "2025-06-06")
        update_job(db_path, job_id, status="failed", error="timeout")
        job = get_job(db_path, job_id)
        assert job["status"] == "failed"
        assert job["error"] == "timeout"

    def test_get_nonexistent_returns_none(self, db_path):
        assert get_job(db_path, "nonexistent") is None
