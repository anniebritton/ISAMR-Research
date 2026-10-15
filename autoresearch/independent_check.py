"""Independent real-data checks for the frozen autoresearch candidate. Run once, after freeze.sh.

The candidate joins the robustness grid only if it beats the pre-registered Savitzky-Golay baseline on
all three criteria fixed in prereg.md:
  1. held-out synthetic recovery (results/tables/autoresearch_final.json)
  2. agreement with MCD12Q2 MidGreenup on real pixels (pixel-year MAE and annual r)
  3. snow-off lag plausibility: fewer pixel-years whose green-up precedes that pixel's own melt
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from wapusk_greenup import config, method, phenology, smoothers

ROOT = Path(__file__).resolve().parents[1]


def melt_day(doy: np.ndarray, snow: np.ndarray, run: int = 7) -> float:
    """First day after which the pixel's MODIS snow flag reads snow-free on `run` consecutive flagged days.

    Days without a flag (NaN) are skipped rather than ending the run, so cloudy days do not
    shorten the snow season.
    """
    s = np.asarray(snow, float)
    d = np.asarray(doy, float)
    known = ~np.isnan(s)
    s, d = s[known], d[known]
    if s.size < run or s[0] != 1:
        return np.nan
    for i in range(s.size - run + 1):
        if (s[i:i + run] == 0).all():
            return float(d[i])
    return np.nan


def run() -> dict:
    lock = (ROOT / "results" / "method_lock.txt").read_text()
    frozen = re.search(r"sha256: ([0-9a-f]{64})", lock).group(1)
    actual = hashlib.sha256((ROOT / "src" / "wapusk_greenup" / "method.py").read_bytes()).hexdigest()
    if frozen != actual:
        raise SystemExit("method.py does not match the frozen hash in results/method_lock.txt")

    cfg = config.load()["phenology"]
    lo, hi = cfg["window_doy"]
    daily = phenology.load_daily("strict")
    daily = daily[(daily["doy"] >= lo) & (daily["doy"] <= hi)]
    base = phenology.baselines(phenology.load_daily("strict"))
    rows = []
    for (pid, year), g in daily.groupby(["pixel_id", "year"]):
        doy, ndvi, snow = g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy()
        b = base.get(pid, np.nan)
        rows.append({
            "pixel_id": pid, "year": year, "melt": melt_day(doy, snow),
            "baseline": smoothers.greenup_doy(doy, ndvi, snow, b, smoother="savgol", fraction=0.5),
            "candidate": method.greenup_doy(doy, ndvi, snow, b, 0.5),
        })
    df = pd.DataFrame(rows)

    out = {"method_sha256": actual}
    for name in ("baseline", "candidate"):
        pix = df[["pixel_id", "year", name]].rename(columns={name: "doy"})
        v = phenology.compare_mcd12q2(pix)
        has = df[name].notna() & df["melt"].notna()
        out[name] = {
            "valid_pixel_years": int(df[name].notna().sum()),
            "mcd12q2": v,
            "share_greenup_before_own_melt": float((df.loc[has, name] < df.loc[has, "melt"]).mean()),
            "median_lag_after_melt_days": float((df.loc[has, name] - df.loc[has, "melt"]).median()),
        }
    final = json.loads((ROOT / "results" / "tables" / "autoresearch_final.json").read_text())
    b, c = out["baseline"], out["candidate"]
    out["criteria"] = {
        "heldout_recovery": final["heldout"]["mean_capped_error"] < final["baselines"]["savgol"]["heldout"]["mean_capped_error"],
        "mcd12q2_pixel_mae": c["mcd12q2"]["pixel_mae_days"] < b["mcd12q2"]["pixel_mae_days"],
        "mcd12q2_annual_r": c["mcd12q2"]["annual_r"] > b["mcd12q2"]["annual_r"],
        "lag_plausibility": c["share_greenup_before_own_melt"] <= b["share_greenup_before_own_melt"],
    }
    out["joins_robustness_grid"] = all(out["criteria"].values())
    (ROOT / "results" / "tables" / "autoresearch_independent.json").write_text(json.dumps(out, indent=2, default=float))
    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, default=float))
