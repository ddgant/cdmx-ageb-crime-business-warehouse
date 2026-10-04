"""Clean INEGI Census 2020 (AGEB/urban block results, CDMX) -> one row per urban AGEB."""
import json
import pandas as pd
from config import CENSUS_CSV, CENSUS_PQ, DOCS_QA, ENT_CODE

# INEGI codes: '*' = confidential (suppressed), 'N/D' = not available
NA = ["*", "N/D"]
NUM_COLS = ["POBTOT", "POBFEM", "POBMAS", "P_0A2", "P_3A5", "P_6A11", "P_12A14",
            "P_15A17", "P_18A24", "P_60YMAS", "P_12YMAS", "PEA", "PE_INAC",
            "POCUPADA", "PDESOCUP", "VIVTOT", "TVIVHAB", "PROM_OCUP", "GRAPROES"]


def main():
    raw = pd.read_csv(CENSUS_CSV, encoding="utf-8-sig", dtype=str, na_values=NA)
    n_raw = len(raw)

    # AGEB-level totals: MZA == '000' rows with a real AGEB code
    df = raw[(raw.ENTIDAD == ENT_CODE) & (raw.MZA == "000") & (raw.AGEB != "0000")].copy()
    df["cvegeo"] = df.ENTIDAD + df.MUN + df.LOC + df.AGEB
    assert df.cvegeo.is_unique, "duplicate AGEB keys in census"

    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # derived age group 25-59 = total minus every other group (no explicit INEGI column)
    others = ["P_0A2", "P_3A5", "P_6A11", "P_12A14", "P_15A17", "P_18A24", "P_60YMAS"]
    df["P_25A59"] = df.POBTOT - df[others].sum(axis=1, min_count=len(others))
    neg = int((df.P_25A59 < 0).sum())
    df.loc[df.P_25A59 < 0, "P_25A59"] = pd.NA

    out = df[["cvegeo", "ENTIDAD", "MUN", "NOM_MUN", "LOC", "AGEB"] + NUM_COLS + ["P_25A59"]].rename(
        columns=str.lower)
    out = out.rename(columns={"entidad": "cve_ent", "mun": "cve_mun", "loc": "cve_loc",
                              "ageb": "cve_ageb"})
    out.to_parquet(CENSUS_PQ, index=False)

    qa = {
        "source": "INEGI Censo de Poblacion y Vivienda 2020, Principales resultados por AGEB y manzana urbana (Ciudad de Mexico)",
        "rows_raw_file": n_raw,
        "rows_ageb": len(out),
        "alcaldias": int(out.cve_mun.nunique()),
        "pobtot_sum": int(out.pobtot.sum()),
        "null_counts": {c: int(out[c.lower()].isna().sum()) for c in NUM_COLS
                        if out[c.lower()].isna().sum() > 0},
        "p_25a59_negative_set_null": neg,
        "rule": "ENTIDAD=09, MZA=000, AGEB!=0000; '*' and 'N/D' converted to NULL (not zero)",
    }
    (DOCS_QA / "census_qa.json").write_text(json.dumps(qa, indent=2, ensure_ascii=False))
    print(json.dumps(qa, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
