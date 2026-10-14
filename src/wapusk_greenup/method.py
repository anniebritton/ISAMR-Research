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

from __future__ import annotations

import numpy as np

from .smoothers import greenup_doy as _baseline_greenup


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
    return _baseline_greenup(doy, ndvi, snow, baseline, smoother="savgol", fraction=fraction)
