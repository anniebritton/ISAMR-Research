"""Post-hoc checks requested by the referee report (results/review.md).

Everything here was added after the confirmatory run and is listed under Deviations in prereg.md.
None of it changes the confirmatory estimates; it qualifies how they are interpreted.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import statsmodels.api as sm

from . import aoi, config, drivers, extract, phenology, stats

OUT = config.TABLES / "revision_checks.json"


def _fast(series: pd.DataFrame, drv: pd.DataFrame, x1: str = "snow_off", x2: str = "tdd") -> dict:
    """H1 slope, H2 standardized slope, and H3 delta R^2 without inner bootstraps."""
    d = series.merge(drv, on="year").dropna(subset=["greenup_doy", x1, x2])
    y = d["greenup_doy"].to_numpy(float)
    z1 = stats.standardize(d[x1].to_numpy(float))
    z2 = stats.standardize(d[x2].to_numpy(float))
    m1 = sm.OLS(y, sm.add_constant(z1)).fit()
    m2 = sm.OLS(y, sm.add_constant(np.column_stack([z1, z2]))).fit()
    f, p3, _ = m2.compare_f_test(m1)
    return {"n": len(d), "h1_slope": stats.theil_sen(d["year"].to_numpy(float), y)["slope"],
            "h2_slope_per_sd": float(m1.params[1]), "h2_p": float(m1.pvalues[1]), "h2_r2": float(m1.rsquared),
            "h3_delta_r2": float(m2.rsquared - m1.rsquared), "h3_p": float(p3), "m2_r2": float(m2.rsquared)}


def _ci(values: list[float]) -> list[float]:
    return [float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))]


def pixel_bootstrap(primary: pd.DataFrame, drv: pd.DataFrame, reps: int = 500, seed: int = 7) -> dict:
    """Resample pixels within stratum within year, re-aggregate, and refit, to carry retrieval
    variability through H1-H3 (referee issue 4)."""
    strata = {p["properties"]["pixel_id"]: p["properties"]["stratum"] for p in aoi.load_points()}
    df = primary.dropna(subset=["doy"]).assign(stratum=lambda d: d["pixel_id"].map(strata))
    groups = [g for _, g in df.groupby(["year", "stratum"])]
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(reps):
        sample = pd.concat([g.iloc[rng.integers(0, len(g), len(g))] for g in groups])
        draws.append(_fast(phenology.aggregate(sample, "median"), drv))
    out = {k: _ci([d[k] for d in draws]) for k in ("h1_slope", "h2_slope_per_sd", "h3_delta_r2", "m2_r2")}
    out["share_h3_p_below_0.05"] = float(np.mean([d["h3_p"] < 0.05 for d in draws]))
    out["share_h2_p_below_0.05"] = float(np.mean([d["h2_p"] < 0.05 for d in draws]))
    out["reps"] = reps
    return out


def year_bootstrap(d: pd.DataFrame, reps: int = 2000, seed: int = 11) -> dict:
    """CIs over resampled years for commonality shares, combined-model coefficients, and LOO RMSE."""
    rng = np.random.default_rng(seed)
    rows = []
    n = len(d)
    for _ in range(reps):
        b = d.iloc[rng.integers(0, n, n)]
        if b["snow_off"].std() == 0 or b["tdd"].std() == 0:
            continue
        c = stats.commonality(b, "greenup_doy", "snow_off", "tdd")
        z = np.column_stack([stats.standardize(b["snow_off"].to_numpy(float)), stats.standardize(b["tdd"].to_numpy(float))])
        m2 = sm.OLS(b["greenup_doy"].to_numpy(float), sm.add_constant(z)).fit()
        rows.append({**c, "coef_snow_off": m2.params[1], "coef_tdd": m2.params[2]})
    r = pd.DataFrame(rows)
    out = {k: _ci(r[k].tolist()) for k in r.columns}
    for k in ("unique_snow_off", "unique_tdd", "common"):
        out[f"{k}_share_of_explained"] = _ci((r[k] / r["total"]).tolist())
    return out


def leverage(d: pd.DataFrame) -> dict:
    y = d["greenup_doy"].to_numpy(float)
    z = np.column_stack([stats.standardize(d["snow_off"].to_numpy(float)), stats.standardize(d["tdd"].to_numpy(float))])
    m = sm.OLS(y, sm.add_constant(z)).fit()
    infl = m.get_influence()
    cooks = infl.cooks_distance[0]
    table = pd.DataFrame({"year": d["year"], "cooks_d": cooks, "leverage": infl.hat_matrix_diag})
    return {"top_cooks_d": table.sort_values("cooks_d", ascending=False).head(5).round(3).to_dict("records"),
            "threshold_4_over_n": 4 / len(d)}


def run() -> dict:
    cfg = config.load()
    p = cfg["phenology"]["primary"]
    pix = phenology.load_pixels()
    primary = phenology.select(pix, p["mask"], p["smoother"], p["fraction"])
    series = pd.read_csv(config.PROCESSED / "greenup_annual.csv")
    drv = drivers.load()
    d = series.merge(drv, on="year")
    conf = json.loads((config.TABLES / "confirmatory.json").read_text())
    out: dict = {}

    # Issue 2: commonality as shares of explained variance, with CIs.
    c = conf["commonality"]
    out["commonality_share_of_explained"] = {k: c[k] / c["total"] for k in ("unique_snow_off", "unique_tdd", "common")}
    out["year_bootstrap"] = year_bootstrap(d)

    # Issue 3: trend bounds across the grid, the matched Mallory period, and shifts in days.
    mv = pd.read_csv(config.TABLES / "multiverse.csv")
    out["grid_trend_bounds"] = {
        "ci_low_range": [float(mv["h1_ci_low"].min()), float(mv["h1_ci_low"].max())],
        "ci_high_range": [float(mv["h1_ci_high"].min()), float(mv["h1_ci_high"].max())],
        "n_specs_ci_below_minus_0.56": int((mv["h1_ci_low"] <= -0.56).sum()),
        "n_specs": int(len(mv)),
    }
    h = conf["hypotheses"]
    span = series["year"].max() - series["year"].min()
    out["primary_total_shift_days"] = {"estimate": h["h1_slope"] * span, "ci": [h["h1_ci_low"] * span, h["h1_ci_high"] * span]}
    sub = series[(series["year"] >= 2004) & (series["year"] <= 2016)]
    out["trend_2004_2016"] = stats.theil_sen(sub["year"].to_numpy(float), sub["greenup_doy"].to_numpy(float))
    mv_sub = []
    for mask in cfg["multiverse"]["masks"]:
        for smoother in cfg["multiverse"]["smoothers"]:
            s = phenology.aggregate(phenology.select(pix, mask, smoother, 0.15), "median")
            s = s[(s["year"] >= 2004) & (s["year"] <= 2016)]
            mv_sub.append({"mask": mask, "smoother": smoother,
                           **stats.theil_sen(s["year"].to_numpy(float), s["greenup_doy"].to_numpy(float))})
    out["onset_15pct_trend_2004_2016"] = mv_sub

    # Issue 4: propagate pixel-level retrieval variability; BCa for H3; MODIS snow-off as predictor.
    out["pixel_bootstrap"] = pixel_bootstrap(primary, drv)
    out["h3_bca"] = json.loads((config.TABLES / "statistical_robustness.json").read_text())["h3_bca"]
    out["modis_snow_off_predictor"] = _fast(series, drv.assign(snow_off=drv["snow_off_modis"]))

    # Issue 5: influence, leave-one-year-out for the extreme years, transformed TDD.
    out["leverage"] = leverage(d)
    out["drop_year"] = {int(y): _fast(series[series["year"] != y], drv) for y in (2004, 2009, 2023)}
    out["drop_2004_2009"] = _fast(series[~series["year"].isin([2004, 2009])], drv)
    out["tdd_rank"] = _fast(series, drv.assign(tdd=drv["tdd"].rank()))
    out["tdd_log1p"] = _fast(series, drv.assign(tdd=np.log1p(drv["tdd"])))
    out["years_snow_off_after_may31"] = drv.loc[drv["snow_off"] > 151, "year"].astype(int).tolist()

    # Issue 6: genuine station snow-off years only.
    st_years = drv.loc[drv["snow_off_station"].notna(), "year"]
    out["station_snow_off_only"] = _fast(series[series["year"].isin(st_years)],
                                         drv.assign(snow_off=drv["snow_off_station"]))

    # Issue 7: wetland vs other strata, and how often snow anchors constrain the crossing.
    strata = {f["properties"]["pixel_id"]: f["properties"]["stratum"] for f in aoi.load_points()}
    wet = {k for k, v in strata.items() if v == "wetland"}
    non_wet = primary[~primary["pixel_id"].isin(wet)]
    wet_only = primary[primary["pixel_id"].isin(wet)]
    out["by_wetland"] = {
        "non_wetland": _fast(phenology.aggregate(non_wet, "median", n_total=len(strata) - len(wet)), drv),
        "wetland_only": _fast(phenology.aggregate(wet_only, "median", n_total=len(wet)), drv),
    }
    out["anchor_binding"] = anchor_binding(primary)

    # Issue 8: park-wide vs park-wide MCD12Q2 agreement and annual bias over time.
    mcd = pd.read_csv(config.PROCESSED / "mcd12q2_annual.csv")
    m = series.merge(mcd, on="year", suffixes=("", "_mcd"))
    bias = m["greenup_doy"] - m["greenup_doy_mcd"]
    out["mcd12q2_parkwide"] = {
        "r": float(np.corrcoef(m["greenup_doy"], m["greenup_doy_mcd"])[0, 1]),
        "mean_bias_days": float(bias.mean()), "bias_sd_days": float(bias.std(ddof=1)),
        "bias_trend": stats.theil_sen(m["year"].to_numpy(float), bias.to_numpy(float)),
        "bias_2022_2024_mean": float(bias[m["year"] >= 2022].mean()),
        "bias_by_year": dict(zip(m["year"].astype(int).tolist(), bias.round(2).tolist())),
    }

    # Issue 10 and minor 7: population and numbers not yet in a table.
    meta = json.loads((config.ROOT / cfg["aoi"]["sample_points"]).read_text())["metadata"]
    out["population"] = {"candidates": meta["n_candidates"], "too_wet": meta["candidates_too_wet"],
                         "share_too_wet": meta["candidates_too_wet"] / meta["n_candidates"],
                         "dry_area_share": meta["dry_area_share"]}
    out["reported_numbers"] = reported_numbers(drv)
    OUT.write_text(json.dumps(out, indent=2, default=float))
    return out


def anchor_binding(primary: pd.DataFrame) -> dict:
    """Days from each pixel-year's first snow-free observation to its crossing.

    A crossing within a few days of the first clear view means the snow anchors, not observed
    growth, largely fix the date.
    """
    cfg = config.load()["phenology"]
    lo, hi = cfg["window_doy"]
    daily = phenology.load_daily(cfg["primary"]["mask"])
    daily = daily[(daily["doy"] >= lo) & (daily["doy"] <= hi) & daily["ndvi"].notna()]
    first = daily.groupby(["pixel_id", "year"])["doy"].min().rename("first_clear")
    m = primary.dropna(subset=["doy"]).merge(first.reset_index(), on=["pixel_id", "year"])
    gap = m["doy"] - m["first_clear"]
    return {"median_days_after_first_clear": float(gap.median()),
            "share_within_3_days": float((gap <= 3).mean()), "share_within_7_days": float((gap <= 7).mean()),
            "share_before_first_clear": float((gap < 0).mean()), "n": int(len(m))}


def reported_numbers(drv: pd.DataFrame) -> dict:
    """Values quoted in the report that were previously computed only interactively."""
    cfg = config.load()
    raw = extract.load("mod09ga")
    raw = raw[raw["date"].dt.dayofyear.between(*cfg["extract_doy"])]
    strict = phenology.load_daily("strict")
    base = phenology.baselines(strict)
    peak = strict[strict["doy"].between(190, 230)].groupby(["pixel_id", "year"])["ndvi"].quantile(0.9) \
        .groupby("pixel_id").median()
    ratio = (base / peak).dropna()
    with np.load(config.ROOT / "autoresearch" / "data" / "gap_masks.npz") as f:
        n_gap = int(f["valid"].shape[0])
    return {
        "usable_pixel_days_strict": float(raw["ndvi_strict"].notna().mean()),
        "usable_pixel_days_lenient": float(raw["ndvi_lenient"].notna().mean()),
        "dormant_baseline_median": float(base.median()),
        "summer_peak_median": float(peak.median()),
        "share_pixels_baseline_above_half_peak": float((ratio > 0.5).mean()),
        "tdd_sd": float(drv["tdd"].std(ddof=1)),
        "snow_off_sd": float(drv["snow_off"].std(ddof=1)),
        "gap_library_pixel_years": n_gap,
    }
