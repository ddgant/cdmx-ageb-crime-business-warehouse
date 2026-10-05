"""Draw the star-schema diagram (docs/warehouse_model.png) with Graphviz.

Requires the Graphviz `dot` executable (https://graphviz.org/download/) and the
`graphviz` Python package. Facts are orange, dimensions blue. Only the key columns
and the most important attributes are drawn; the full list is in docs/data_dictionary.md.

    python tools/make_model_diagram.py
"""
from pathlib import Path

import graphviz

ROOT = Path(__file__).resolve().parents[1]

DIM_FILL, DIM_HEAD = "#eaf2fc", "#2a78d6"
FACT_FILL, FACT_HEAD = "#fdf0e3", "#e0731c"

# name -> (kind, grain or None, [(column, note)])
TABLES = {
    "dim_ageb": ("dim", None, [("ageb_key", "PK"), ("cvegeo", "13-char INEGI key"), ("nom_mun", "alcaldia"),
                               ("area_km2", ""), ("geom", "Polygon 4326"), ("geom_utm", "Polygon 32614")]),
    "dim_date": ("dim", None, [("date_key", "PK yyyymmdd"), ("year, quarter, month", ""), ("day_name, is_weekend", "")]),
    "dim_time": ("dim", None, [("hour_key", "PK 0-23"), ("time_band", "")]),
    "dim_crime_type": ("dim", None, [("crime_type_key", "PK"), ("crime_category", "10 groups"), ("crime_type", "offense"),
                                     ("fgj_category", "")]),
    "dim_scian": ("dim", None, [("scian_key", "PK"), ("codigo_act", "6-digit class"), ("sector_code", ""),
                                ("macro_group", "retail / services / other")]),
    "dim_business_size": ("dim", None, [("size_key", "PK"), ("per_ocu", "stratum"), ("min_emp, max_emp", "")]),
    "dim_age_group": ("dim", None, [("age_group_key", "PK"), ("label", "0-2 ... 60+"), ("min_age, max_age", "")]),
    "fact_population_ageb": ("fact", "1 row per AGEB", [("ageb_key", "PK, FK"), ("pobtot, pobfem, pobmas", ""),
                                                        ("p_12ymas, pea, pocupada, pdesocup", ""), ("vivtot, tvivhab", "")]),
    "fact_population_age": ("fact", "1 row per AGEB x age group", [("ageb_key", "PK, FK"), ("age_group_key", "PK, FK"),
                                                                  ("population", "")]),
    "fact_establishment": ("fact", "1 row per establishment", [("establishment_key", "PK"), ("denue_id", "natural key"),
                                                              ("ageb_key", "FK"), ("scian_key", "FK"), ("size_key", "FK"),
                                                              ("ageb_source, coord_quality", ""), ("geom", "Point 4326")]),
    "fact_crime_incident": ("fact", "1 row per incident", [("incident_key", "PK"), ("ageb_key", "FK"), ("crime_type_key", "FK"),
                                                          ("date_key", "FK"), ("hour_key", "FK"), ("geom", "Point 4326")]),
}

# (fact, dimension): foreign-key edges drawn from fact to dimension
EDGES = [
    ("fact_population_ageb", "dim_ageb"),
    ("fact_population_age", "dim_ageb"), ("fact_population_age", "dim_age_group"),
    ("fact_establishment", "dim_ageb"), ("fact_establishment", "dim_scian"), ("fact_establishment", "dim_business_size"),
    ("fact_crime_incident", "dim_ageb"), ("fact_crime_incident", "dim_crime_type"),
    ("fact_crime_incident", "dim_date"), ("fact_crime_incident", "dim_time"),
]


def note(text: str) -> str:
    """Grey note text; an empty note must not produce an empty FONT tag (invalid in Graphviz)."""
    return f'<FONT COLOR="#555555">{text}</FONT>' if text else " "


def html_label(name: str, kind: str, grain: str | None, cols: list[tuple[str, str]]) -> str:
    head = DIM_HEAD if kind == "dim" else FACT_HEAD
    rows = "".join(
        f'<TR><TD ALIGN="LEFT">{c}</TD><TD ALIGN="LEFT">{note(n)}</TD></TR>' for c, n in cols
    )
    sub = f'<TR><TD COLSPAN="2" BGCOLOR="{head}"><FONT COLOR="white" POINT-SIZE="9"><I>grain: {grain}</I></FONT></TD></TR>' if grain else ""
    return (f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4" COLOR="{head}" '
            f'BGCOLOR="{DIM_FILL if kind == "dim" else FACT_FILL}">'
            f'<TR><TD COLSPAN="2" BGCOLOR="{head}"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>{sub}{rows}</TABLE>>')


COMPACT = {  # table -> attributes shown in the compact (wide) diagram
    "dim_ageb": ["ageb_key (PK)", "cvegeo", "nom_mun", "geom, geom_utm"],
    "dim_date": ["date_key (PK)", "year, month, day_name"],
    "dim_time": ["hour_key (PK)", "time_band"],
    "dim_crime_type": ["crime_type_key (PK)", "crime_category", "crime_type"],
    "dim_scian": ["scian_key (PK)", "sector_code", "macro_group"],
    "dim_business_size": ["size_key (PK)", "per_ocu"],
    "dim_age_group": ["age_group_key (PK)", "label"],
    "fact_population_ageb": ["ageb_key (PK, FK)", "pobtot, pea, p_12ymas ..."],
    "fact_population_age": ["ageb_key, age_group_key (PK)", "population"],
    "fact_establishment": ["establishment_key (PK)", "ageb_key, scian_key, size_key (FK)", "geom"],
    "fact_crime_incident": ["incident_key (PK)", "ageb_key, crime_type_key (FK)", "date_key, hour_key (FK)", "geom"],
}


def compact_label(name: str, kind: str) -> str:
    head, fill = (DIM_HEAD, DIM_FILL) if kind == "dim" else (FACT_HEAD, FACT_FILL)
    rows = "".join(f'<TR><TD ALIGN="LEFT">{a}</TD></TR>' for a in COMPACT[name])
    return (f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="3" COLOR="{head}" BGCOLOR="{fill}">'
            f'<TR><TD BGCOLOR="{head}"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>{rows}</TABLE>>')


def make_wide() -> None:
    """Landscape variant for papers: dimensions on top, facts in the middle, dim_ageb below."""
    g = graphviz.Digraph("warehouse_wide", format="png")
    g.attr(rankdir="TB", splines="spline", nodesep="0.08", ranksep="0.7", dpi="220", bgcolor="white", fontname="Helvetica")
    g.attr("node", shape="plaintext", fontname="Helvetica", fontsize="11")
    g.attr("edge", color="#6b6b6b", arrowsize="0.7")
    for name, (kind, _, _) in TABLES.items():
        g.node(name, compact_label(name, kind))
    top = [d for d in TABLES if d.startswith("dim_") and d != "dim_ageb"]
    with g.subgraph() as s:
        s.attr(rank="same")
        for d in top:
            s.node(d)
    with g.subgraph() as s:
        s.attr(rank="same")
        for f in (n for n in TABLES if n.startswith("fact_")):
            s.node(f)
    for fact, dim in EDGES:
        if dim == "dim_ageb":
            g.edge(fact, dim)
        else:
            g.edge(dim, fact, dir="back")
    out = ROOT / "docs" / "warehouse_model_wide"
    g.render(str(out), cleanup=True)
    print(f"wrote {out.with_suffix('.png').relative_to(ROOT)}")


def main() -> None:
    make_wide()
    g = graphviz.Digraph("warehouse", format="png")
    g.attr(rankdir="LR", splines="spline", nodesep="0.3", ranksep="2.0", dpi="200", bgcolor="white", fontname="Helvetica",
           label="Mexico City urban intelligence warehouse (schema dw) - star schema around the AGEB dimension",
           labelloc="t", fontsize="16")
    g.attr("node", shape="plaintext", fontname="Helvetica", fontsize="11")
    g.attr("edge", color="#6b6b6b", arrowsize="0.7", arrowhead="normal")
    for name, (kind, grain, cols) in TABLES.items():
        g.node(name, html_label(name, kind, grain, cols))
    for fact, dim in EDGES:
        g.edge(fact, dim)
    out = ROOT / "docs" / "warehouse_model"
    g.render(str(out), cleanup=True)
    print(f"wrote {out.with_suffix('.png').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
