"""Candidate green-up extractor for the autoresearch loop.

This is the only file the autoresearch agent may edit (see autoresearch/program.md).
The confirmatory analysis never imports it; it uses smoothers.py.

Contract, fixed by autoresearch/evaluate.py:
    greenup_doy(doy, ndvi, snow, baseline, fraction) -> float
    doy       int array, every day of the growing-season window (DOY 91-300)
    ndvi      float array, NaN where cloud- or snow-masked
    snow      float array, 1 snow flagged, 0 snow-free, NaN unknown
    baseline  dormant (snow-free) NDVI for this pixel
    fraction  share of the seasonal amplitude that defines the crossing (0.5 or 0.15)
    returns   fractional day of year of the crossing, or NaN if the season cannot be resolved

Allowed imports: numpy, scipy. The function must be deterministic and take under 50 ms per call.
"""

import numpy as np
from scipy.signal import savgol_filter

from .smoothers import crossing, prepare, savgol


def greenup_doy(doy: np.ndarray, ndvi: np.ndarray, snow: np.ndarray, baseline: float, fraction: float = 0.5) -> float:
    # Pre-registered Savitzky-Golay baseline, except that only the persistent winter snowpack
    # becomes dormant pseudo-observations. prepare() turns every snow flag before the first clear
    # observation into a baseline value. When clouds hide the weeks after melt, a brief late
    # snowfall would then pin the curve to the dormant level partway up the rise. A transient
    # snowfall hides the canopy but doesn't make it dormant, so flags after melt are cleared here.
    snow = np.array(snow, dtype=float)
    valid = ~np.isnan(np.asarray(ndvi, dtype=float))
    if (snow == 0).any() and valid.any():
        melt, first = int(np.argmax(snow == 0)), int(np.argmax(valid))
        snow[melt:first] = 0
    if valid.sum() < 15 or np.isnan(baseline):
        return np.nan
    t, y = prepare(doy, ndvi, snow, baseline)
    grid = np.asarray(doy, dtype=float)
    curve = savgol(t, y, grid)
    # The upper envelope is kept for the curve's shape, since it undoes cloud dips on the rise. But
    # lifting every point below the fit also keeps only the positive half of clear-sky noise, so the
    # enveloped peak sits above the canopy's real maximum and raises the 50% threshold, giving late
    # crossings. The first, unlifted fit has no such selection; its peak sets the amplitude instead.
    # The threshold is only ever lowered, and crossing() still searches the enveloped curve.
    first_fit = savgol_filter(np.interp(grid, t, y), window_length=31, polyorder=2, mode="nearest")
    # Without the envelope, residual cloud near the peak drags that fit down. Cloud only lowers NDVI,
    # so one refit drops observations more than 3 robust sigma below it (MAD over clear observations
    # above the baseline; clipped and snow points sit on it). Symmetric clear-sky noise is kept, so
    # this doesn't recreate the envelope's upward bias. If no such points exist, NaN keeps everything.
    resid = y - np.interp(t, grid, first_fit)
    keep = ~(resid < -3 * 1.4826 * np.median(np.abs(resid[y > baseline])))
    first_fit = savgol_filter(np.interp(grid, t[keep], y[keep]), window_length=31, polyorder=2, mode="nearest")
    amp, amp0 = curve.max() - baseline, first_fit.max() - baseline
    scale = min(1.0, max(amp0, 0.0) / amp) if amp > 0 else 1.0
    # The pre-registered 0.10 amplitude floor rejects weak but real seasons (small amplitudes, or a
    # peak trimmed by early senescence). After smoothing, a 0.05 rise is still well above clear-sky
    # noise, and 0.05 is the floor used to define a resolvable season, so only flatter curves give NaN.
    return crossing(grid, curve, baseline, fraction * scale, min_amplitude=0.05)
