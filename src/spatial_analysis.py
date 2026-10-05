"""Spatial analytics on top of the warehouse KPI view.

Everything here reads from the PostgreSQL/PostGIS warehouse (dw.vw_ageb_kpis),
never from raw files, CSVs or intermediate DataFrames.

Main steps used by notebooks/03_spatial_analysis.ipynb:
    load_kpis -> analysis_sample -> queen_weights / knn_weights
    -> spearman_pairs, global_moran, local_moran, bivariate_moran, local_bivariate
"""
from __future__ import annotations

from dataclasses import dataclass

import esda
import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal import weights
from scipy import stats

METRIC_EPSG = 32614          # UTM 14N, metric CRS used for neighbours and distances
MIN_POP_FOR_RATES = 500      # AGEB below this population have unstable per-resident rates
DEFAULT_PERMUTATIONS = 999
DEFAULT_SEED = 42
ALPHA = 0.05

KPI_QUERY = """
SELECT k.*, a.nom_mun, a.cve_mun
FROM dw.vw_ageb_kpis AS k
JOIN dw.dim_ageb AS a USING (ageb_key)
"""

# Moran quadrant codes used by esda: 1=HH, 2=LH, 3=LL, 4=HL
QUADRANT_LABELS = {1: "High-High", 2: "Low-High", 3: "Low-Low", 4: "High-Low"}
NOT_SIGNIFICANT = "Not significant"


# ------------------------------------------------------------------ data access
def load_kpis(engine) -> gpd.GeoDataFrame:
    """KPI table (one row per AGEB) from the warehouse, projected to the metric CRS."""
    gdf = gpd.read_postgis(KPI_QUERY, engine, geom_col="geom", crs=4326)
    return gdf.rename_geometry("geometry").to_crs(METRIC_EPSG)


def add_transforms(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add log1p versions of the skewed indicators used in the spatial statistics."""
    out = gdf.copy()
    for col in ("population_density_km2", "business_density_km2", "retail_density_km2",
                "service_density_km2", "crime_rate_per_1000", "businesses_per_1000"):
        out[f"log_{col}"] = np.log1p(out[col])
    return out


def analysis_sample(gdf: gpd.GeoDataFrame, min_pop: int = MIN_POP_FOR_RATES) -> gpd.GeoDataFrame:
    """Keep AGEB with a stable population base and complete indicators.

    Rates divide by population, so AGEB with very few residents (parks, industrial
    zones, a single building) produce extreme values that would dominate the statistics.
    """
    keep = (gdf.total_population >= min_pop) & gdf.eap_rate_pct.notna()
    return gdf.loc[keep].reset_index(drop=True)


# ------------------------------------------------------------------ spatial weights
def queen_weights(gdf: gpd.GeoDataFrame) -> weights.W:
    """Queen contiguity (shared edge or vertex), row-standardised."""
    w = weights.Queen.from_dataframe(gdf, use_index=False)
    w.transform = "R"
    return w


def knn_weights(gdf: gpd.GeoDataFrame, k: int = 8) -> weights.W:
    """k nearest neighbours between AGEB centroids, row-standardised (no islands by design)."""
    w = weights.KNN.from_dataframe(gdf, k=k)
    w.transform = "R"
    return w


def describe_weights(w: weights.W) -> dict:
    """Summary of a weights object, to report the neighbourhood rule."""
    return {
        "n": w.n,
        "islands": len(w.islands),
        "min_neighbors": int(w.min_neighbors),
        "mean_neighbors": round(float(w.mean_neighbors), 2),
        "max_neighbors": int(w.max_neighbors),
    }


# ------------------------------------------------------------------ correlation
def correlation_table(df: pd.DataFrame, pairs: list[tuple[str, str]]) -> pd.DataFrame:
    """Spearman and Pearson (on the given columns) with p-values for each pair."""
    rows = []
    for x, y in pairs:
        pair = df[[x, y]].dropna()
        rho, p_rho = stats.spearmanr(pair[x], pair[y])
        r, p_r = stats.pearsonr(pair[x], pair[y])
        rows.append({"x": x, "y": y, "n": len(pair), "spearman_rho": rho,
                     "spearman_p": p_rho, "pearson_r": r, "pearson_p": p_r})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ Moran statistics
@dataclass
class MoranResult:
    name: str
    statistic: float
    expected: float
    z_score: float
    p_value: float
    permutations: int

    def as_dict(self) -> dict:
        return {"indicator": self.name, "I": self.statistic, "E[I]": self.expected,
                "z (permutation)": self.z_score, "p (permutation)": self.p_value,
                "permutations": self.permutations}


def global_moran(values, w: weights.W, name: str = "",
                 permutations: int = DEFAULT_PERMUTATIONS, seed: int = DEFAULT_SEED) -> MoranResult:
    """Global Moran's I with a permutation-based pseudo p-value."""
    np.random.seed(seed)
    m = esda.Moran(np.asarray(values, dtype=float), w, permutations=permutations)
    return MoranResult(name, float(m.I), float(m.EI), float(m.z_sim), float(m.p_sim), permutations)


def bivariate_moran(x, y, w: weights.W, name: str = "",
                    permutations: int = DEFAULT_PERMUTATIONS, seed: int = DEFAULT_SEED) -> MoranResult:
    """Global bivariate Moran's I: association between x at a location and y in its neighbours."""
    np.random.seed(seed)
    m = esda.Moran_BV(np.asarray(x, dtype=float), np.asarray(y, dtype=float), w,
                      permutations=permutations)
    z = (m.I - m.EI_sim) / m.seI_sim
    return MoranResult(name, float(m.I), float(m.EI_sim), float(z), float(m.p_sim), permutations)


def _two_sided_pvalue(observed, simulated) -> np.ndarray:
    """Two-sided pseudo p-value from conditional permutations, (M + 1) / (R + 1).

    Computed here instead of through esda's `alternative=` argument because that
    argument only exists in recent esda releases (it needs Python 3.12+), while older
    releases silently return a one-sided p-value. `simulated` has shape (R, n).
    """
    sim = np.asarray(simulated, dtype=float).T            # (n, R)
    obs = np.asarray(observed, dtype=float)
    n, r = sim.shape
    pvals = np.empty(n)
    for i in range(n):
        pct = (sim[i] <= obs[i]).mean() * 100
        p_low = min(pct, 100 - pct)
        low, high = np.percentile(sim[i], p_low), np.percentile(sim[i], 100 - p_low)
        outside = (sim[i] <= low).sum() + (sim[i] >= high).sum()
        pvals[i] = (outside + 1) / (r + 1)
    return pvals


def _cluster_labels(quadrant, p_values, alpha: float) -> pd.Series:
    labels = pd.Series(quadrant).map(QUADRANT_LABELS)
    return labels.where(np.asarray(p_values) < alpha, NOT_SIGNIFICANT)


def local_moran(values, w: weights.W, permutations: int = DEFAULT_PERMUTATIONS,
                seed: int = DEFAULT_SEED, alpha: float = ALPHA) -> pd.DataFrame:
    """Local Moran's I (LISA): statistic, pseudo p-value, quadrant and cluster label per AGEB."""
    lisa = esda.Moran_Local(np.asarray(values, dtype=float), w,
                            permutations=permutations, seed=seed)
    p_sim = _two_sided_pvalue(lisa.Is, lisa.sim)
    return pd.DataFrame({
        "local_I": lisa.Is,
        "p_sim": p_sim,
        "quadrant": lisa.q,
        "cluster": _cluster_labels(lisa.q, p_sim, alpha).values,
    })


def local_bivariate(x, y, w: weights.W, permutations: int = DEFAULT_PERMUTATIONS,
                    seed: int = DEFAULT_SEED, alpha: float = ALPHA) -> pd.DataFrame:
    """Local bivariate Moran: hotspots where high x coincides with high y in the neighbours."""
    lisa = esda.Moran_Local_BV(np.asarray(x, dtype=float), np.asarray(y, dtype=float), w,
                               permutations=permutations, seed=seed)
    p_sim = _two_sided_pvalue(lisa.Is, lisa.sim)
    return pd.DataFrame({
        "local_I": lisa.Is,
        "p_sim": p_sim,
        "quadrant": lisa.q,
        "cluster": _cluster_labels(lisa.q, p_sim, alpha).values,
    })


def cluster_counts(clusters: pd.Series) -> pd.Series:
    """Number of AGEB per cluster label, in a fixed, readable order."""
    order = ["High-High", "Low-Low", "High-Low", "Low-High", NOT_SIGNIFICANT]
    return clusters.value_counts().reindex(order, fill_value=0)


def spatial_lag(values, w: weights.W) -> np.ndarray:
    """Weighted average of the neighbours' values (used in Moran scatterplots)."""
    return weights.lag_spatial(w, np.asarray(values, dtype=float))
