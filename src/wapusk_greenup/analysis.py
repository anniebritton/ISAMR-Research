"""Confirmatory analysis (run once, after prereg.md is committed) and the robustness grid."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from itertools import product

import numpy as np
import pandas as pd

from . import config, drivers, extract, phenology, stats

PREREG = config.ROOT / "prereg.md"
CONFIRMATORY = config.TABLES / "confirmatory.json"


def prereg_hash() -> str:
    return hashlib.sha256(PREREG.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=config.ROOT, capture_output=True, text=True).stdout.strip()


def _check_prereg_committed() -> None:
    if not PREREG.exists():
        raise SystemExit("prereg.md is missing; write and commit it before the confirmatory run.")
    if _git("status", "--porcelain", "--", "prereg.md"):
        raise SystemExit("prereg.md has uncommitted changes; commit it before the confirmatory run.")
    if not _git("log", "-1", "--format=%H", "--", "prereg.md"):
        raise SystemExit("prereg.md has never been committed.")


def annual_series(pix: pd.DataFrame, mask: str, smoother: str, fraction: float, aggregation: str) -> pd.DataFrame:
    return phenology.aggregate(phenology.select(pix, mask, smoother, fraction), aggregation)


def _hypotheses(series: pd.DataFrame, drv: pd.DataFrame, cfg: dict) -> dict:
    s = cfg["stats"]
    d = series.merge(drv, on="year")
    years = d["year"].to_numpy(float)
    y = d["greenup_doy"].to_numpy(float)
    out = {"h1_" + k: v for k, v in stats.theil_sen(years, y, s["alpha"]).items()}
    out.update({"h1_" + k: v for k, v in stats.mann_kendall(y, s["alpha"]).items()})
    out["h1_lag1"] = stats.lag1(y)
    out.update(stats.nested_models(d, "greenup_doy", "snow_off", "tdd", reps=s["bootstrap_reps"], seed=s["random_seed"]))
    return out


def confirmatory(force: bool = False) -> dict:
    """Pre-registered primary specification. Refuses to overwrite an existing result unless forced."""
    if CONFIRMATORY.exists() and not force:
        raise SystemExit(f"{CONFIRMATORY.relative_to(config.ROOT)} exists; the confirmatory run happens once.")
    _check_prereg_committed()
    cfg = config.load()
    p = cfg["phenology"]["primary"]
    pix = phenology.load_pixels()
    drv = drivers.load()
    primary_pix = phenology.select(pix, p["mask"], p["smoother"], p["fraction"])
    series = phenology.aggregate(primary_pix, p["aggregation"])
    series.to_csv(config.PROCESSED / "greenup_annual.csv", index=False)

    d = series.merge(drv, on="year")
    d["lag_days"] = d["greenup_doy"] - d["snow_off"]
    result = {
        "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": _git("rev-parse", "HEAD"),
        "prereg_sha256": prereg_hash(),
        "primary_spec": p,
        "hypotheses": _hypotheses(series, drv, cfg),
        "commonality": stats.commonality(d, "greenup_doy", "snow_off", "tdd"),
        "secondary_lag_trend": stats.theil_sen(d["year"].to_numpy(float), d["lag_days"].to_numpy(float)),
        "mcd12q2_validation": phenology.compare_mcd12q2(primary_pix),
        "years_with_valid_greenup": int(series["greenup_doy"].notna().sum()),
        "tdd_days_filled_from_era5": int(d["tdd_days_filled"].sum()),
    }
    config.ensure_dirs()
    CONFIRMATORY.write_text(json.dumps(result, indent=2, default=float))
    return result


def sensitivity() -> dict:
    """Checks reported next to the confirmatory result. None of these change the primary estimate."""
    cfg = config.load()
    p = cfg["phenology"]["primary"]
    pix = phenology.load_pixels()
    drv = drivers.load()
    out: dict = {}

    mcd = phenology.mcd12q2_annual()
    mcd.to_csv(config.PROCESSED / "mcd12q2_annual.csv", index=False)
    out["mcd12q2_trend"] = stats.theil_sen(mcd["year"].to_numpy(float), mcd["greenup_doy"].to_numpy(float))
    out["mcd12q2_trend"].update(stats.mann_kendall(mcd["greenup_doy"].to_numpy(float)))

    nbar = annual_series(pix, "nbar", "savgol", p["fraction"], p["aggregation"])
    out["nbar_trend"] = stats.theil_sen(nbar["year"].to_numpy(float), nbar["greenup_doy"].to_numpy(float))
    nbar_pix = phenology.select(pix, "nbar", "savgol", p["fraction"])
    out["nbar_mcd12q2_validation"] = phenology.compare_mcd12q2(nbar_pix)

    strat = phenology.by_stratum(phenology.select(pix, p["mask"], p["smoother"], p["fraction"]))
    strat.to_csv(config.TABLES / "greenup_by_stratum.csv", index=False)
    out["stratum_trends"] = {
        name: stats.theil_sen(g["year"].to_numpy(float), g["median"].to_numpy(float))
        for name, g in strat.groupby("stratum")
    }

    # Alternative predictor sources, swapped in one at a time.
    series_p = annual_series(pix, p["mask"], p["smoother"], p["fraction"], p["aggregation"])
    for label, swap in [("station_snow_off", {"snow_off": "snow_off_station_filled"}), ("era5_tdd", {"tdd": "tdd_era5"})]:
        alt = drv.copy()
        for target, source in swap.items():
            alt[target] = alt[source]
        out[f"alt_predictors_{label}"] = _hypotheses(series_p, alt, cfg)

    # Predictor cross-checks: station vs reanalysis vs MODIS snow-off, station vs ERA5 TDD.
    out["predictor_agreement"] = {
        "snow_off_station_vs_era5_r": float(drv[["snow_off_station", "snow_off_era5"]].corr().iloc[0, 1]),
        "snow_off_station_vs_modis_r": float(drv[["snow_off_station", "snow_off_modis"]].corr().iloc[0, 1]),
        "snow_off_era5_vs_modis_r": float(drv[["snow_off_era5", "snow_off_modis"]].corr().iloc[0, 1]),
        "tdd_station_vs_era5_r": float(drv[["tdd", "tdd_era5"]].corr().iloc[0, 1]),
    }
    expl = stats.spearman_table(
        series_p.merge(drv, on="year"), "greenup_doy",
        ["snow_off", "snow_off_station_filled", "snow_off_modis", "tdd", "tdd_era5", "max_snow_depth_cm",
         "spring_precip_mm"],
    )
    expl.to_csv(config.TABLES / "exploratory_correlations.csv", index=False)
    (config.TABLES / "sensitivity.json").write_text(json.dumps(out, indent=2, default=float))
    return out


def multiverse() -> pd.DataFrame:
    cfg = config.load()
    mv = cfg["multiverse"]
    p = cfg["phenology"]["primary"]
    pix = phenology.load_pixels()
    drv = drivers.load()
    rows = []
    for mask, smoother, fraction, agg in product(mv["masks"], mv["smoothers"], mv["fractions"], mv["aggregations"]):
        series = annual_series(pix, mask, smoother, fraction, agg)
        h = _hypotheses(series, drv, cfg)
        rows.append({
            "mask": mask, "smoother": smoother, "fraction": fraction, "aggregation": agg,
            "primary": (mask, smoother, fraction, agg) == (p["mask"], p["smoother"], p["fraction"], p["aggregation"]),
            "n_years": h["h1_n"],
            "h1_slope": h["h1_slope"], "h1_ci_low": h["h1_ci_low"], "h1_ci_high": h["h1_ci_high"],
            "h1_mk_p": h["h1_mk_p"], "h1_tfpw_p": h["h1_tfpw_p"],
            "h2_slope_per_sd": h["h2_slope_per_sd"], "h2_p": h["h2_p"], "h2_r2": h["h2_r2"],
            "h3_delta_r2": h["h3_delta_r2"], "h3_p": h["h3_p"],
        })
    out = pd.DataFrame(rows)
    out.to_csv(config.TABLES / "multiverse.csv", index=False)
    return out


def power_analysis() -> dict:
    """Minimum detectable trend from the MCD12Q2 interannual SD, so the response itself is not inspected."""
    cfg = config.load()
    s = cfg["stats"]
    mcd = phenology.mcd12q2_annual()
    y = mcd["greenup_doy"].to_numpy(float)
    y = y[~np.isnan(y)]
    years = mcd.dropna()["year"].to_numpy(float)
    resid = y - np.polyval(np.polyfit(years, y, 1), years)
    sd = float(resid.std(ddof=2))
    rho = max(0.0, stats.lag1(resid))
    mdt, curve = stats.minimum_detectable_trend(sd, len(cfg["year_list"]), rho, s["mdt_power"], s["alpha"],
                                                s["mdt_sims"], s["random_seed"])
    curve.to_csv(config.TABLES / "power_curve.csv", index=False)
    out = {"reference": "MCD12Q2 MidGreenup_1, area-weighted median, detrended", "sd_days": sd, "lag1": rho,
           "n_years": len(cfg["year_list"]), "power": s["mdt_power"], "alpha": s["alpha"],
           "minimum_detectable_trend_days_per_year": mdt}
    (config.TABLES / "power_analysis.json").write_text(json.dumps(out, indent=2))
    return out


def parameter_sensitivity() -> pd.DataFrame:
    """Post-hoc, one-at-a-time sensitivity of H1-H3 to parameters the literature does not fix.

    Added after the confirmatory run (see the Deviations section of prereg.md); it cannot change
    the primary result. Each row moves one parameter of the primary specification.
    """
    from . import aoi, extract, station

    cfg = config.load()
    ph = cfg["phenology"]
    p = ph["primary"]
    drv = drivers.load()
    daily = phenology.load_daily(p["mask"])
    rows = []

    def record(parameter: str, value, pix: pd.DataFrame | None = None, drv_alt: pd.DataFrame | None = None,
               series: pd.DataFrame | None = None) -> None:
        if series is None:
            series = phenology.aggregate(pix, p["aggregation"])
        h = _hypotheses(series, drv if drv_alt is None else drv_alt, cfg)
        rows.append({"parameter": parameter, "value": value, "n_years": h["h1_n"],
                     "mean_doy": float(series["greenup_doy"].mean()),
                     "h1_slope": h["h1_slope"], "h1_ci_low": h["h1_ci_low"], "h1_ci_high": h["h1_ci_high"],
                     "h2_slope_per_sd": h["h2_slope_per_sd"], "h2_p": h["h2_p"],
                     "h3_delta_r2": h["h3_delta_r2"], "h3_p": h["h3_p"], "m2_r2": h["m2_r2"]})

    primary = phenology.select(phenology.load_pixels(), p["mask"], p["smoother"], p["fraction"])
    record("primary", "as pre-registered", primary)
    for w in (21, 45):
        record("savgol_window_days", w, phenology.primary_variant(daily, savgol_window=w))
    for q in (2, 10):
        record("baseline_percentile", q, phenology.primary_variant(daily, baseline_percentile=q))
    for n in (10, 25):
        record("min_valid_obs", n, phenology.primary_variant(daily, min_valid=n))
    for a in (0.05, 0.15):
        record("min_amplitude", a, phenology.primary_variant(daily, min_amplitude=a))

    # Stricter water screen: keep only pixels with at most 2% surface water.
    dry = {f["properties"]["pixel_id"] for f in aoi.load_points() if f["properties"]["water_fraction"] <= 0.02}
    sub = primary[primary["pixel_id"].isin(dry)]
    record("max_water_fraction", 0.02, series=phenology.aggregate(sub, p["aggregation"], n_total=len(dry)))
    record("stratum_weighting", "unweighted", series=phenology.aggregate(primary, p["aggregation"], weighted=False))

    era = extract.load("era5")
    for thr in (30, 70):
        alt = drv.drop(columns="snow_off").merge(
            drivers.era5_snow_off(era, thr).rename(columns={"snow_off_era5": "snow_off"}), on="year")
        record("era5_snow_cover_threshold_pct", thr, primary, drv_alt=alt)

    temp = drivers.station_temperature_filled(station.load(), era)
    for end in (135, 166):
        t = drivers.tdd(temp, "tmean_filled_c", (cfg["drivers"]["tdd_window_doy"][0], end))
        alt = drv.drop(columns="tdd").merge(t.rename(columns={"tdd_tmean_filled_c": "tdd"})[["year", "tdd"]], on="year")
        record("tdd_window_end_doy", end, primary, drv_alt=alt)

    out = pd.DataFrame(rows)
    config.ensure_dirs()
    out.to_csv(config.TABLES / "parameter_sensitivity.csv", index=False)
    return out


def statistical_robustness() -> dict:
    """Post-hoc checks raised by the methods audit (docs/methods_justification.md)."""
    from . import station

    cfg = config.load()
    s = cfg["stats"]
    series = pd.read_csv(config.PROCESSED / "greenup_annual.csv")
    drv = drivers.load()
    d = series.merge(drv, on="year")
    years = d["year"].to_numpy(float)
    y = d["greenup_doy"].to_numpy(float)
    out: dict = {"mann_kendall_variants": stats.mann_kendall_variants(y, s["alpha"])}

    # Weatherhead et al. (1998) estimate noise from the series' own residuals; the pre-registered
    # MDT used MCD12Q2 so the response was not inspected. Both are reported, over a range of lag-1 values.
    resid = y - np.polyval(np.polyfit(years, y, 1), years)
    own_sd = float(resid.std(ddof=2))
    mcd_sd = json.loads((config.TABLES / "power_analysis.json").read_text())["sd_days"]
    out["mdt"] = {
        "own_series_sd_days": own_sd,
        "own_series_lag1": stats.lag1(resid),
        "by_source_and_lag1": [
            {"sd_source": src, "sd_days": sd, "lag1": rho,
             "mdt_days_per_year": stats.minimum_detectable_trend(sd, len(y), rho, s["mdt_power"], s["alpha"], 1000,
                                                                 s["random_seed"])[0]}
            for src, sd in (("this_study", own_sd), ("mcd12q2", mcd_sd)) for rho in (0.0, 0.1, 0.2, 0.3)
        ],
    }
    out["h3_bca"] = stats.delta_r2_bca(d, "greenup_doy", "snow_off", "tdd", s["bootstrap_reps"], s["random_seed"])

    # Homogenized AHCCD spring temperature (2001-2020) in place of spliced-station TDD.
    ah = station.ahccd_spring()
    da = d.merge(ah, on="year")
    temp = drivers.station_temperature_filled(station.load(), extract.load("era5"))
    temp = temp.assign(year=temp["date"].dt.year, month=temp["date"].dt.month)
    raw_spring = temp[temp["month"].isin([4, 5])].groupby("year")["tmean_filled_c"].mean().rename("raw_spring_tmean_c")
    da = da.merge(raw_spring.reset_index(), on="year")
    out["ahccd_check"] = {
        "years": [int(da["year"].min()), int(da["year"].max())],
        "n": int(len(da)),
        "raw_vs_ahccd_spring_tmean_r": float(np.corrcoef(da["raw_spring_tmean_c"], da["ahccd_spring_tmean_c"])[0, 1]),
        "raw_minus_ahccd_mean_c": float((da["raw_spring_tmean_c"] - da["ahccd_spring_tmean_c"]).mean()),
        "h3_with_ahccd": stats.nested_models(da, "greenup_doy", "snow_off", "ahccd_spring_tmean_c",
                                             reps=s["bootstrap_reps"], seed=s["random_seed"]),
        "h3_with_tdd_same_years": stats.nested_models(da, "greenup_doy", "snow_off", "tdd",
                                                      reps=s["bootstrap_reps"], seed=s["random_seed"]),
    }

    # ERA5-Land snow_cover is a function of modelled depth and overestimates snow duration
    # (Urraca & Gobron 2023), so report its offset from MODIS snow-off as well as their agreement.
    both = drv[["snow_off_era5", "snow_off_modis"]].dropna()
    out["era5_vs_modis_snow_off"] = {
        "mean_era5_minus_modis_days": float((both["snow_off_era5"] - both["snow_off_modis"]).mean()),
        "r": float(np.corrcoef(both["snow_off_era5"], both["snow_off_modis"])[0, 1]),
        "n": int(len(both)),
    }
    (config.TABLES / "statistical_robustness.json").write_text(json.dumps(out, indent=2, default=float))
    return out
