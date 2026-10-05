import geopandas as gpd
import numpy as np
import pandas as pd
import pytest
from shapely.geometry import box

import spatial_analysis as sa


def grid(n=10):
    cells = [box(i, j, i + 1, j + 1) for j in range(n) for i in range(n)]
    return gpd.GeoDataFrame({"x": [c.centroid.x for c in cells], "y": [c.centroid.y for c in cells]},
                            geometry=cells, crs=32614)


def test_queen_weights_on_grid():
    w = sa.queen_weights(grid(5))
    info = sa.describe_weights(w)
    assert info["n"] == 25 and info["islands"] == 0
    assert info["min_neighbors"] == 3 and info["max_neighbors"] == 8   # corner / interior


def test_global_moran_detects_gradient_and_noise():
    g = grid(12)
    w = sa.queen_weights(g)
    smooth = sa.global_moran(g.x.values + g.y.values, w, "gradient", permutations=199)
    assert smooth.statistic > 0.8 and smooth.p_value < 0.01
    noise = sa.global_moran(np.random.default_rng(0).normal(size=len(g)), w, "noise", permutations=199)
    assert abs(noise.statistic) < 0.2 and noise.p_value > 0.01


def test_local_moran_flags_high_high_cluster():
    g = grid(14)
    values = np.random.default_rng(1).normal(size=len(g))
    values[(g.x < 5) & (g.y < 5)] += 6          # a 5x5 block of high values
    out = sa.local_moran(values, sa.queen_weights(g), permutations=999)
    assert "High-High" in set(out.cluster)
    assert set(out.cluster) <= set(sa.QUADRANT_LABELS.values()) | {sa.NOT_SIGNIFICANT}


def test_bivariate_moran_positive_for_related_gradients():
    g = grid(12)
    w = sa.queen_weights(g)
    res = sa.bivariate_moran(g.x.values, g.x.values + 0.1 * g.y.values, w, permutations=199)
    assert res.statistic > 0.5


def test_correlation_table_perfect_monotone():
    df = pd.DataFrame({"a": np.arange(50), "b": np.arange(50) ** 3})
    out = sa.correlation_table(df, [("a", "b")])
    assert out.spearman_rho.iloc[0] == pytest.approx(1.0)


def test_analysis_sample_drops_small_and_incomplete_agebs():
    g = grid(2).assign(total_population=[100, 800, 900, 1000], eap_rate_pct=[60, 60, np.nan, 70])
    kept = sa.analysis_sample(g, min_pop=500)
    assert len(kept) == 2


def test_moran_scatter_slope_equals_morans_i():
    """The slope drawn in the Moran scatter plot must equal the global Moran's I."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import viz

    g = grid(12)
    w = sa.queen_weights(g)
    values = g.x.values + g.y.values + np.random.default_rng(1).normal(scale=2.0, size=len(g))
    result = sa.global_moran(values, w, "x", permutations=99)
    fig = viz.moran_scatter(values, sa.spatial_lag(values, w), "test")
    drawn = float(fig.axes[0].texts[0].get_text().split("=")[1])
    plt.close(fig)
    assert drawn == pytest.approx(result.statistic, abs=0.01)
