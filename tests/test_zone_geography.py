# ABOUTME: Tests for zone geography module that computes bounding boxes from geojson.
# ABOUTME: Validates bbox computation, geojson parsing, and SQLite storage.

import pytest
import sqlite3
import tempfile
import os

from src.zone_geography import compute_bbox, parse_zone_name, load_zone_bboxes


class TestComputeBbox:
    def test_simple_polygon(self):
        # A simple square polygon
        coords = [[0.0, 0.0], [0.0, 1.0], [1.0, 1.0], [1.0, 0.0], [0.0, 0.0]]
        bbox = compute_bbox(coords)
        assert bbox == (1.0, 1.0, 0.0, 0.0)  # (ne_lat, ne_lng, sw_lat, sw_lng)

    def test_real_coordinates(self):
        # Coordinates around Naples area
        coords = [
            [14.2, 40.8], [14.3, 40.8], [14.3, 40.9], [14.2, 40.9], [14.2, 40.8]
        ]
        bbox = compute_bbox(coords)
        assert bbox[0] == pytest.approx(40.9)  # ne_lat
        assert bbox[1] == pytest.approx(14.3)  # ne_lng
        assert bbox[2] == pytest.approx(40.8)  # sw_lat
        assert bbox[3] == pytest.approx(14.2)  # sw_lng

    def test_irregular_polygon(self):
        coords = [[10.0, 44.0], [10.5, 43.8], [11.0, 44.2], [10.3, 44.5], [10.0, 44.0]]
        bbox = compute_bbox(coords)
        assert bbox[0] == pytest.approx(44.5)   # ne_lat = max lat
        assert bbox[1] == pytest.approx(11.0)   # ne_lng = max lng
        assert bbox[2] == pytest.approx(43.8)   # sw_lat = min lat
        assert bbox[3] == pytest.approx(10.0)   # sw_lng = min lng


class TestParseZoneName:
    def test_standard_format(self):
        comune, zona = parse_zone_name("VILLAREGGIA - Zona OMI R1")
        assert comune == "VILLAREGGIA"
        assert zona == "R1"

    def test_multi_word_comune(self):
        comune, zona = parse_zone_name("LA SALLE - Zona OMI D1")
        assert comune == "LA SALLE"
        assert zona == "D1"

    def test_returns_none_for_invalid(self):
        comune, zona = parse_zone_name("something unexpected")
        assert comune is None
        assert zona is None


class TestLoadZoneBboxes:
    SAMPLE_GEOJSON = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"zona": "X001", "name": "TESTVILLE - Zona OMI B1"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[14.1, 40.7], [14.3, 40.7], [14.3, 40.9], [14.1, 40.9], [14.1, 40.7]]
                    ]
                }
            }
        ]
    }

    def test_stores_bbox_for_matched_zone(self, tmp_path):
        import json

        geojson_path = tmp_path / "zones.geojson"
        geojson_path.write_text(json.dumps(self.SAMPLE_GEOJSON))

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE omi_zones (
                link_zona TEXT,
                comune_name TEXT,
                zona TEXT,
                ne_lat REAL, ne_lng REAL, sw_lat REAL, sw_lng REAL
            )
        """)
        conn.execute(
            "INSERT INTO omi_zones (link_zona, comune_name, zona) VALUES (?, ?, ?)",
            ("TT00000001", "TESTVILLE", "B1"),
        )
        conn.commit()
        conn.close()

        load_zone_bboxes(str(geojson_path), db_path)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT ne_lat, ne_lng, sw_lat, sw_lng FROM omi_zones WHERE link_zona = ?",
            ("TT00000001",)
        ).fetchone()
        conn.close()

        assert row is not None
        assert row[0] == pytest.approx(40.9)  # ne_lat
        assert row[1] == pytest.approx(14.3)  # ne_lng
        assert row[2] == pytest.approx(40.7)  # sw_lat
        assert row[3] == pytest.approx(14.1)  # sw_lng

    def test_skips_unmatched_zones(self, tmp_path):
        import json

        geojson_path = tmp_path / "zones.geojson"
        geojson_path.write_text(json.dumps(self.SAMPLE_GEOJSON))

        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE omi_zones (
                link_zona TEXT,
                comune_name TEXT,
                zona TEXT,
                ne_lat REAL, ne_lng REAL, sw_lat REAL, sw_lng REAL
            )
        """)
        # Different comune — should not get a bbox
        conn.execute(
            "INSERT INTO omi_zones (link_zona, comune_name, zona) VALUES (?, ?, ?)",
            ("TT00000002", "OTHERTOWN", "B1"),
        )
        conn.commit()
        conn.close()

        load_zone_bboxes(str(geojson_path), db_path)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT ne_lat FROM omi_zones WHERE link_zona = ?", ("TT00000002",)
        ).fetchone()
        conn.close()
        assert row[0] is None
