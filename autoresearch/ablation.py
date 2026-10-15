"""Post-hoc ablation of the autoresearch run. Run after freeze.sh and independent_check.py.

Scores every kept version of method.py, plus the frozen candidate with each substantive change
removed, on four things the loop never saw together:
  visible synthetic score (what the loop optimised), held-out synthetic error, real-pixel agreement
  with MCD12Q2 (pixel MAE and park-wide annual r), and the confirmatory statistics (H1-H3).
The aim is to see which changes carried over from the synthetic benchmark to the science.
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import evaluate  # noqa: E402
import synth  # noqa: E402

from wapusk_greenup import config, drivers, phenology, revision  # noqa: E402

METHOD = "src/wapusk_greenup/method.py"


def kept_versions() -> list[tuple[str, str]]:
    """(label, source) for the starting point and every kept autoresearch commit, oldest first."""
    log = subprocess.run(["git", "log", "--reverse", "--format=%h %s", "--", METHOD], cwd=ROOT,
                         capture_output=True, text=True, check=True).stdout.splitlines()
    out = []
    for line in log:
        sha, msg = line.split(" ", 1)
        label = "start (= pre-registered SG)" if not msg.startswith("autoresearch iter") else msg.split(":")[0].replace("autoresearch ", "")
        src = subprocess.run(["git", "show", f"{sha}:{METHOD}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        out.append((label, src))
    return out


def component_ablations(final: str) -> list[tuple[str, str]]:
    """The frozen candidate with one substantive change undone at a time."""
    edits = {
        "final without amplitude-floor change (0.05 -> 0.10)": ("min_amplitude=0.05", "min_amplitude=0.10"),
        "final without robust amplitude rescaling": ("fraction * scale", "fraction"),
        "final without post-melt snow-flag clearing": ("        snow[np.argmax(snow == 0) : np.argmax(valid)] = 0", "        pass"),
    }
    out = []
    for label, (old, new) in edits.items():
        if old not in final:
            raise SystemExit(f"cannot build ablation {label!r}: pattern not found")
        out.append((label, final.replace(old, new)))
    return out


def load(source: str, name: str):
    mod = types.ModuleType(f"wapusk_greenup._ablation_{name}")
    mod.__package__ = "wapusk_greenup"
    exec(compile(source, f"<{name}>", "exec"), mod.__dict__)
    return mod.greenup_doy


def real_data(fn, daily: pd.DataFrame, base: pd.Series, drv: pd.DataFrame, mcd: pd.DataFrame) -> dict:
    rows = []
    for (pid, year), g in daily.groupby(["pixel_id", "year"]):
        rows.append({"pixel_id": pid, "year": year,
                     "doy": fn(g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy(), base.get(pid, np.nan), 0.5)})
    pix = pd.DataFrame(rows)
    v = phenology.compare_mcd12q2(pix)
    series = phenology.aggregate(pix, "median")
    m = series.merge(mcd, on="year", suffixes=("", "_mcd"))
    h = revision._fast(series, drv)
    return {"valid_pixel_years": int(pix["doy"].notna().sum()), "pixel_mae_days": v["pixel_mae_days"],
            "pixel_bias_days": v["pixel_bias_days"],
            "parkwide_annual_r": float(np.corrcoef(m["greenup_doy"], m["greenup_doy_mcd"])[0, 1]),
            "h1_slope": h["h1_slope"], "h2_slope_per_sd": h["h2_slope_per_sd"], "h2_r2": h["h2_r2"],
            "h3_delta_r2": h["h3_delta_r2"], "m2_r2": h["m2_r2"]}


def main() -> None:
    lo, hi = config.load()["phenology"]["window_doy"]
    full = phenology.load_daily("strict")
    base = phenology.baselines(full)
    daily = full[(full["doy"] >= lo) & (full["doy"] <= hi)]
    drv = drivers.load()
    mcd = pd.read_csv(config.PROCESSED / "mcd12q2_annual.csv")
    visible = synth.generate(evaluate.VISIBLE_N, evaluate.VISIBLE_SEED)
    held = evaluate.heldout_seasons()

    versions = kept_versions()
    versions += component_ablations(versions[-1][1])
    rows = []
    for i, (label, src) in enumerate(versions):
        fn = load(src, str(i))
        vis = evaluate.score_fn(fn, visible)
        ho = evaluate.score_fn(fn, held)
        row = {"version": label, "visible_error": vis["mean_capped_error"], "heldout_error": ho["mean_capped_error"],
               "heldout_template_error": ho["by_family"].get("template"), "heldout_fail_rate": ho["fail_rate"],
               **real_data(fn, daily, base, drv, mcd)}
        rows.append(row)
        print(f"{label}: visible {row['visible_error']:.3f} heldout {row['heldout_error']:.3f} "
              f"annual r {row['parkwide_annual_r']:.3f} pixel MAE {row['pixel_mae_days']:.2f}", flush=True)
    out = pd.DataFrame(rows)
    out.to_csv(config.TABLES / "autoresearch_ablation.csv", index=False)


if __name__ == "__main__":
    main()
