"""Synthetic pixel-seasons with known green-up crossings, for scoring candidate extractors.

Each season has a known noiseless NDVI curve, a snow-off day, real cloud-gap patterns resampled
from the MOD09GA strict mask (gap_masks.npz), Gaussian noise, and negative outliers that mimic
residual cloud. The truth is the crossing of the noiseless curve at baseline + fraction * amplitude.

Visible families (the loop scores against these): double_logistic, step_ramp, two_stage.
A further family and its seeds are held out from the loop and live outside the repository.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from wapusk_greenup.smoothers import crossing

DOY = np.arange(91, 301)
HERE = Path(__file__).resolve().parent
GAP_LIBRARY = HERE / "data" / "gap_masks.npz"
VISIBLE_FAMILIES = ("double_logistic", "step_ramp", "two_stage")


@dataclass
class Season:
    family: str
    doy: np.ndarray
    ndvi: np.ndarray        # observed, NaN where masked
    snow: np.ndarray        # 1 snow, 0 snow-free
    baseline: float         # estimated dormant baseline passed to the extractor
    fraction: float
    truth: float            # crossing of the noiseless curve


def _logistic(t, mid, k):
    return 1 / (1 + np.exp(-k * (t - mid)))


def curve_double_logistic(rng, base, amp):
    mid = rng.uniform(140, 195)
    k1 = rng.uniform(0.06, 0.25)
    sen = rng.uniform(235, 265)
    k2 = rng.uniform(0.03, 0.1)
    return base + amp * (_logistic(DOY, mid, k1) - _logistic(DOY, sen, k2)), mid - rng.uniform(0, 25)


def curve_step_ramp(rng, base, amp):
    """Snowmelt reveals already-green vegetation: a step at snow-off, then a linear ramp to peak."""
    snow_off = rng.uniform(130, 175)
    step = rng.uniform(0.2, 0.5)
    ramp = rng.uniform(15, 45)
    sen = rng.uniform(235, 265)
    rise = np.clip((DOY - snow_off) / ramp, 0, 1)
    y = np.where(DOY < snow_off, 0.0, step + (1 - step) * rise)
    y = y * (1 - _logistic(DOY, sen, 0.06))
    return base + amp * y, snow_off


def curve_two_stage(rng, base, amp):
    """Understory then canopy: two logistic rises separated by a shoulder."""
    m1 = rng.uniform(140, 180)
    gap = rng.uniform(10, 25)
    shoulder = rng.uniform(0.3, 0.6)
    sen = rng.uniform(235, 265)
    y = shoulder * _logistic(DOY, m1, 0.2) + (1 - shoulder) * _logistic(DOY, m1 + gap, 0.15)
    y = y * (1 - _logistic(DOY, sen, 0.06))
    return base + amp * y, m1 - rng.uniform(0, 20)


CURVES = {
    "double_logistic": curve_double_logistic,
    "step_ramp": curve_step_ramp,
    "two_stage": curve_two_stage,
}


def load_gap_masks() -> np.ndarray:
    """Boolean (n, len(DOY)) array: True where a real pixel-year had a strict-mask observation."""
    with np.load(GAP_LIBRARY) as f:
        return np.unpackbits(f["valid"], axis=1, count=len(DOY)).astype(bool)


def observe(rng, true_curve, base, snow_off, gaps, family, fraction) -> Season:
    snow = (DOY < snow_off).astype(float)
    # Occasional late snowfall after melt.
    if rng.random() < 0.2:
        start = int(rng.uniform(snow_off + 3, snow_off + 25))
        snow[(DOY >= start) & (DOY < start + rng.integers(1, 4))] = 1
    real = gaps[rng.integers(len(gaps))]
    visible = real & (snow == 0)
    noise = rng.normal(0, 0.02, DOY.size)
    outlier = rng.random(DOY.size) < 0.05
    noise[outlier] -= rng.uniform(0.05, 0.2, outlier.sum())
    ndvi = np.where(visible, true_curve + noise, np.nan)
    amp = true_curve.max() - base
    truth = crossing(DOY.astype(float), true_curve, base, fraction, min(0.05, amp / 2))
    return Season(family, DOY.copy(), ndvi, snow, base + rng.normal(0, 0.01), fraction, truth)


def generate(n: int, seed: int, families=VISIBLE_FAMILIES, curve_fns=None, gaps=None) -> list[Season]:
    rng = np.random.default_rng(seed)
    gaps = load_gap_masks() if gaps is None else gaps
    curve_fns = curve_fns or CURVES
    seasons = []
    while len(seasons) < n:
        family = families[len(seasons) % len(families)]
        base = rng.uniform(0.1, 0.45)
        amp = rng.uniform(0.12, 0.5)
        curve, snow_off = curve_fns[family](rng, base, amp)
        fraction = 0.5 if rng.random() < 0.5 else 0.15
        s = observe(rng, curve, base, snow_off, gaps, family, fraction)
        if not np.isnan(s.truth) and np.sum(~np.isnan(s.ndvi)) >= 15:
            seasons.append(s)
    return seasons


def build_gap_library(out: Path = GAP_LIBRARY) -> int:
    """Derive the gap library from cached MOD09GA extracts (run once by a person, then committed)."""
    from wapusk_greenup import phenology

    daily = phenology.load_daily("strict")
    daily = daily[(daily["doy"] >= DOY[0]) & (daily["doy"] <= DOY[-1])]
    wide = daily.assign(valid=daily["ndvi"].notna()).pivot_table(
        index=["pixel_id", "year"], columns="doy", values="valid", aggfunc="max", fill_value=False)
    wide = wide.reindex(columns=DOY, fill_value=False).to_numpy(bool)
    wide = wide[wide.sum(axis=1) >= 15]
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, valid=np.packbits(wide, axis=1))
    return len(wide)
