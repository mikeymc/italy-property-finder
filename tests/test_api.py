# ABOUTME: Tests for the Flask JSON API endpoints.
# ABOUTME: Uses Flask test client with a small in-memory OMI database fixture.

import json
import sqlite3
import pytest
from unittest.mock import patch

from src.api import create_app
from src.database import init_db


@pytest.fixture
def db_path(tmp_path):
    """Create a test database with OMI tables and sample data."""
    path = str(tmp_path / "test.db")

    # Create OMI tables with sample data
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE omi_values (
            area TEXT, region TEXT, province TEXT, comune_istat TEXT,
            comune_name TEXT, fascia TEXT, zona TEXT, link_zona TEXT,
            property_type_code TEXT, property_type TEXT, condition TEXT,
            buy_min REAL, buy_max REAL, rent_min REAL, rent_max REAL
        )
    """)
    conn.execute("""
        CREATE TABLE omi_zones (
            area TEXT, region TEXT, province TEXT, comune_istat TEXT,
            comune_name TEXT, fascia TEXT, zona TEXT, zona_desc TEXT,
            link_zona TEXT, prevalent_type TEXT, microzona INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO omi_values VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("SUD", "PUGLIA", "BA", "001", "Bari", "C", "B1", "link1", "20", "Abitazioni civili", "NORMALE", 800, 1200, 3.0, 5.0),
            ("SUD", "PUGLIA", "LE", "002", "Lecce", "C", "B2", "link2", "20", "Abitazioni civili", "NORMALE", 600, 900, 2.5, 4.0),
            ("SUD", "SICILIA", "PA", "003", "Palermo", "C", "B3", "link3", "20", "Abitazioni civili", "NORMALE", 500, 800, 2.0, 3.5),
        ],
    )
    conn.executemany(
        "INSERT INTO omi_zones VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("SUD", "PUGLIA", "BA", "001", "Bari", "C", "B1", "Centro storico", "link1", "civili", 1),
            ("SUD", "PUGLIA", "LE", "002", "Lecce", "C", "B2", "Periferia", "link2", "civili", 1),
            ("SUD", "SICILIA", "PA", "003", "Palermo", "C", "B3", "Centro", "link3", "civili", 1),
        ],
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_region ON omi_values(region)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_province ON omi_values(province)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_zones_link ON omi_zones(link_zona)")
    conn.commit()
    conn.close()

    # Init airbnb/scrape tables
    init_db(path)
    return path


@pytest.fixture
def client(db_path):
    app = create_app(db_path)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestZonesEndpoint:
    def test_get_all_zones(self, client):
        resp = client.get("/api/zones")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 3

    def test_filter_by_region(self, client):
        resp = client.get("/api/zones?region=PUGLIA")
        data = resp.get_json()
        assert len(data) == 2
        assert all(z["region"] == "PUGLIA" for z in data)

    def test_filter_by_province(self, client):
        resp = client.get("/api/zones?province=BA")
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["comune_name"] == "Bari"

    def test_filter_by_max_price(self, client):
        resp = client.get("/api/zones?max_price=900")
        data = resp.get_json()
        assert all(z["buy_max"] <= 900 for z in data)

    def test_filter_by_min_rent(self, client):
        resp = client.get("/api/zones?min_rent=2.5")
        data = resp.get_json()
        assert all(z["rent_min"] >= 2.5 for z in data)


class TestRegionsEndpoint:
    def test_get_regions(self, client):
        resp = client.get("/api/zones/regions")
        data = resp.get_json()
        assert data == ["PUGLIA", "SICILIA"]


class TestProvincesEndpoint:
    def test_get_provinces(self, client):
        resp = client.get("/api/zones/provinces?region=PUGLIA")
        data = resp.get_json()
        assert data == ["BA", "LE"]

    def test_missing_region_param(self, client):
        resp = client.get("/api/zones/provinces")
        assert resp.status_code == 400


class TestAnalysisEndpoint:
    def test_basic_analysis(self, client):
        resp = client.get("/api/analysis?purchase_price=100000&square_meters=50&nightly_rate=80&occupancy_rate=0.6")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "annual_cash_flow" in data
        assert "cap_rate" in data
        assert "cash_on_cash_return" in data
        assert "break_even_occupancy" in data
        assert "monthly" in data

    def test_missing_required_params(self, client):
        resp = client.get("/api/analysis")
        assert resp.status_code == 400


class TestScrapeEndpoints:
    def test_start_scrape_job(self, client):
        resp = client.post(
            "/api/scrape/airbnb",
            json={"query": "Rome, Italy", "checkin": "2025-06-01", "checkout": "2025-06-06"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "job_id" in data

    def test_get_job_status(self, client):
        # Create a job first
        resp = client.post(
            "/api/scrape/airbnb",
            json={"query": "Rome", "checkin": "2025-06-01", "checkout": "2025-06-06"},
        )
        job_id = resp.get_json()["job_id"]

        resp = client.get(f"/api/scrape/airbnb/{job_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] in ("pending", "running", "completed", "failed")

    def test_get_nonexistent_job(self, client):
        resp = client.get("/api/scrape/airbnb/nonexistent")
        assert resp.status_code == 404

    def test_start_scrape_missing_params(self, client):
        resp = client.post("/api/scrape/airbnb", json={"query": "Rome"})
        assert resp.status_code == 400


class TestAirbnbListingsEndpoint:
    def test_get_empty_listings(self, client):
        resp = client.get("/api/airbnb-listings?query=Rome")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_missing_query_param(self, client):
        resp = client.get("/api/airbnb-listings")
        assert resp.status_code == 400
