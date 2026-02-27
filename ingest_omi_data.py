# ABOUTME: One-time data import script for OMI property data and zone bounding boxes.
# ABOUTME: Loads CSV data into SQLite, then computes zone bboxes from zones.geojson.

import os
from src.omi_data import load_omi_to_sqlite
from src.zone_geography import load_zone_bboxes

DB_PATH = os.environ.get("DB_PATH", "data/real_estate.db")

VALORI_CSV = "data/QI_20251_VALORI.csv"
ZONE_CSV = "data/QI_20251_ZONE.csv"
ZONES_GEOJSON = "frontend/public/zones.geojson"


def main():
    print(f"Loading OMI data from {VALORI_CSV} and {ZONE_CSV} into {DB_PATH}...")
    load_omi_to_sqlite(valori_csv=VALORI_CSV, zone_csv=ZONE_CSV, db_path=DB_PATH)
    print("OMI data loaded.")

    print(f"Computing zone bounding boxes from {ZONES_GEOJSON}...")
    updated = load_zone_bboxes(geojson_path=ZONES_GEOJSON, db_path=DB_PATH)
    print(f"Bounding boxes computed for {updated} zones.")


if __name__ == "__main__":
    main()
