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


def _detect_csv_format(filepath: str) -> tuple[str, bool]:
    """Detect delimiter and whether the file has a title row before headers.

    Returns (delimiter, has_title_row).
    """
    with open(filepath, encoding="utf-8") as f:
        first_line = f.readline()
        second_line = f.readline()
    # If the first line doesn't contain the expected header column, it's a title row
    has_title = "Area_territoriale" not in first_line
    # Check which delimiter the header line uses
    header_line = second_line if has_title else first_line
    delimiter = ";" if ";" in header_line else ","
    return delimiter, has_title


def _open_omi_csv(filepath: str) -> csv.DictReader:
    """Open an OMI CSV file, handling both comma and semicolon formats."""
    delimiter, has_title = _detect_csv_format(filepath)
    f = open(filepath, encoding="utf-8")
    if has_title:
        f.readline()  # Skip title row
    return csv.DictReader(f, delimiter=delimiter)


def load_omi_to_sqlite(valori_csv: str, zone_csv: str, db_path: str) -> None:
    """Load OMI valori and zone CSVs into a SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")

    conn.execute("DROP TABLE IF EXISTS omi_values")
    conn.execute("DROP TABLE IF EXISTS omi_zones")

    conn.execute("""
        CREATE TABLE omi_values (
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
        CREATE TABLE omi_zones (
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
    reader = _open_omi_csv(valori_csv)
    rows = []
    for row in reader:
        # Strip trailing empty keys from semicolon-delimited files
        cod_tip = row.get("Cod_Tip", "").strip()
        if cod_tip not in RESIDENTIAL_TYPES:
            continue
        rows.append((
            row["Area_territoriale"].strip(),
            row["Regione"].strip(),
            row["Prov"].strip(),
            row["Comune_ISTAT"].strip(),
            row["Comune_descrizione"].strip(),
            row["Fascia"].strip(),
            row["Zona"].strip(),
            row["LinkZona"].strip(),
            cod_tip,
            row["Descr_Tipologia"].strip(),
            row["Stato"].strip(),
            parse_italian_float(row["Compr_min"].strip()),
            parse_italian_float(row["Compr_max"].strip()),
            parse_italian_float(row["Loc_min"].strip()),
            parse_italian_float(row["Loc_max"].strip()),
        ))

    conn.executemany(
        "INSERT INTO omi_values VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )

    # Load zones
    reader = _open_omi_csv(zone_csv)
    zone_rows = []
    for row in reader:
        zone_rows.append((
            row["Area_territoriale"].strip(),
            row["Regione"].strip(),
            row["Prov"].strip(),
            row["Comune_ISTAT"].strip(),
            row["Comune_descrizione"].strip(),
            row["Fascia"].strip(),
            row["Zona"].strip(),
            row.get("Zona_Descr", "").strip(),
            row["LinkZona"].strip(),
            row.get("Descr_tip_prev", "").strip(),
            int(row.get("Microzona", "0").strip() or 0),
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


def get_regions(db_path: str) -> list[str]:
    """Return sorted list of distinct regions in the OMI database."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT DISTINCT region FROM omi_values ORDER BY region").fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_provinces(db_path: str, region: str) -> list[str]:
    """Return sorted list of distinct provinces for a region."""
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT province FROM omi_values WHERE region = ? ORDER BY province",
        (region,),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


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
               v.buy_min, v.buy_max, v.rent_min, v.rent_max,
               v.link_zona
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
