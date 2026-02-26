# ABOUTME: Parses OMI (Osservatorio del Mercato Immobiliare) CSV data from Agenzia delle Entrate.
# ABOUTME: Loads property values and zone definitions into SQLite for analysis.

import csv
import sqlite3
from typing import Optional

# OMI residential property type codes
RESIDENTIAL_TYPES = {"20", "21", "22", "23"}  # civili, economiche, signorili, tipiche


def parse_italian_float(value: Optional[str]) -> Optional[float]:
    """Parse Italian-format numbers (comma as decimal separator)."""
    if not value:
        return None
    return float(value.replace(",", "."))


def load_omi_to_sqlite(valori_csv: str, zone_csv: str, db_path: str) -> None:
    """Load OMI valori and zone CSVs into a SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS omi_values (
            area TEXT,
            region TEXT,
            province TEXT,
            comune_istat TEXT,
            comune_name TEXT,
            fascia TEXT,
            zona TEXT,
            link_zona TEXT,
            property_type_code TEXT,
            property_type TEXT,
            condition TEXT,
            buy_min REAL,
            buy_max REAL,
            rent_min REAL,
            rent_max REAL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS omi_zones (
            area TEXT,
            region TEXT,
            province TEXT,
            comune_istat TEXT,
            comune_name TEXT,
            fascia TEXT,
            zona TEXT,
            zona_desc TEXT,
            link_zona TEXT,
            prevalent_type TEXT,
            microzona INTEGER
        )
    """)

    # Load values (residential only)
    with open(valori_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            if row["Cod_Tip"] not in RESIDENTIAL_TYPES:
                continue
            rows.append((
                row["Area_territoriale"],
                row["Regione"],
                row["Prov"],
                row["Comune_ISTAT"],
                row["Comune_descrizione"],
                row["Fascia"],
                row["Zona"],
                row["LinkZona"],
                row["Cod_Tip"],
                row["Descr_Tipologia"],
                row["Stato"],
                parse_italian_float(row["Compr_min"]),
                parse_italian_float(row["Compr_max"]),
                parse_italian_float(row["Loc_min"]),
                parse_italian_float(row["Loc_max"]),
            ))

    conn.executemany(
        "INSERT INTO omi_values VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )

    # Load zones
    with open(zone_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        zone_rows = []
        for row in reader:
            zone_rows.append((
                row["Area_territoriale"],
                row["Regione"],
                row["Prov"],
                row["Comune_ISTAT"],
                row["Comune_descrizione"],
                row["Fascia"],
                row["Zona"],
                row.get("Zona_Descr", ""),
                row["LinkZona"],
                row.get("Descr_tip_prev", ""),
                int(row.get("Microzona", 0) or 0),
            ))

    conn.executemany(
        "INSERT INTO omi_zones VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        zone_rows,
    )

    # Create indexes for common queries
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_region ON omi_values(region)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_province ON omi_values(province)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_comune ON omi_values(comune_istat)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_values_type ON omi_values(property_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_zones_link ON omi_zones(link_zona)")

    conn.commit()
    conn.close()


def query_zones(
    db_path: str,
    region: Optional[str] = None,
    province: Optional[str] = None,
    max_buy_price_sqm: Optional[float] = None,
    min_rent_sqm: Optional[float] = None,
    property_type: str = "Abitazioni civili",
    condition: str = "NORMALE",
) -> list[dict]:
    """Query OMI zones matching criteria. Returns dicts with zone + value info."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT v.region, v.province, v.comune_name, v.zona,
               z.zona_desc, v.property_type, v.condition,
               v.buy_min, v.buy_max, v.rent_min, v.rent_max
        FROM omi_values v
        LEFT JOIN omi_zones z ON v.link_zona = z.link_zona
        WHERE v.property_type = ? AND v.condition = ?
    """
    params: list = [property_type, condition]

    if region:
        query += " AND v.region = ?"
        params.append(region)
    if province:
        query += " AND v.province = ?"
        params.append(province)
    if max_buy_price_sqm is not None:
        query += " AND v.buy_max <= ?"
        params.append(max_buy_price_sqm)
    if min_rent_sqm is not None:
        query += " AND v.rent_min >= ?"
        params.append(min_rent_sqm)

    query += " ORDER BY v.buy_min ASC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]
