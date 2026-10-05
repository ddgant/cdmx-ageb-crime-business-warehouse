"""Clean DENUE 11/2024 (CDMX) -> establishments with a coordinate-quality flag."""
import json
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from config import DENUE_CSV, DENUE_PQ, DOCS_QA, AGEE_SHP, ENT_CODE

KEEP = ["id", "clee", "nom_estab", "codigo_act", "nombre_act", "per_ocu", "cve_ent",
        "cve_mun", "cve_loc", "ageb", "manzana", "latitud", "longitud", "fecha_alta"]


def main():
    raw = pd.read_csv(DENUE_CSV, encoding="latin-1", dtype=str)
    n_raw = len(raw)
    for c in raw.columns:
        raw[c] = raw[c].str.strip()

    df = raw[raw.cve_ent == ENT_CODE][KEEP].copy()
    dup = int(df.id.duplicated().sum())
    df = df.drop_duplicates("id")

    df["lat"] = pd.to_numeric(df.latitud, errors="coerce")
    df["lon"] = pd.to_numeric(df.longitud, errors="coerce")
    df["cvegeo_denue"] = df.cve_ent + df.cve_mun + df.cve_loc + df.ageb

    # Coordinate validity rule: point must fall inside the CDMX state polygon (AGEE).
    state = gpd.read_file(AGEE_SHP).to_crs(4326).geometry.union_all()
    has = df.lat.notna() & df.lon.notna()
    ok = np.zeros(len(df), dtype=bool)
    ok[has.values] = shapely.contains_xy(state, df.lon[has].values, df.lat[has].values)
    df["coord_quality"] = np.where(ok, "ok", "invalid")

    df.drop(columns=["latitud", "longitud", "cve_ent"]).to_parquet(DENUE_PQ, index=False)

    qa = {
        "source": "INEGI DENUE 11/2024 (Ciudad de Mexico, csv), file denue_inegi_09_.csv",
        "rows_raw_file": n_raw,
        "duplicate_ids_removed": dup,
        "rows_after_clean": len(df),
        "coord_quality_counts": df.coord_quality.value_counts().to_dict(),
        "null_codigo_act": int(df.codigo_act.isna().sum()),
        "per_ocu_distribution": df.per_ocu.value_counts().to_dict(),
        "latest_fecha_alta": str(df.fecha_alta.max()),
        "rule": "cve_ent=09; dedupe by id; coordinates must fall inside the CDMX polygon else flagged invalid (kept, AGEB assigned by DENUE code when it exists)",
    }
    (DOCS_QA / "denue_qa.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(qa, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
