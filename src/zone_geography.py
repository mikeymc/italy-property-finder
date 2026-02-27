# ABOUTME: Computes geographic bounding boxes for OMI zones from a GeoJSON file.
# ABOUTME: Parses zone polygons once and stores bbox coords in the omi_zones table.

import json
import logging
import re
import sqlite3
from typing import Optional

logger = logging.getLogger(__name__)


def compute_bbox(coords: list[list[float]]) -> tuple[float, float, float, float]:
    """Compute bounding box from a list of [lng, lat] coordinate pairs.

    Returns (ne_lat, ne_lng, sw_lat, sw_lng).
    """
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return max(lats), max(lngs), min(lats), min(lngs)


def parse_zone_name(name: str) -> tuple[Optional[str], Optional[str]]:
    """Parse a GeoJSON zone name like 'COMUNE - Zona OMI X1' into (comune, zona)."""
    match = re.match(r"^(.+) - Zona OMI (.+)$", name)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None


def load_zone_bboxes(geojson_path: str, db_path: str) -> int:
    """Parse the zones GeoJSON and write bounding boxes into omi_zones.

    Adds ne_lat, ne_lng, sw_lat, sw_lng columns if absent, then updates rows
    where the geojson feature name matches (comune_name, zona) in the DB.

    Returns the number of zones updated.
    """
    conn = sqlite3.connect(db_path)

    # Add bbox columns if they don't exist yet
    existing_cols = {
        row[1] for row in conn.execute("PRAGMA table_info(omi_zones)").fetchall()
    }
    for col in ("ne_lat", "ne_lng", "sw_lat", "sw_lng"):
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE omi_zones ADD COLUMN {col} REAL")

    # Build a lookup: (comune_name, zona) -> link_zona
    lookup: dict[tuple[str, str], str] = {}
    for row in conn.execute("SELECT link_zona, comune_name, zona FROM omi_zones"):
        lookup[(row[1], row[2])] = row[0]

    with open(geojson_path, encoding="utf-8") as f:
        data = json.load(f)

    updated = 0
    for feature in data["features"]:
        name = feature.get("properties", {}).get("name", "")
        comune, zona = parse_zone_name(name)
        if not comune or not zona:
            continue

        link_zona = lookup.get((comune, zona))
        if not link_zona:
            continue

        geometry = feature.get("geometry", {})
        if geometry.get("type") != "Polygon":
            continue

        # GeoJSON Polygon: coordinates is a list of rings; first ring is exterior
        ring = geometry["coordinates"][0]
        ne_lat, ne_lng, sw_lat, sw_lng = compute_bbox(ring)

        conn.execute(
            """UPDATE omi_zones
               SET ne_lat = ?, ne_lng = ?, sw_lat = ?, sw_lng = ?
               WHERE link_zona = ?""",
            (ne_lat, ne_lng, sw_lat, sw_lng, link_zona),
        )
        updated += 1

    conn.commit()
    conn.close()
    logger.info("Updated bounding boxes for %d zones", updated)
    return updated
