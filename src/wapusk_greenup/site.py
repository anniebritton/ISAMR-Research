"""Build site/data.json, the data behind the interactive research brief (site/index.html)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import aoi, config, drivers, extract, phenology, smoothers

SITE = config.ROOT / "site"


def _r(x, nd: int = 2):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), nd)


def seasons(per_stratum: int = 3, seed: int = 3) -> list[dict]:
    """Observed NDVI, snow anchors, fitted curve, and crossing for a few pixels in every stratum and year."""
    cfg = config.load()["phenology"]
    lo, hi = cfg["window_doy"]
    full = phenology.load_daily(cfg["primary"]["mask"])
    base = phenology.baselines(full)
    daily = full[(full["doy"] >= lo) & (full["doy"] <= hi)]
    mcd = extract.load("mcd12q2")
    mcd = mcd[mcd["mid_qa"] <= 1].set_index(["pixel_id", "year"])["MidGreenup_doy"]
    rng = np.random.default_rng(seed)
    pts = aoi.load_points()
    chosen = []
    for name in config.load()["aoi"]["strata"]:
        ids = [p["properties"]["pixel_id"] for p in pts if p["properties"]["stratum"] == name]
        chosen += [(int(i), name) for i in rng.choice(ids, per_stratum, replace=False)]
    grid = np.arange(lo, hi + 1, dtype=float)
    out = []
    for pid, name in chosen:
        for year, g in daily[daily["pixel_id"] == pid].groupby("year"):
            doy, ndvi, snow = g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy()
            b = base[pid]
            d = smoothers.greenup_doy(doy, ndvi, snow, b)
            obs = ~np.isnan(ndvi)
            entry = {"pixel": pid, "stratum": name, "year": int(year), "baseline": _r(b, 3),
                     "obs_doy": doy[obs].astype(int).tolist(), "obs_ndvi": [_r(v, 3) for v in ndvi[obs]],
                     "snow_doy": doy[(snow == 1) & ~obs].astype(int).tolist(),
                     "greenup": _r(d, 1), "mcd12q2": _r(mcd.get((pid, year)), 0)}
            if np.sum(obs) >= cfg["min_valid_obs"]:
                t, y = smoothers.prepare(doy, ndvi, snow, b)
                curve = smoothers.savgol(t, y, grid)
                entry["curve_doy"] = grid[::2].astype(int).tolist()
                entry["curve_ndvi"] = [_r(v, 3) for v in curve[::2]]
            out.append(entry)
    return out


def build() -> dict:
    t = config.TABLES
    conf = json.loads((t / "confirmatory.json").read_text())
    sens = json.loads((t / "sensitivity.json").read_text())
    rev = json.loads((t / "revision_checks.json").read_text())
    power = json.loads((t / "power_analysis.json").read_text())
    series = pd.read_csv(config.PROCESSED / "greenup_annual.csv")
    mcd = pd.read_csv(config.PROCESSED / "mcd12q2_annual.csv")
    drv = drivers.load()
    mv = pd.read_csv(t / "multiverse.csv")
    par = pd.read_csv(t / "parameter_sensitivity.csv")
    abl = pd.read_csv(t / "autoresearch_ablation.csv")
    ledger = [json.loads(line) for line in (config.ROOT / "autoresearch" / "ledger.jsonl").read_text().splitlines()]
    indep = json.loads((t / "autoresearch_independent.json").read_text())
    final = json.loads((t / "autoresearch_final.json").read_text())
    h = conf["hypotheses"]

    annual = series.merge(drv, on="year").merge(mcd[["year", "greenup_doy"]].rename(columns={"greenup_doy": "mcd12q2"}), on="year")
    data = {
        "headline": {
            "trend": [h["h1_slope"], h["h1_ci_low"], h["h1_ci_high"]],
            "mdt": power["minimum_detectable_trend_days_per_year"],
            "mean_doy": float(series["greenup_doy"].mean()), "sd_doy": float(series["greenup_doy"].std(ddof=1)),
            "h2": [h["h2_slope_per_sd"], h["h2_ci_low"], h["h2_ci_high"], h["h2_r2"]],
            "h3": [h["h3_delta_r2"], rev["h3_bca"]["bca_ci_low"], rev["h3_bca"]["bca_ci_high"], h["h3_p"]],
            "m2_r2": h["m2_r2"], "loo": [h["loo_rmse_m2"], h["loo_rmse_m1"], h["loo_rmse_mean_only"]],
            "mcd_r": rev["mcd12q2_parkwide"]["r"], "trend_2004_2016": rev["trend_2004_2016"],
        },
        "boundary": aoi.boundary_geojson()["features"][0]["geometry"]["coordinates"][0][::4],
        "points": [{"id": p["properties"]["pixel_id"], "stratum": p["properties"]["stratum"],
                    "lon": p["geometry"]["coordinates"][0], "lat": p["geometry"]["coordinates"][1]} for p in aoi.load_points()],
        "annual": [{"year": int(r.year), "greenup": _r(r.greenup_doy, 1), "mcd12q2": _r(r.mcd12q2, 1),
                    "snow_off": _r(r.snow_off, 0), "tdd": _r(r.tdd, 1), "n_pixels": int(r.n_pixels)}
                   for r in annual.itertuples()],
        "multiverse": [{"label": f"{r.mask} / {r.smoother.replace('_', ' ')} / {int(r.fraction * 100)}% / {r.aggregation}",
                        "primary": bool(r.primary), "slope": r.h1_slope, "lo": r.h1_ci_low, "hi": r.h1_ci_high,
                        "h2": r.h2_slope_per_sd, "h3": r.h3_delta_r2} for r in mv.itertuples()],
        "parameters": [{"parameter": r.parameter, "value": str(r.value), "n_years": int(r.n_years),
                        "slope": _r(r.h1_slope, 3), "lo": _r(r.h1_ci_low, 3), "hi": _r(r.h1_ci_high, 3),
                        "h2": _r(r.h2_slope_per_sd, 2), "h3": _r(r.h3_delta_r2, 3)} for r in par.itertuples()],
        "agent": {
            "ledger": [{"iteration": r["iteration"], "score": _r(r["score"], 4) if r["score"] is not None else None,
                        "kept": r["kept"], "cost": _r(r["cost_usd"], 2),
                        "rationale": (r["rationale"] or "")[:600]} for r in ledger],
            "start_score": 3.1824,
            "ablation": [{"version": r.version, "visible": _r(r.visible_error, 4), "heldout": _r(r.heldout_error, 4),
                          "annual_r": _r(r.parkwide_annual_r, 3), "pixel_mae": _r(r.pixel_mae_days, 2)} for r in abl.itertuples()],
            "criteria": indep["criteria"],
            "heldout": {"candidate": final["heldout"]["mean_capped_error"],
                        **{k: v["heldout"]["mean_capped_error"] for k, v in final["baselines"].items()}},
            "total_cost": sum(r["cost_usd"] or 0 for r in ledger),
            "coding": pd.read_csv(config.ROOT / "autoresearch" / "iteration_coding.csv").to_dict("records"),
            "contributions": pd.read_csv(config.TABLES / "agent_contributions.csv").to_dict("records"),
        },
        "stratum_trends": sens["stratum_trends"],
        "seasons": seasons(),
    }
    SITE.mkdir(exist_ok=True)
    (SITE / "data.json").write_text(json.dumps(data, separators=(",", ":"), default=float))
    return data
