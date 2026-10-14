"""Baseline green-up extractors used by the confirmatory analysis and the robustness grid.

All functions are pure: one pixel-year of daily observations in, one day of year out.
The autoresearch agent never edits this file; its candidate lives in method.py.

Conventions for one pixel-year:
    doy       integer day of year for every day in the growing-season window
    ndvi      NDVI, NaN where cloud- or snow-masked
    snow      1 where MODIS flagged snow, 0 where clear of snow, NaN where unknown
    baseline  per-pixel dormant (snow-free) NDVI, Beck et al. (2006)
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy import sparse
from scipy.optimize import OptimizeWarning, curve_fit
from scipy.sparse.linalg import spsolve
from scipy.signal import savgol_filter

SMOOTHERS = ("savgol", "double_logistic", "whittaker")


def prepare(doy: np.ndarray, ndvi: np.ndarray, snow: np.ndarray, baseline: float) -> tuple[np.ndarray, np.ndarray]:
    """Observations plus snow pseudo-observations at the baseline.

    Snow-flagged days before the first and after the last snow-free observation are dormant,
    so they enter as baseline values. Observed NDVI below the baseline is clipped to it.
    """
    doy = np.asarray(doy, dtype=float)
    ndvi = np.asarray(ndvi, dtype=float)
    snow = np.asarray(snow, dtype=float)
    valid = ~np.isnan(ndvi)
    if not valid.any():
        return np.array([]), np.array([])
    first, last = doy[valid].min(), doy[valid].max()
    pseudo = (~valid) & (snow == 1) & ((doy < first) | (doy > last))
    t = np.concatenate([doy[valid], doy[pseudo]])
    y = np.concatenate([np.maximum(ndvi[valid], baseline), np.full(pseudo.sum(), baseline)])
    order = np.argsort(t)
    return t[order], y[order]


def _upper_envelope(t: np.ndarray, y: np.ndarray, grid: np.ndarray, fit, iterations: int = 2) -> np.ndarray:
    """Chen et al. (2004) style: observations below the fit are treated as residual contamination."""
    y = y.copy()
    curve = fit(y)
    for _ in range(iterations):
        y = np.maximum(y, np.interp(t, grid, curve))
        curve = fit(y)
    return curve


def savgol(t: np.ndarray, y: np.ndarray, grid: np.ndarray, window: int = 31, order: int = 2) -> np.ndarray:
    def fit(values: np.ndarray) -> np.ndarray:
        daily = np.interp(grid, t, values)
        return savgol_filter(daily, window_length=window, polyorder=order, mode="nearest")

    return _upper_envelope(t, y, grid, fit)


def whittaker(t: np.ndarray, y: np.ndarray, grid: np.ndarray, lam: float = 200.0) -> np.ndarray:
    """Weighted Whittaker smoother (Eilers 2003), second-order differences, zero weight on gaps."""
    n = len(grid)
    idx = np.searchsorted(grid, t)
    d = sparse.diags([1.0, -2.0, 1.0], [0, 1, 2], shape=(n - 2, n))
    penalty = lam * (d.T @ d)

    def fit(values: np.ndarray) -> np.ndarray:
        w = np.zeros(n)
        z = np.zeros(n)
        np.add.at(w, idx, 1.0)
        np.add.at(z, idx, values)
        return spsolve((sparse.diags(w) + penalty).tocsc(), z)

    return _upper_envelope(t, y, grid, fit)


def _double_logistic(t, base, peak, k1, t1, k2, t2):
    return base + (peak - base) * (1 / (1 + np.exp(-k1 * (t - t1))) + 1 / (1 + np.exp(k2 * (t - t2))) - 1)


def double_logistic(t: np.ndarray, y: np.ndarray, grid: np.ndarray, baseline: float) -> np.ndarray | None:
    """Beck et al. (2006) double logistic with the baseline fixed at the dormant NDVI."""
    peak0 = np.percentile(y, 95)
    mid = baseline + 0.5 * (peak0 - baseline)
    above = t[y >= mid]
    t1_0 = above.min() if above.size else np.median(t)
    p0 = [peak0, 0.1, t1_0, 0.05, min(260.0, grid.max() - 20)]
    lo = [baseline, 0.01, grid.min(), 0.005, grid.min() + 30]
    hi = [1.0, 1.0, grid.max(), 1.0, grid.max() + 60]
    p0 = np.clip(p0, lo, hi)

    def f(tt, peak, k1, t1, k2, t2):
        return _double_logistic(tt, baseline, peak, k1, t1, k2, t2)

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            params, _ = curve_fit(f, t, y, p0=p0, bounds=(lo, hi), maxfev=5000)
    except (RuntimeError, ValueError):
        return None
    return f(grid, *params)


def crossing(grid: np.ndarray, curve: np.ndarray, baseline: float, fraction: float, min_amplitude: float) -> float:
    """First day before the peak where the curve reaches baseline + fraction * amplitude.

    Returns NaN for weak seasons and for crossings at the window start (left-censored).
    """
    peak_i = int(np.argmax(curve))
    amplitude = curve[peak_i] - baseline
    if amplitude < min_amplitude:
        return np.nan
    threshold = baseline + fraction * amplitude
    above = np.nonzero(curve[: peak_i + 1] >= threshold)[0]
    if above.size == 0 or above[0] == 0:
        return np.nan
    i = above[0]
    # Linear interpolation between the last day below and the first day at or above the threshold.
    y0, y1 = curve[i - 1], curve[i]
    return float(grid[i - 1] + (threshold - y0) / (y1 - y0) * (grid[i] - grid[i - 1]))


def greenup_doy(
    doy: np.ndarray,
    ndvi: np.ndarray,
    snow: np.ndarray,
    baseline: float,
    smoother: str = "savgol",
    fraction: float = 0.5,
    window: tuple[int, int] = (91, 300),
    min_valid: int = 15,
    min_amplitude: float = 0.10,
) -> float:
    doy = np.asarray(doy)
    keep = (doy >= window[0]) & (doy <= window[1])
    doy, ndvi, snow = doy[keep], np.asarray(ndvi, float)[keep], np.asarray(snow, float)[keep]
    if np.sum(~np.isnan(ndvi)) < min_valid or np.isnan(baseline):
        return np.nan
    t, y = prepare(doy, ndvi, snow, baseline)
    grid = np.arange(window[0], window[1] + 1, dtype=float)
    if smoother == "savgol":
        curve = savgol(t, y, grid)
    elif smoother == "whittaker":
        curve = whittaker(t, y, grid)
    elif smoother == "double_logistic":
        curve = double_logistic(t, y, grid, baseline)
        if curve is None:
            return np.nan
    else:
        raise ValueError(f"unknown smoother {smoother!r}")
    return crossing(grid, curve, baseline, fraction, min_amplitude)


def dormant_baseline(doy: np.ndarray, ndvi: np.ndarray, exclude: tuple[int, int] = (150, 250), percentile: float = 5) -> float:
    """Per-pixel dormant NDVI: low percentile of snow-free NDVI outside the main growing season, all years pooled."""
    doy = np.asarray(doy)
    ndvi = np.asarray(ndvi, float)
    sel = ~np.isnan(ndvi) & ((doy < exclude[0]) | (doy > exclude[1]))
    if sel.sum() < 5:
        return np.nan
    return float(np.percentile(ndvi[sel], percentile))
