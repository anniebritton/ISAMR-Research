"""Per-pixel green-up dates, park-wide aggregation, and comparison with MCD12Q2."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor
from itertools import product

import numpy as np
import pandas as pd

from . import aoi, config, extract, smoothers

MASK_COLUMNS = {"strict": "ndvi_strict", "lenient": "ndvi_lenient", "nbar": "ndvi_nbar"}


def load_daily(mask: str) -> pd.DataFrame:
    source = "nbar" if mask == "nbar" else "mod09ga"
    df = extract.load(source)
    df = df.rename(columns={MASK_COLUMNS[mask]: "ndvi"})[["pixel_id", "date", "ndvi", "snow"]]
    df["year"] = df["date"].dt.year
    df["doy"] = df["date"].dt.dayofyear
    return df


def baselines(daily: pd.DataFrame, percentile: float | None = None) -> pd.Series:
    cfg = config.load()["phenology"]
    pct = cfg["baseline_percentile"] if percentile is None else percentile
    return daily.groupby("pixel_id").apply(
        lambda g: smoothers.dormant_baseline(
            g["doy"].to_numpy(), g["ndvi"].to_numpy(), tuple(cfg["baseline_exclude_doy"]), pct
        ),
        include_groups=False,
    )


def _pixel_years(daily: pd.DataFrame, base: pd.Series):
    for (pid, year), g in daily.groupby(["pixel_id", "year"]):
        yield pid, year, g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy(), base.get(pid, np.nan)


def _fit_chunk(args) -> list[dict]:
    chunk, smoother, fraction, cfg, extra = args
    opts = {"min_valid": cfg["min_valid_obs"], "min_amplitude": cfg["min_amplitude"], **extra}
    out = []
    for pid, year, doy, ndvi, snow, b in chunk:
        d = smoothers.greenup_doy(
            doy, ndvi, snow, b, smoother=smoother, fraction=fraction, window=tuple(cfg["window_doy"]), **opts,
        )
        out.append({"pixel_id": pid, "year": year, "doy": d})
    return out


def pixel_greenup(masks: list[str], smoother_list: list[str], fractions: list[float], workers: int = 8) -> pd.DataFrame:
    """Green-up DOY for every pixel-year under every (mask, smoother, fraction) combination."""
    cfg = config.load()["phenology"]
    frames = []
    for mask in masks:
        daily = load_daily(mask)
        base = baselines(daily)
        items = list(_pixel_years(daily, base))
        chunks = [items[i::workers] for i in range(workers)]
        for smoother, fraction in product(smoother_list, fractions):
            with ProcessPoolExecutor(max_workers=workers) as pool:
                rows = [r for part in pool.map(_fit_chunk, [(c, smoother, fraction, cfg, {}) for c in chunks]) for r in part]
            frames.append(pd.DataFrame(rows).assign(mask=mask, smoother=smoother, fraction=fraction))
        frames.append(base.rename("baseline").reset_index().assign(mask=mask, smoother="_baseline", fraction=np.nan, year=0))
    out = pd.concat(frames, ignore_index=True)
    return out


def yearly_baselines(daily: pd.DataFrame, pooled: pd.Series, min_obs: int = 5) -> pd.Series:
    """Per pixel-year dormant baseline, falling back to the pooled value when a year has too few observations."""
    cfg = config.load()["phenology"]
    lo, hi = cfg["baseline_exclude_doy"]
    sel = daily[daily["ndvi"].notna() & ((daily["doy"] < lo) | (daily["doy"] > hi))]
    g = sel.groupby(["pixel_id", "year"])["ndvi"]
    per_year = g.quantile(cfg["baseline_percentile"] / 100).where(g.count() >= min_obs)
    idx = pd.MultiIndex.from_frame(daily[["pixel_id", "year"]].drop_duplicates())
    per_year = per_year.reindex(idx)
    return per_year.fillna(pd.Series(idx.get_level_values(0).map(pooled), index=idx))


def primary_variant(daily: pd.DataFrame, baseline_percentile: float | None = None, workers: int = 8,
                    smoother: str | None = None, yearly_baseline: bool = False, **extra) -> pd.DataFrame:
    """Pixel green-up under the primary specification with one or more parameters overridden."""
    cfg = config.load()["phenology"]
    p = cfg["primary"]
    base = baselines(daily, baseline_percentile)
    if yearly_baseline:
        yb = yearly_baselines(daily, base)
        items = [(pid, yr, d, n, s_, yb.get((pid, yr), b)) for pid, yr, d, n, s_, b in _pixel_years(daily, base)]
    else:
        items = list(_pixel_years(daily, base))
    chunks = [items[i::workers] for i in range(workers)]
    args = [(c, smoother or p["smoother"], p["fraction"], cfg, extra) for c in chunks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        rows = [r for part in pool.map(_fit_chunk, args) for r in part]
    return pd.DataFrame(rows)


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cum = np.cumsum(w) / w.sum()
    return float(v[np.searchsorted(cum, 0.5)])


def aggregate(pix: pd.DataFrame, how: str, min_pixel_share: float = 0.3, weighted: bool = True,
              n_total: int | None = None) -> pd.DataFrame:
    """Area-weighted park-wide value per year.

    The sample has equal pixels per stratum, so each valid pixel is weighted by its stratum's
    dry-land share divided by the number of valid pixels in that stratum that year.
    """
    strata = {p["properties"]["pixel_id"]: p["properties"]["stratum"] for p in aoi.load_points()}
    shares = aoi.stratum_weights() if weighted else {s: 1.0 for s in set(strata.values())}
    df = pix.dropna(subset=["doy"]).copy()
    df["stratum"] = df["pixel_id"].map(strata)
    n_pixels = n_total or len(strata)
    rows = []
    for year, g in df.groupby("year"):
        counts = g["stratum"].value_counts()
        w = g["stratum"].map(lambda s: shares[s] / counts[s]).to_numpy()
        v = g["doy"].to_numpy()
        value = _weighted_median(v, w) if how == "median" else float(np.average(v, weights=w))
        share = len(g) / n_pixels
        rows.append({"year": year, "greenup_doy": value if share >= min_pixel_share else np.nan,
                     "n_pixels": len(g), "pixel_share": share})
    return pd.DataFrame(rows)


def by_stratum(pix: pd.DataFrame) -> pd.DataFrame:
    strata = {p["properties"]["pixel_id"]: p["properties"]["stratum"] for p in aoi.load_points()}
    df = pix.dropna(subset=["doy"]).assign(stratum=lambda d: d["pixel_id"].map(strata))
    return df.groupby(["stratum", "year"])["doy"].agg(["median", "count"]).reset_index()


def compare_mcd12q2(pix: pd.DataFrame, max_qa: int = 1) -> dict:
    """Pixel-year and annual agreement with MCD12Q2 MidGreenup (validation only, never used for tuning)."""
    ref = extract.load("mcd12q2")
    ref = ref[(ref["mid_qa"] <= max_qa) & ref["MidGreenup_doy"].notna()]
    m = pix.merge(ref[["pixel_id", "year", "MidGreenup_doy"]], on=["pixel_id", "year"]).dropna(subset=["doy"])
    diff = m["doy"] - m["MidGreenup_doy"]
    ann = m.groupby("year")[["doy", "MidGreenup_doy"]].median()
    return {
        "n_pixel_years": int(len(m)),
        "pixel_r": float(np.corrcoef(m["doy"], m["MidGreenup_doy"])[0, 1]) if len(m) > 2 else np.nan,
        "pixel_mae_days": float(diff.abs().mean()),
        "pixel_bias_days": float(diff.mean()),
        "annual_r": float(np.corrcoef(ann["doy"], ann["MidGreenup_doy"])[0, 1]) if len(ann) > 2 else np.nan,
        "annual_mae_days": float((ann["doy"] - ann["MidGreenup_doy"]).abs().mean()),
    }


def mcd12q2_annual(max_qa: int = 1) -> pd.DataFrame:
    """Area-weighted annual MCD12Q2 MidGreenup, for the independent-product comparison."""
    ref = extract.load("mcd12q2")
    ref = ref[(ref["mid_qa"] <= max_qa)].rename(columns={"MidGreenup_doy": "doy"})
    return aggregate(ref[["pixel_id", "year", "doy"]], "median")


def run() -> pd.DataFrame:
    cfg = config.load()
    mv = cfg["multiverse"]
    pix = pixel_greenup(mv["masks"], mv["smoothers"], mv["fractions"])
    nbar = pixel_greenup(["nbar"], ["savgol"], [cfg["phenology"]["primary"]["fraction"]])
    pix = pd.concat([pix, nbar], ignore_index=True)
    config.ensure_dirs()
    pix.to_csv(config.PROCESSED / "pixel_greenup.csv.gz", index=False)
    return pix


def load_pixels() -> pd.DataFrame:
    return pd.read_csv(config.PROCESSED / "pixel_greenup.csv.gz")


def select(pix: pd.DataFrame, mask: str, smoother: str, fraction: float) -> pd.DataFrame:
    return pix[(pix["mask"] == mask) & (pix["smoother"] == smoother) & np.isclose(pix["fraction"], fraction)]
