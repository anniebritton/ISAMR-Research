"""Report figures. Static PNGs on a light surface, one shared style."""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import aoi, config, drivers, extract, phenology, smoothers  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]  # validated categorical order, slots 1-4

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "lines.linewidth": 2,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "semibold", "axes.titlelocation": "left",
    "figure.dpi": 150,
})


def _save(fig, name: str) -> None:
    config.ensure_dirs()
    fig.savefig(config.FIGURES / f"{name}.png", bbox_inches="tight")
    plt.close(fig)


def study_area() -> None:
    ring = np.array(aoi.boundary_geojson()["features"][0]["geometry"]["coordinates"][0])
    pts = aoi.load_points()
    fig, ax = plt.subplots(figsize=(5, 6))
    ax.fill(ring[:, 0], ring[:, 1], color=GRID, zorder=0)
    ax.plot(ring[:, 0], ring[:, 1], color=INK_2, lw=1)
    for color, name in zip(SERIES, config.load()["aoi"]["strata"]):
        xy = np.array([p["geometry"]["coordinates"] for p in pts if p["properties"]["stratum"] == name])
        ax.scatter(xy[:, 0], xy[:, 1], s=14, color=color, edgecolor=SURFACE, linewidth=0.8, label=name.replace("_", " "))
    ax.set_aspect(1 / np.cos(np.deg2rad(58)))
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Wapusk National Park and the 300 sample pixels")
    ax.legend(frameon=False, loc="lower left")
    _save(fig, "study_area")


def example_fits(n: int = 3, seed: int = 7) -> None:
    """Spot-check: raw observations, smoothed curve, and crossing for random pixel-years."""
    cfg = config.load()
    p = cfg["phenology"]["primary"]
    daily = phenology.load_daily(p["mask"])
    base = phenology.baselines(daily)
    rng = np.random.default_rng(seed)
    keys = daily[["pixel_id", "year"]].drop_duplicates().to_numpy()
    fig, axes = plt.subplots(n, 1, figsize=(8, 2.4 * n), sharex=True)
    shown = 0
    for pid, year in keys[rng.permutation(len(keys))]:
        g = daily[(daily["pixel_id"] == pid) & (daily["year"] == year)]
        lo, hi = cfg["phenology"]["window_doy"]
        g = g[(g["doy"] >= lo) & (g["doy"] <= hi)]
        b = base[pid]
        d = smoothers.greenup_doy(g["doy"], g["ndvi"], g["snow"], b, smoother=p["smoother"], fraction=p["fraction"])
        if np.isnan(d):
            continue
        t, y = smoothers.prepare(g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy(), b)
        grid = np.arange(lo, hi + 1, dtype=float)
        curve = smoothers.savgol(t, y, grid)
        ax = axes[shown]
        ax.scatter(g["doy"], g["ndvi"], s=10, color=INK_2, label="Snow-free observation")
        ax.scatter(g.loc[g["snow"] == 1, "doy"], np.full((g["snow"] == 1).sum(), b), s=8, marker="x",
                   color=SERIES[3], label="Snow flag (baseline anchor)")
        ax.plot(grid, curve, color=SERIES[0], label="Savitzky-Golay fit")
        ax.axvline(d, color=SERIES[1], lw=1.5, ls="--", label=f"Mid-green-up DOY {d:.0f}")
        ax.set_title(f"Pixel {pid}, {year}")
        ax.set_ylabel("NDVI")
        ax.legend(frameon=False, fontsize=8, loc="upper right")
        shown += 1
        if shown == n:
            break
    axes[-1].set_xlabel("Day of year")
    _save(fig, "example_fits")


def greenup_series(series: pd.DataFrame, mcd: pd.DataFrame, trend: dict) -> None:
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(series["year"], series["greenup_doy"], color=SERIES[0], marker="o", ms=5, label="This study (MOD09GA, primary spec)")
    ax.plot(mcd["year"], mcd["greenup_doy"], color=SERIES[1], marker="s", ms=5, label="MCD12Q2 MidGreenup (validation)")
    yrs = np.array([series["year"].min(), series["year"].max()], float)
    ax.plot(yrs, trend["intercept"] + trend["slope"] * yrs, color=SERIES[0], lw=1, ls="--",
            label=f"Theil-Sen {trend['slope']:+.2f} d/yr [{trend['ci_low']:+.2f}, {trend['ci_high']:+.2f}]")
    ax.set_ylabel("Mid-green-up (day of year)")
    ax.set_title("Park-wide mid-green-up, 2001-2024")
    ax.legend(frameon=False, fontsize=8)
    _save(fig, "greenup_series")


def validation_scatter(pix: pd.DataFrame) -> None:
    ref = extract.load("mcd12q2")
    ref = ref[(ref["mid_qa"] <= 1)]
    m = pix.merge(ref, on=["pixel_id", "year"]).dropna(subset=["doy", "MidGreenup_doy"])
    fig, ax = plt.subplots(figsize=(4.6, 4.4))
    hb = ax.hexbin(m["MidGreenup_doy"], m["doy"], gridsize=35, cmap="Blues", mincnt=1, linewidths=0)
    lim = [min(m["doy"].min(), m["MidGreenup_doy"].min()), max(m["doy"].max(), m["MidGreenup_doy"].max())]
    ax.plot(lim, lim, color=INK_2, lw=1, ls="--")
    ax.set_xlabel("MCD12Q2 MidGreenup (DOY)")
    ax.set_ylabel("This study (DOY)")
    ax.set_title("Pixel-year agreement")
    fig.colorbar(hb, ax=ax, label="Pixel-years")
    _save(fig, "validation_scatter")


def drivers_scatter(series: pd.DataFrame, drv: pd.DataFrame) -> None:
    d = series.merge(drv, on="year")
    fig, axes = plt.subplots(1, 2, figsize=(8, 3.4), sharey=True)
    for ax, col, label in zip(axes, ["snow_off", "tdd"], ["Snow-off (DOY, Churchill)", "Thawing degree days, Apr-May"]):
        ok = d[[col, "greenup_doy"]].dropna()
        ax.scatter(ok[col], ok["greenup_doy"], s=30, color=SERIES[0], edgecolor=SURFACE, linewidth=1)
        b = np.polyfit(ok[col], ok["greenup_doy"], 1)
        xs = np.linspace(ok[col].min(), ok[col].max(), 2)
        ax.plot(xs, np.polyval(b, xs), color=INK_2, lw=1)
        ax.set_xlabel(label)
    axes[0].set_ylabel("Mid-green-up (DOY)")
    axes[0].set_title("Green-up against the two pre-registered predictors")
    _save(fig, "drivers_scatter")


def multiverse_plot(mv: pd.DataFrame) -> None:
    mv = mv.sort_values("h1_slope").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(7, 0.26 * len(mv) + 1))
    for i, r in mv.iterrows():
        color = SERIES[1] if r["primary"] else SERIES[0]
        ax.plot([r["h1_ci_low"], r["h1_ci_high"]], [i, i], color=color, lw=1.5)
        ax.scatter(r["h1_slope"], i, color=color, s=24, zorder=3)
    ax.axvline(0, color=INK_2, lw=1)
    labels = [f"{r['mask']} / {r['smoother']} / {r['fraction']:.2f} / {r['aggregation']}" for _, r in mv.iterrows()]
    ax.set_yticks(range(len(mv)), labels, fontsize=7)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Theil-Sen slope (days/yr) with 95% CI")
    ax.set_title("H1 across all 24 specifications (primary in orange)")
    _save(fig, "multiverse")


def strata_plot(strat: pd.DataFrame) -> None:
    names = list(config.load()["aoi"]["strata"])
    fig, axes = plt.subplots(1, len(names), figsize=(10, 2.8), sharey=True)
    for ax, name in zip(axes, names):
        g = strat[strat["stratum"] == name]
        ax.plot(g["year"], g["median"], color=SERIES[0], marker="o", ms=3)
        ax.set_title(name.replace("_", " "))
    axes[0].set_ylabel("Median mid-green-up (DOY)")
    _save(fig, "greenup_by_stratum")


def run() -> None:
    cfg = config.load()
    p = cfg["phenology"]["primary"]
    pix = phenology.load_pixels()
    primary = phenology.select(pix, p["mask"], p["smoother"], p["fraction"])
    series = pd.read_csv(config.PROCESSED / "greenup_annual.csv")
    mcd = pd.read_csv(config.PROCESSED / "mcd12q2_annual.csv")
    conf = json.loads((config.TABLES / "confirmatory.json").read_text())
    h = conf["hypotheses"]
    study_area()
    example_fits()
    greenup_series(series, mcd, {"slope": h["h1_slope"], "intercept": h["h1_intercept"],
                                 "ci_low": h["h1_ci_low"], "ci_high": h["h1_ci_high"]})
    validation_scatter(primary)
    drivers_scatter(series, drivers.load())
    if (config.TABLES / "multiverse.csv").exists():
        multiverse_plot(pd.read_csv(config.TABLES / "multiverse.csv"))
    if (config.TABLES / "greenup_by_stratum.csv").exists():
        strata_plot(pd.read_csv(config.TABLES / "greenup_by_stratum.csv"))
