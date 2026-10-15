"""Run once, by a person, before the loop starts. Never run by the agent.

Creates the held-out benchmark and the integrity lock outside the repository:
    $WAPUSK_HELDOUT_DIR (default ~/.wapusk-autoresearch)/
        heldout.json     seeds and families for the final score
        templates.npz    normalised real NDVI season shapes (the held-out curve family)
        lock.json        SHA-256 of evaluate.py, synth.py, and the gap library

Also builds the committed gap library (autoresearch/data/gap_masks.npz) if it is missing.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import synth  # noqa: E402

LOCKED = [HERE / "evaluate.py", HERE / "synth.py", synth.GAP_LIBRARY]


def heldout_dir() -> Path:
    return Path(os.environ.get("WAPUSK_HELDOUT_DIR", Path.home() / ".wapusk-autoresearch"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def templates(min_obs: int = 40, max_templates: int = 400, seed: int | None = None) -> np.ndarray:
    """Clean real pixel-years, smoothed with the Whittaker baseline and normalised to 0-1."""
    from wapusk_greenup import phenology, smoothers

    rng = np.random.default_rng(seed)
    daily = phenology.load_daily("strict")
    base = phenology.baselines(daily)
    grid = synth.DOY.astype(float)
    out = []
    for (pid, _), g in daily.groupby(["pixel_id", "year"]):
        g = g[(g["doy"] >= grid[0]) & (g["doy"] <= grid[-1])]
        if g["ndvi"].notna().sum() < min_obs:
            continue
        t, y = smoothers.prepare(g["doy"].to_numpy(), g["ndvi"].to_numpy(), g["snow"].to_numpy(), base[pid])
        c = smoothers.whittaker(t, y, grid)
        lo, hi = base[pid], c.max()
        if hi - lo < 0.1:
            continue
        out.append(np.clip((c - lo) / (hi - lo), 0, 1))
    out = np.array(out)
    return out[rng.permutation(len(out))[:max_templates]]


def main() -> None:
    if not synth.GAP_LIBRARY.exists():
        print(f"gap library: {synth.build_gap_library()} pixel-year masks")
    d = heldout_dir()
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    np.savez_compressed(d / "templates.npz", curves=templates())
    spec = {
        "families": ["template", "double_logistic", "step_ramp", "two_stage"],
        "seeds": [secrets.randbelow(2**31) for _ in range(3)],
        "n_per_seed": 600,
    }
    (d / "heldout.json").write_text(json.dumps(spec, indent=1))
    (d / "lock.json").write_text(json.dumps({str(p.relative_to(HERE.parent)): sha256(p) for p in LOCKED}, indent=1))
    print(f"held-out benchmark and lock written to {d}")


if __name__ == "__main__":
    main()
