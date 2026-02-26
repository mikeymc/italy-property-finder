import os
from src.omi_data import load_omi_to_sqlite

DB_PATH = os.environ.get("DB_PATH", "data/real_estate.db")

VALORI_CSV = "data/QI_20251_VALORI.csv"
ZONE_CSV = "data/QI_20251_ZONE.csv"


def main():
    print(f"Loading OMI data from {VALORI_CSV} and {ZONE_CSV} into {DB_PATH}...")
    load_omi_to_sqlite(valori_csv=VALORI_CSV, zone_csv=ZONE_CSV, db_path=DB_PATH)
    print("Successfully loaded.")


if __name__ == "__main__":
    main()
