"""Load official AGEB polygons, validate them and cross-check them against the Census."""
import json
import geopandas as gpd
import pandas as pd
from config import AGEB_SHP, AGEB_GPKG, DOCS_QA, CENSUS_PQ, ENT_CODE


def main():
    g = gpd.read_file(AGEB_SHP)
    src_crs = str(g.crs.name)
    invalid_before = int((~g.is_valid).sum())
    if invalid_before:
        g["geometry"] = g.geometry.make_valid()

    m = g[g.CVE_ENT == ENT_CODE].copy()
    assert m.CVEGEO.is_unique and (m.CVEGEO.str.len() == 13).all()
    m = m.to_crs(4326)
    m["geometry"] = m.geometry.force_2d()
    m = m.rename(columns={"CVEGEO": "cvegeo", "CVE_ENT": "cve_ent", "CVE_MUN": "cve_mun",
                          "CVE_LOC": "cve_loc", "CVE_AGEB": "cve_ageb"})
    m.to_file(AGEB_GPKG, driver="GPKG", layer="ageb")

    census = pd.read_parquet(CENSUS_PQ)
    no_poly = census[~census.cvegeo.isin(m.cvegeo)]
    qa = {
        "source": "INEGI Marco Geoestadistico (Censo 2020), capa AGEB urbano, Ciudad de Mexico",
        "original_crs": src_crs,
        "stored_crs": "EPSG:4326 (areas computed later in EPSG:32614)",
        "ageb_polygons": len(m),
        "invalid_geometries_before_fix": invalid_before,
        "invalid_geometries_after": int((~m.is_valid).sum()),
        "geometry_types": m.geom_type.value_counts().to_dict(),
        "alcaldias": int(m.cve_mun.nunique()),
        "census_ageb_without_polygon": no_poly[["cvegeo", "pobtot"]].to_dict("records"),
        "polygons_without_census_row": int((~m.cvegeo.isin(census.cvegeo)).sum()),
    }
    (DOCS_QA / "ageb_qa.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False, default=str))
    print(json.dumps(qa, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
