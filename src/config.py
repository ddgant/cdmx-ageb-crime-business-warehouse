"""Shared paths and settings for the Mexico City (CDMX) Urban Intelligence pipeline."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
DOCS_QA = ROOT / "docs" / "qa"
SQL = ROOT / "sql"
for _p in (PROC, DOCS_QA):
    _p.mkdir(parents=True, exist_ok=True)

# Study area: urban AGEBs of Mexico City (entity 09, 16 alcaldias)
ENT_CODE = "09"
CRIME_YEAR = 2024          # year of the incident date (fecha_hecho)
METRIC_EPSG = 32614        # UTM zone 14N, used for areas

# Raw files (see README for download links and expected layout)
CENSUS_CSV = RAW / "census" / "RESAGEBURB_09CSV20.csv"
AGEB_SHP = RAW / "mg2020" / "ageb_urbano" / "2020_1_09_A.shp"
AGEE_SHP = RAW / "mg2020" / "agee" / "2020_1_09_ENT.shp"
DENUE_EDITION = "ed1124"   # DENUE 11/2024, same year as the crime data
DENUE_CSV = RAW / "denue" / DENUE_EDITION / "conjunto_de_datos" / "denue_inegi_09_.csv"
CRIME_CSV = RAW / "crime" / "carpetasFGJ_acumulado_2025_01.csv"  # FGJ CDMX, datos.cdmx.gob.mx

# Processed outputs
CENSUS_PQ = PROC / "census_ageb.parquet"
DENUE_PQ = PROC / "denue_cdmx.parquet"
AGEB_GPKG = PROC / "ageb_cdmx.gpkg"
CRIME_PQ = PROC / "crime_cdmx.parquet"


def db_url() -> str:
    return "postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}".format(
        u=os.getenv("PGUSER", "postgres"),
        p=os.getenv("PGPASSWORD", "postgres"),
        h=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        d=os.getenv("PGDATABASE", "cdmx_dw"),
    )
