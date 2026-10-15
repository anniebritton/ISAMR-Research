"""Fixed scorer for the autoresearch loop. The agent cannot edit this file.

run_loop.sh verifies this file's SHA-256 against a value stored outside the repository before every run.

Score (lower is better):
    mean capped error   |estimate - truth| capped at 30 days; a NaN estimate counts as 30
  + complexity          0.001 per non-blank, non-comment line of method.py
  + speed               0.05 per ms of mean runtime above 50 ms per call

Modes:
    visible (default)   1,800 seasons from the three visible families, seed 1
    final               visible + held-out family and seeds from $WAPUSK_HELDOUT_DIR, plus the
                        three baseline smoothers on the same seasons for comparison
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import synth  # noqa: E402

METHOD = HERE.parent / "src" / "wapusk_greenup" / "method.py"
CAP = 30.0
VISIBLE_N = 1800
VISIBLE_SEED = 1


def complexity(path: Path = METHOD) -> int:
    n = 0
    in_doc = False
    for line in path.read_text().splitlines():
        s = line.strip()
        if s.startswith('"""') or s.startswith("'''"):
            in_doc = not in_doc if s.count('"""') + s.count("'''") == 1 else in_doc
            continue
        if in_doc or not s or s.startswith("#"):
            continue
        n += 1
    return n


def score_fn(fn, seasons) -> dict:
    errors, signed, fails = [], [], 0
    by_family: dict[str, list[float]] = {}
    t0 = time.perf_counter()
    for s in seasons:
        try:
            est = float(fn(s.doy.copy(), s.ndvi.copy(), s.snow.copy(), s.baseline, s.fraction))
        except Exception:
            est = np.nan
        if np.isnan(est):
            err = CAP
            fails += 1
        else:
            err = min(abs(est - s.truth), CAP)
            signed.append(est - s.truth)
        errors.append(err)
        by_family.setdefault(s.family, []).append(err)
    ms = 1000 * (time.perf_counter() - t0) / len(seasons)
    return {
        "mean_capped_error": float(np.mean(errors)),
        "median_abs_error": float(np.median(errors)),
        "bias_days": float(np.mean(signed)) if signed else float("nan"),
        "fail_rate": fails / len(seasons),
        "ms_per_call": ms,
        "by_family": {k: float(np.mean(v)) for k, v in by_family.items()},
    }


def total(result: dict, loc: int) -> float:
    return result["mean_capped_error"] + 0.001 * loc + 0.05 * max(0.0, result["ms_per_call"] - 50)


def load_candidate():
    sys.path.insert(0, str(HERE.parent / "src"))
    import wapusk_greenup.method as method

    return importlib.reload(method).greenup_doy


def baselines():
    from wapusk_greenup import smoothers

    return {
        name: (lambda n: lambda doy, ndvi, snow, b, f: smoothers.greenup_doy(doy, ndvi, snow, b, smoother=n, fraction=f))(name)
        for name in smoothers.SMOOTHERS
    }


def heldout_seasons() -> list:
    d = Path(os.environ.get("WAPUSK_HELDOUT_DIR", Path.home() / ".wapusk-autoresearch"))
    spec = json.loads((d / "heldout.json").read_text())
    with np.load(d / "templates.npz") as f:
        templates = f["curves"]

    def curve_template(rng, base, amp):
        """Real smoothed pixel-year shapes, normalised, shifted, and rescaled."""
        t = templates[rng.integers(len(templates))]
        shift = int(rng.integers(-15, 16))
        shape = np.interp(synth.DOY - shift, synth.DOY, t, left=t[0], right=t[-1])
        mid = synth.DOY[np.argmax(shape >= 0.5)]
        return base + amp * shape, mid - rng.uniform(0, 20)

    fns = {**synth.CURVES, "template": curve_template}
    seasons = []
    for seed in spec["seeds"]:
        seasons += synth.generate(spec["n_per_seed"], seed, families=tuple(spec["families"]), curve_fns=fns)
    return seasons


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["visible", "final"], default="visible")
    args = ap.parse_args()

    loc = complexity()
    visible = synth.generate(VISIBLE_N, VISIBLE_SEED)
    cand = score_fn(load_candidate(), visible)
    out = {"mode": args.mode, "loc": loc, "visible": cand, "score": total(cand, loc)}
    if args.mode == "final":
        held = heldout_seasons()
        out["heldout"] = score_fn(load_candidate(), held)
        out["heldout_score"] = total(out["heldout"], loc)
        out["baselines"] = {
            name: {"visible": score_fn(fn, visible), "heldout": score_fn(fn, held)} for name, fn in baselines().items()
        }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
