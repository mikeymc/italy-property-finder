# ABOUTME: Tests for the zone sampling orchestrator.
# ABOUTME: Validates zone selection, status tracking, and listing association.

import sqlite3
import pytest

from src.zone_sampler import (
    init_sampling_tables,
    get_zones_to_sample,
    record_sampling_result,
    sample_zone,
)
from src.airbnb_scraper import AirbnbListing


def make_db(tmp_path):
    """Create a minimal test database with omi_zones and required tables."""
    db_path = str(tmp_path / "test.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE omi_zones (
            link_zona TEXT PRIMARY KEY,
            region TEXT,
            province TEXT,
            comune_name TEXT,
            zona TEXT,
            ne_lat REAL, ne_lng REAL, sw_lat REAL, sw_lng REAL
        )
    """)
    conn.execute("""
        CREATE TABLE airbnb_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            link_zona TEXT,
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
    """)
    conn.executemany(
        "INSERT INTO omi_zones VALUES (?,?,?,?,?,?,?,?,?)",
        [
            ("SA00000001", "CAMPANIA", "SA", "AMALFI", "B1", 40.64, 14.61, 40.62, 14.59),
            ("SA00000002", "CAMPANIA", "SA", "AMALFI", "C1", 40.65, 14.62, 40.63, 14.60),
            ("NA00000001", "CAMPANIA", "NA", "NAPOLI", "A1", 40.87, 14.28, 40.85, 14.26),
            # Zone with no bbox — should be skipped
            ("NA00000002", "CAMPANIA", "NA", "NAPOLI", "B1", None, None, None, None),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


class TestInitSamplingTables:
    def test_creates_zone_sampling_status_table(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE omi_zones (link_zona TEXT)")
        conn.commit()
        conn.close()

        init_sampling_tables(db_path)

        conn = sqlite3.connect(db_path)
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        assert "zone_sampling_status" in tables

    def test_idempotent(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE omi_zones (link_zona TEXT)")
        conn.commit()
        conn.close()

        init_sampling_tables(db_path)
        init_sampling_tables(db_path)  # Should not raise


class TestGetZonesToSample:
    def test_returns_zones_with_bbox(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        zones = get_zones_to_sample(db_path)
        link_zonas = [z["link_zona"] for z in zones]
        assert "SA00000001" in link_zonas
        assert "SA00000002" in link_zonas
        assert "NA00000001" in link_zonas

    def test_skips_zones_without_bbox(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        zones = get_zones_to_sample(db_path)
        link_zonas = [z["link_zona"] for z in zones]
        assert "NA00000002" not in link_zonas

    def test_filters_by_province(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        zones = get_zones_to_sample(db_path, province="SA")
        assert all(z["province"] == "SA" for z in zones)
        assert len(zones) == 2

    def test_skips_already_sampled_zones(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)
        record_sampling_result(db_path, "SA00000001", status="completed", listing_count=5)

        zones = get_zones_to_sample(db_path)
        link_zonas = [z["link_zona"] for z in zones]
        assert "SA00000001" not in link_zonas


class TestRecordSamplingResult:
    def test_records_completed_status(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        record_sampling_result(db_path, "SA00000001", status="completed", listing_count=10)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT status, listing_count FROM zone_sampling_status WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert row[0] == "completed"
        assert row[1] == 10

    def test_records_failed_status(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        record_sampling_result(db_path, "SA00000001", status="failed", listing_count=0)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT status FROM zone_sampling_status WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert row[0] == "failed"


class TestSampleZone:
    def _make_listing(self, listing_id="1"):
        return AirbnbListing(
            listing_id=listing_id,
            title="Test",
            name="Test listing",
            nightly_rate=100.0,
            latitude=40.63,
            longitude=14.60,
        )

    def test_calls_scraper_with_bbox(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        calls = []
        def fake_scraper(ne_lat, ne_lng, sw_lat, sw_lng, checkin, checkout, **kwargs):
            calls.append({"ne_lat": ne_lat, "ne_lng": ne_lng, "sw_lat": sw_lat, "sw_lng": sw_lng})
            return [self._make_listing()]

        zone = {"link_zona": "SA00000001", "ne_lat": 40.64, "ne_lng": 14.61, "sw_lat": 40.62, "sw_lng": 14.59}
        sample_zone(db_path, zone, scraper=fake_scraper, checkin="2025-06-01", checkout="2025-06-06")

        assert len(calls) == 1
        assert calls[0]["ne_lat"] == pytest.approx(40.64)

    def test_stores_listings_with_link_zona(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        def fake_scraper(**kwargs):
            return [self._make_listing("listing-abc")]

        zone = {"link_zona": "SA00000001", "ne_lat": 40.64, "ne_lng": 14.61, "sw_lat": 40.62, "sw_lng": 14.59}
        sample_zone(db_path, zone, scraper=fake_scraper, checkin="2025-06-01", checkout="2025-06-06")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT link_zona, listing_id FROM airbnb_listings WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "SA00000001"
        assert row[1] == "listing-abc"

    def test_records_sampling_status(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        def fake_scraper(**kwargs):
            return [self._make_listing()]

        zone = {"link_zona": "SA00000001", "ne_lat": 40.64, "ne_lng": 14.61, "sw_lat": 40.62, "sw_lng": 14.59}
        sample_zone(db_path, zone, scraper=fake_scraper, checkin="2025-06-01", checkout="2025-06-06")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT status, listing_count FROM zone_sampling_status WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert row[0] == "completed"
        assert row[1] == 1

    def test_records_no_results_status(self, tmp_path):
        db_path = make_db(tmp_path)
        init_sampling_tables(db_path)

        def fake_scraper(**kwargs):
            return []

        zone = {"link_zona": "SA00000001", "ne_lat": 40.64, "ne_lng": 14.61, "sw_lat": 40.62, "sw_lng": 14.59}
        sample_zone(db_path, zone, scraper=fake_scraper, checkin="2025-06-01", checkout="2025-06-06")

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT status FROM zone_sampling_status WHERE link_zona = ?",
            ("SA00000001",)
        ).fetchone()
        conn.close()
        assert row[0] == "no_results"
