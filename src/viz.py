"""Plot helpers for the maps and figures saved to outputs/.

Colour rules: one-hue light-to-dark ramps for magnitudes, two hues around a neutral for
polarity (cluster maps), fixed categorical order, thin recessive boundaries.
"""
from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch, Rectangle

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.spines.top": False,
    "axes.spines.right": False, "figure.dpi": 110, "savefig.dpi": 200,
})

INK = "#0b0b0b"
INK_MUTED = "#52514e"
GRID = "#d9d8d3"
BOUNDARY = "#8a8985"
NEUTRAL = "#f0efec"

# One-hue sequential ramps (light -> dark)
BLUE_RAMP = ["#cde2fb", "#9ec5f4", "#5598e7", "#256abf", "#104281", "#0d366b"]
ORANGE_RAMP = ["#fde3d6", "#f9bfa3", "#f1946a", "#e56a34", "#c24f1f", "#8f3913"]

# LISA clusters: polarity (red high / blue low) plus tints for the outlier classes
CLUSTER_COLORS = {
    "High-High": "#e34948",
    "Low-Low": "#2a78d6",
    "High-Low": "#f4b3b2",
    "Low-High": "#b3d0f2",
    "Not significant": "#ececea",
}

# 3x3 bivariate palette (rows: low->high y, columns: low->high x)
BIVARIATE = [
    ["#e8e8e8", "#b8d6be", "#73ae80"],
    ["#e4acac", "#ad9ea5", "#627f8c"],
    ["#c85a5a", "#985356", "#574249"],
]


def _frame(ax, title: str | None):
    ax.set_axis_off()
    ax.set_aspect("equal")
    if title:
        ax.set_title(title, loc="left", fontsize=11, color=INK, fontweight="bold")


def _boundaries(ax, boundaries: gpd.GeoDataFrame | None):
    if boundaries is not None:
        boundaries.boundary.plot(ax=ax, color=BOUNDARY, linewidth=0.6, zorder=3)


def _save(fig, path: Path | None):
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, bbox_inches="tight", facecolor="white")


def quantile_edges(values: pd.Series, k: int = 6) -> np.ndarray:
    """Unique quantile class edges, so the legend never repeats a break."""
    return np.unique(np.quantile(values.dropna(), np.linspace(0, 1, k + 1)))


def choropleth(gdf, column, title, ramp, path=None, boundaries=None, k=6,
               legend_title=None, fmt="{:,.0f}"):
    """Quantile choropleth with one-hue ramp and an explicit class legend."""
    edges = quantile_edges(gdf[column], k)
    n = len(edges) - 1
    cmap = ListedColormap(ramp[:n] if n <= len(ramp) else ramp)
    norm = BoundaryNorm(edges, cmap.N)
    fig, ax = plt.subplots(figsize=(7, 7.5))
    gdf.plot(ax=ax, column=column, cmap=cmap, norm=norm, linewidth=0.05, edgecolor="white")
    _boundaries(ax, boundaries)
    _frame(ax, title)
    handles = [Patch(facecolor=cmap(i), edgecolor="none",
                     label=f"{fmt.format(edges[i])} to {fmt.format(edges[i + 1])}") for i in range(n)]
    ax.legend(handles=handles, title=legend_title or column, loc="lower left",
              frameon=False, fontsize=8, title_fontsize=8)
    _save(fig, path)
    return fig


def categorical_map(gdf, column, title, colors: dict, path=None, boundaries=None, order=None,
                    legend_title=None):
    """Map of a categorical column with a fixed colour per category."""
    order = order or list(colors)
    fig, ax = plt.subplots(figsize=(7, 7.5))
    for cat in order:
        sub = gdf[gdf[column] == cat]
        if len(sub):
            sub.plot(ax=ax, color=colors[cat], linewidth=0.05, edgecolor="white")
    _boundaries(ax, boundaries)
    _frame(ax, title)
    counts = gdf[column].value_counts()
    handles = [Patch(facecolor=colors[c], edgecolor="none", label=f"{c} ({counts.get(c, 0):,})")
               for c in order]
    ax.legend(handles=handles, title=legend_title, loc="lower left", frameon=False, fontsize=8,
              title_fontsize=8)
    _save(fig, path)
    return fig


def bivariate_map(gdf, x_col, y_col, title, x_label, y_label, path=None, boundaries=None):
    """3x3 bivariate choropleth (terciles of x across, terciles of y up)."""
    xq = pd.qcut(gdf[x_col], 3, labels=False, duplicates="drop")
    yq = pd.qcut(gdf[y_col], 3, labels=False, duplicates="drop")
    colors = [BIVARIATE[int(j)][int(i)] for i, j in zip(xq, yq)]
    fig, ax = plt.subplots(figsize=(7, 7.5))
    gdf.assign(_c=colors).plot(ax=ax, color=gdf.assign(_c=colors)["_c"], linewidth=0.05,
                               edgecolor="white")
    _boundaries(ax, boundaries)
    _frame(ax, title)
    lax = ax.inset_axes([0.02, 0.02, 0.2, 0.2])
    for j in range(3):
        for i in range(3):
            lax.add_patch(Rectangle((i, j), 1, 1, facecolor=BIVARIATE[j][i], edgecolor="white"))
    lax.set_xlim(0, 3); lax.set_ylim(0, 3); lax.set_xticks([]); lax.set_yticks([])
    lax.set_xlabel(f"{x_label} (low to high)", fontsize=7, color=INK_MUTED)
    lax.set_ylabel(f"{y_label} (low to high)", fontsize=7, color=INK_MUTED)
    for s in lax.spines.values():
        s.set_visible(False)
    _save(fig, path)
    return fig


def moran_scatter(values, lag, title, path=None, xlabel="Standardised value", clusters=None):
    """Moran scatterplot: standardised value vs standardised spatial lag."""
    # Both axes use the mean and standard deviation of the values, so the fitted slope equals Moran's I
    # (with row-standardised weights). Standardising the lag by its own spread would inflate the slope.
    mu, sd = np.mean(values), np.std(values)
    z = (np.asarray(values) - mu) / sd
    zl = (np.asarray(lag) - mu) / sd
    fig, ax = plt.subplots(figsize=(5, 4.6))
    if clusters is not None:
        colors = pd.Series(clusters).map(CLUSTER_COLORS).values
    else:
        colors = "#2a78d6"
    ax.scatter(z, zl, s=9, c=colors, alpha=0.75, linewidths=0)
    slope = np.polyfit(z, zl, 1)
    xs = np.linspace(z.min(), z.max(), 2)
    ax.plot(xs, np.polyval(slope, xs), color=INK, linewidth=1.5)
    ax.axhline(0, color=GRID, linewidth=0.8); ax.axvline(0, color=GRID, linewidth=0.8)
    ax.set_xlabel(xlabel, color=INK_MUTED); ax.set_ylabel("Spatial lag of neighbours", color=INK_MUTED)
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", color=INK)
    ax.text(0.98, 0.04, f"slope = {slope[0]:.3f}", transform=ax.transAxes, ha="right",
            fontsize=8, color=INK_MUTED)
    _save(fig, path)
    return fig


def correlation_heatmap(corr: pd.DataFrame, title, path=None):
    """Spearman correlation matrix with a diverging blue-red scale around a neutral gray."""
    cmap = ListedColormap(["#184f95", "#3987e5", "#9ec5f4", NEUTRAL, "#f4b3b2", "#e66767", "#a8201f"])
    fig, ax = plt.subplots(figsize=(7.2, 6))
    im = ax.imshow(corr.values, cmap=cmap, vmin=-1, vmax=1)
    ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=40, ha="right")
    ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.index)
    for i in range(len(corr)):
        for j in range(len(corr)):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8, color=INK)
    ax.set_title(title, loc="left", fontsize=11, fontweight="bold", color=INK)
    for s in ax.spines.values():
        s.set_visible(False)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Spearman rho")
    _save(fig, path)
    return fig
