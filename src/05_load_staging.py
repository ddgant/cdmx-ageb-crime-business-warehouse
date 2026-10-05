"""Load cleaned files into PostgreSQL staging schema (stg). Raw files are never touched."""
import geopandas as gpd
import pandas as pd
from sqlalchemy import text
from config import AGEB_GPKG, CENSUS_PQ, DENUE_PQ, CRIME_PQ
from db import get_engine


def main():
    eng = get_engine()
    with eng.begin() as cx:
        cx.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        cx.execute(text("CREATE SCHEMA IF NOT EXISTS stg"))

    ageb = gpd.read_file(AGEB_GPKG, layer="ageb").rename_geometry("geom")
    ageb.to_postgis("ageb", eng, schema="stg", if_exists="replace", index=True)
    print("stg.ageb", len(ageb))

    census = pd.read_parquet(CENSUS_PQ)
    census.to_sql("census", eng, schema="stg", if_exists="replace", index=False)
    print("stg.census", len(census))

    denue = pd.read_parquet(DENUE_PQ)
    denue.to_sql("denue", eng, schema="stg", if_exists="replace", index=False, chunksize=20000, method="multi")
    print("stg.denue", len(denue))

    # Crime staging contract (produced by 04_clean_crime.py once the dataset is available):
    # source_id, crime_category, crime_type, fgj_category, occurred_date, occurred_hour, lat, lon, coord_quality
    if CRIME_PQ.exists():
        crime = pd.read_parquet(CRIME_PQ)
        crime.to_sql("crime", eng, schema="stg", if_exists="replace", index=False, chunksize=20000, method="multi")
        print("stg.crime", len(crime))
    else:
        with eng.begin() as cx:
            cx.execute(text("DROP TABLE IF EXISTS stg.crime"))
            cx.execute(text("""CREATE TABLE stg.crime (
                source_id TEXT, crime_category TEXT, crime_type TEXT, fgj_category TEXT,
                occurred_date DATE, occurred_hour SMALLINT,
                lat DOUBLE PRECISION, lon DOUBLE PRECISION, coord_quality TEXT)"""))
        print("stg.crime created EMPTY (crime dataset not provided yet)")


if __name__ == "__main__":
    main()
