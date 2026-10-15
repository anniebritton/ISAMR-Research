"""Trend estimation, power analysis, and driver models for n ~ 24 annual values."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pymannkendall as mk
import statsmodels.api as sm
from scipy import stats


def theil_sen(years: np.ndarray, y: np.ndarray, alpha: float = 0.05) -> dict:
    ok = ~np.isnan(y)
    res = stats.theilslopes(y[ok], years[ok], alpha=1 - alpha)
    return {"slope": res.slope, "ci_low": res.low_slope, "ci_high": res.high_slope, "intercept": res.intercept,
            "n": int(ok.sum())}


def mann_kendall(y: np.ndarray, alpha: float = 0.05) -> dict:
    y = y[~np.isnan(y)]
    orig = mk.original_test(y, alpha=alpha)
    # Yue et al. (2002) trend-free pre-whitening, robust to lag-1 autocorrelation.
    tfpw = mk.trend_free_pre_whitening_modification_test(y, alpha=alpha)
    return {"mk_tau": orig.Tau, "mk_p": orig.p, "tfpw_tau": tfpw.Tau, "tfpw_p": tfpw.p}


def mann_kendall_variants(y: np.ndarray, alpha: float = 0.05) -> dict:
    """Mann-Kendall p-values under the main autocorrelation corrections.

    TFPW (Yue et al. 2002) can inflate Type I error under strong autocorrelation (Buerger 2017),
    so the variance-correction (Hamed & Rao 1998) and pre-whitening (Yue & Wang 2002) variants are
    reported alongside it.
    """
    y = y[~np.isnan(y)]
    tests = {
        "original": mk.original_test,
        "hamed_rao": mk.hamed_rao_modification_test,
        "yue_wang_prewhitening": mk.pre_whitening_modification_test,
        "trend_free_prewhitening": mk.trend_free_pre_whitening_modification_test,
    }
    return {name: {"tau": float(fn(y, alpha=alpha).Tau), "p": float(fn(y, alpha=alpha).p)} for name, fn in tests.items()}


def delta_r2_bca(df: pd.DataFrame, response: str, first: str, second: str, reps: int = 5000, seed: int = 42) -> dict:
    """BCa bootstrap CI for the R^2 gained by adding the second predictor, plus adjusted R^2."""
    d = df[[response, first, second]].dropna()
    y = d[response].to_numpy()
    x1 = d[first].to_numpy()
    x2 = d[second].to_numpy()

    def gain(yy, a, b):
        return _ols(yy, np.column_stack([a, b])).rsquared - _ols(yy, a[:, None]).rsquared

    res = stats.bootstrap((y, x1, x2), gain, paired=True, n_resamples=reps, method="BCa",
                          random_state=np.random.default_rng(seed), vectorized=False)
    m1 = _ols(y, x1[:, None])
    m2 = _ols(y, np.column_stack([x1, x2]))
    return {"delta_r2": float(m2.rsquared - m1.rsquared), "bca_ci_low": float(res.confidence_interval.low),
            "bca_ci_high": float(res.confidence_interval.high), "adj_r2_m1": float(m1.rsquared_adj),
            "adj_r2_m2": float(m2.rsquared_adj)}


def lag1(y: np.ndarray) -> float:
    y = y[~np.isnan(y)]
    y = y - y.mean()
    return float(np.sum(y[1:] * y[:-1]) / np.sum(y * y))


def minimum_detectable_trend(
    sd: float, n: int, rho: float = 0.0, power: float = 0.8, alpha: float = 0.05, sims: int = 2000,
    seed: int = 42, slopes: np.ndarray | None = None,
) -> tuple[float, pd.DataFrame]:
    """Smallest |slope| (days/yr) that Mann-Kendall detects with the requested power under AR(1) noise."""
    rng = np.random.default_rng(seed)
    slopes = np.arange(0.05, 2.01, 0.05) if slopes is None else slopes
    t = np.arange(n)
    curve = []
    for b in slopes:
        hits = 0
        for _ in range(sims):
            e = np.empty(n)
            e[0] = rng.normal(0, sd)
            innov = sd * np.sqrt(1 - rho**2)
            for i in range(1, n):
                e[i] = rho * e[i - 1] + rng.normal(0, innov)
            if mk.original_test(-b * t + e, alpha=alpha).p < alpha:
                hits += 1
        curve.append({"slope": round(float(b), 3), "power": hits / sims})
    table = pd.DataFrame(curve)
    above = table[table["power"] >= power]
    return (float(above["slope"].iloc[0]) if len(above) else np.nan), table


def _ols(y: np.ndarray, X: np.ndarray):
    return sm.OLS(y, sm.add_constant(X)).fit()


def standardize(x: np.ndarray) -> np.ndarray:
    return (x - x.mean()) / x.std(ddof=1)


def nested_models(df: pd.DataFrame, response: str, first: str, second: str, reps: int = 5000, seed: int = 42) -> dict:
    """H2: response ~ first. H3: does second add explanatory power beyond first?"""
    d = df[[response, first, second]].dropna()
    y = d[response].to_numpy()
    x1 = standardize(d[first].to_numpy())
    x2 = standardize(d[second].to_numpy())
    m1 = _ols(y, x1[:, None])
    m2 = _ols(y, np.column_stack([x1, x2]))
    f_stat, f_p, _ = m2.compare_f_test(m1)
    rng = np.random.default_rng(seed)
    boot = []
    n = len(y)
    for _ in range(reps):
        i = rng.integers(0, n, n)
        if np.std(x1[i]) == 0 or np.std(x2[i]) == 0:
            continue
        r1 = _ols(y[i], x1[i][:, None]).rsquared
        r2 = _ols(y[i], np.column_stack([x1[i], x2[i]])).rsquared
        boot.append(r2 - r1)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {
        "n": n,
        "h2_slope_per_sd": float(m1.params[1]),
        "h2_ci_low": float(m1.conf_int()[1][0]),
        "h2_ci_high": float(m1.conf_int()[1][1]),
        "h2_p": float(m1.pvalues[1]),
        "h2_r2": float(m1.rsquared),
        "h2_raw_slope_days_per_unit": float(np.polyfit(d[first], y, 1)[0]),
        "m2_coef_first": float(m2.params[1]),
        "m2_coef_second": float(m2.params[2]),
        "m2_r2": float(m2.rsquared),
        "h3_delta_r2": float(m2.rsquared - m1.rsquared),
        "h3_delta_r2_ci_low": float(lo),
        "h3_delta_r2_ci_high": float(hi),
        "h3_f": float(f_stat),
        "h3_p": float(f_p),
        "vif": float(1 / (1 - np.corrcoef(x1, x2)[0, 1] ** 2)),
        "loo_rmse_m1": loo_rmse(y, x1[:, None]),
        "loo_rmse_m2": loo_rmse(y, np.column_stack([x1, x2])),
        "loo_rmse_mean_only": loo_rmse(y, np.empty((n, 0))),
    }


def loo_rmse(y: np.ndarray, X: np.ndarray) -> float:
    errs = []
    for i in range(len(y)):
        keep = np.arange(len(y)) != i
        if X.shape[1] == 0:
            pred = y[keep].mean()
        else:
            m = _ols(y[keep], X[keep])
            pred = m.predict(np.concatenate([[1.0], X[i]])[None, :])[0]
        errs.append(y[i] - pred)
    return float(np.sqrt(np.mean(np.square(errs))))


def commonality(df: pd.DataFrame, response: str, a: str, b: str) -> dict:
    """Unique and shared R^2 for two predictors (Seibold & McPhee 1979)."""
    d = df[[response, a, b]].dropna()
    y = d[response].to_numpy()
    r_a = _ols(y, d[[a]].to_numpy()).rsquared
    r_b = _ols(y, d[[b]].to_numpy()).rsquared
    r_ab = _ols(y, d[[a, b]].to_numpy()).rsquared
    return {f"unique_{a}": r_ab - r_b, f"unique_{b}": r_ab - r_a, "common": r_a + r_b - r_ab, "total": r_ab}


def spearman_table(df: pd.DataFrame, response: str, predictors: list[str]) -> pd.DataFrame:
    rows = []
    for p in predictors:
        d = df[[response, p]].dropna()
        rho, pval = stats.spearmanr(d[response], d[p])
        rows.append({"predictor": p, "spearman_rho": rho, "p": pval, "n": len(d)})
    return pd.DataFrame(rows)
