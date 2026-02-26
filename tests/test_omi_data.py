# ABOUTME: Tests for OMI data parsing and loading into SQLite.
# ABOUTME: Validates Italian number format handling, filtering, and database schema.

import os
import sqlite3
import tempfile

import pytest

from src.omi_data import parse_italian_float, load_omi_to_sqlite, query_zones, get_regions, get_provinces


class TestItalianNumberParsing:
    def test_comma_decimal(self):
        assert parse_italian_float("5,1") == 5.1

    def test_integer(self):
        assert parse_italian_float("810") == 810.0

    def test_large_number(self):
        assert parse_italian_float("1200") == 1200.0

    def test_empty_returns_none(self):
        assert parse_italian_float("") is None

    def test_none_returns_none(self):
        assert parse_italian_float(None) is None


class TestLoadOMI:
    @pytest.fixture
    def db_path(self, tmp_path):
        return str(tmp_path / "test_omi.db")

    @pytest.fixture
    def loaded_db(self, db_path):
        valori = os.path.join(os.path.dirname(__file__), "..", "data", "valori_2018h2.csv")
        zone = os.path.join(os.path.dirname(__file__), "..", "data", "zone_2018h2.csv")
        if not os.path.exists(valori):
            pytest.skip("OMI data files not downloaded")
        load_omi_to_sqlite(valori, zone, db_path)
        return db_path

    def test_creates_database(self, loaded_db):
        assert os.path.exists(loaded_db)

    def test_residential_rows_loaded(self, loaded_db):
        conn = sqlite3.connect(loaded_db)
        count = conn.execute("SELECT COUNT(*) FROM omi_values").fetchone()[0]
        conn.close()
        # Should have all residential types
        assert count > 40_000

    def test_zones_loaded(self, loaded_db):
        conn = sqlite3.connect(loaded_db)
        count = conn.execute("SELECT COUNT(*) FROM omi_zones").fetchone()[0]
        conn.close()
        assert count > 20_000

    def test_numeric_values_parsed(self, loaded_db):
        conn = sqlite3.connect(loaded_db)
        row = conn.execute(
            "SELECT buy_min, buy_max, rent_min, rent_max FROM omi_values LIMIT 1"
        ).fetchone()
        conn.close()
        # All should be numeric (not strings with commas)
        for val in row:
            assert isinstance(val, (int, float))
            assert val > 0

    def test_rent_values_are_monthly_per_sqm(self, loaded_db):
        conn = sqlite3.connect(loaded_db)
        row = conn.execute(
            "SELECT rent_min, rent_max FROM omi_values WHERE property_type = 'Abitazioni civili' LIMIT 1"
        ).fetchone()
        conn.close()
        # Monthly rent per sqm should be reasonable: €1-50 range
        assert 0.5 < row[0] < 100
        assert 0.5 < row[1] < 100


@pytest.fixture
def small_db(tmp_path):
    """A small OMI database for testing helpers without real data files."""
    db_path = str(tmp_path / "small_omi.db")
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE omi_values (
            area TEXT, region TEXT, province TEXT, comune_istat TEXT,
            comune_name TEXT, fascia TEXT, zona TEXT, link_zona TEXT,
            property_type_code TEXT, property_type TEXT, condition TEXT,
            buy_min REAL, buy_max REAL, rent_min REAL, rent_max REAL
        )
    """)
    conn.executemany(
        "INSERT INTO omi_values VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            ("SUD", "PUGLIA", "BA", "001", "Bari", "C", "B1", "link1", "20", "Abitazioni civili", "NORMALE", 800, 1200, 3.0, 5.0),
            ("SUD", "PUGLIA", "LE", "002", "Lecce", "C", "B2", "link2", "20", "Abitazioni civili", "NORMALE", 600, 900, 2.5, 4.0),
            ("SUD", "SICILIA", "PA", "003", "Palermo", "C", "B3", "link3", "20", "Abitazioni civili", "NORMALE", 500, 800, 2.0, 3.5),
            ("NORD", "LOMBARDIA", "MI", "004", "Milano", "C", "B4", "link4", "20", "Abitazioni civili", "NORMALE", 2000, 4000, 8.0, 15.0),
        ],
    )
    conn.commit()
    conn.close()
    return db_path


class TestGetRegions:
    def test_returns_distinct_sorted_regions(self, small_db):
        regions = get_regions(small_db)
        assert regions == ["LOMBARDIA", "PUGLIA", "SICILIA"]

    def test_empty_db(self, tmp_path):
        db_path = str(tmp_path / "empty.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE omi_values (
                area TEXT, region TEXT, province TEXT, comune_istat TEXT,
                comune_name TEXT, fascia TEXT, zona TEXT, link_zona TEXT,
                property_type_code TEXT, property_type TEXT, condition TEXT,
                buy_min REAL, buy_max REAL, rent_min REAL, rent_max REAL
            )
        """)
        conn.commit()
        conn.close()
        assert get_regions(db_path) == []


class TestGetProvinces:
    def test_returns_provinces_for_region(self, small_db):
        provinces = get_provinces(small_db, "PUGLIA")
        assert provinces == ["BA", "LE"]

    def test_unknown_region_returns_empty(self, small_db):
        assert get_provinces(small_db, "NOWHERE") == []


class TestQueryZones:
    @pytest.fixture
    def loaded_db(self, tmp_path):
        db_path = str(tmp_path / "test_omi.db")
        valori = os.path.join(os.path.dirname(__file__), "..", "data", "valori_2018h2.csv")
        zone = os.path.join(os.path.dirname(__file__), "..", "data", "zone_2018h2.csv")
        if not os.path.exists(valori):
            pytest.skip("OMI data files not downloaded")
        load_omi_to_sqlite(valori, zone, db_path)
        return db_path

    def test_query_by_region(self, loaded_db):
        results = query_zones(loaded_db, region="PUGLIA")
        assert len(results) > 0
        for r in results:
            assert r["region"] == "PUGLIA"

    def test_query_by_max_buy_price(self, loaded_db):
        results = query_zones(loaded_db, max_buy_price_sqm=1000)
        assert len(results) > 0
        for r in results:
            assert r["buy_max"] <= 1000

    def test_query_returns_rent_data(self, loaded_db):
        results = query_zones(loaded_db, region="SICILIA", max_buy_price_sqm=1500)
        assert len(results) > 0
        for r in results:
            assert "rent_min" in r
            assert "rent_max" in r
