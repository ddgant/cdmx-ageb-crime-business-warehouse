"""Clean FGJ CDMX crime records (carpetas de investigacion) for one year -> staging contract.

Output columns: source_id, crime_category, crime_type, fgj_category,
                occurred_date, occurred_hour, lat, lon, coord_quality
The year is taken from the incident date (fecha_hecho), not from the filing date.
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from config import CRIME_CSV, CRIME_PQ, DOCS_QA, AGEE_SHP, CRIME_YEAR
from crime_taxonomy import NON_CRIME_CATEGORY, crime_group, parse_hour



def main():
    cols = ["fecha_hecho", "hora_hecho", "delito", "categoria_delito", "latitud", "longitud"]
    raw = pd.read_csv(CRIME_CSV, dtype=str, low_memory=False, usecols=cols)
    raw["source_id"] = raw.index.astype(str)          # row number in the source file
    n_raw = len(raw)

    raw["fh"] = pd.to_datetime(raw.fecha_hecho, errors="coerce", format="mixed")
    df = raw[raw.fh.dt.year == CRIME_YEAR].copy()
    n_year = len(df)

    non_crime = int((df.categoria_delito == NON_CRIME_CATEGORY).sum())
    df = df[df.categoria_delito != NON_CRIME_CATEGORY].copy()

    df["lat"] = pd.to_numeric(df.latitud, errors="coerce")
    df["lon"] = pd.to_numeric(df.longitud, errors="coerce")
    state = gpd.read_file(AGEE_SHP).to_crs(4326).geometry.union_all()
    has = (df.lat.notna() & df.lon.notna()).values
    ok = np.zeros(len(df), dtype=bool)
    ok[has] = shapely.contains_xy(state, df.lon.values[has], df.lat.values[has])
    df["coord_quality"] = np.where(ok, "ok", "invalid")

    df["crime_type"] = df.delito.str.strip()
    df["crime_category"] = df.crime_type.map(crime_group)
    df["fgj_category"] = df.categoria_delito
    df["occurred_date"] = df.fh.dt.date
    df["occurred_hour"] = parse_hour(df.hora_hecho)   # source mixes HH:MM:SS and HH:MM:SS:SS

    out = df[["source_id", "crime_category", "crime_type", "fgj_category", "occurred_date",
              "occurred_hour", "lat", "lon", "coord_quality"]]
    out.to_parquet(CRIME_PQ, index=False)

    # time-of-day quality: reported times heap on round values and on noon (likely a default)
    minutes = df.hora_hecho.str.extract(r"^\d{1,2}:(\d{2})")[0].dropna()
    noon = df.hora_hecho.dropna().str.match(r"^12:00:00")

    qa = {
        "source": "FGJ Ciudad de Mexico, carpetas de investigacion (datos.cdmx.gob.mx), file carpetasFGJ_acumulado_2025_01.csv",
        "year_filter": f"year(fecha_hecho) == {CRIME_YEAR}",
        "rows_raw_file": n_raw,
        "rows_in_year": n_year,
        "excluded_non_criminal_events": non_crime,
        "rows_after_clean": len(out),
        "missing_coordinates": int((~has).sum()),
        "coordinates_outside_cdmx": int((has & ~ok).sum()),
        "rows_with_valid_point": int(ok.sum()),
        "null_hour": int(out.occurred_hour.isna().sum()),
        "share_time_exactly_noon": round(float(noon.mean()), 4),
        "share_time_on_round_hour": round(float((minutes == "00").mean()), 4),
        "distinct_crime_types": int(out.crime_type.nunique()),
        "crime_category_counts": out.crime_category.value_counts().to_dict(),
        "monthly_counts": df.fh.dt.month.value_counts().sort_index().to_dict(),
        "rule": "year by fecha_hecho; 'HECHO NO DELICTIVO' removed; points must be inside CDMX polygon; incidents without a valid point stay in staging but are not loaded to the fact table",
    }
    (DOCS_QA / "crime_qa.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(qa, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
