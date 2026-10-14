import numpy as np
import pytest


def double_logistic_season(mid_doy: float, base: float = 0.15, peak: float = 0.6, k1: float = 0.12,
                           senesce: float = 250.0, k2: float = 0.06) -> tuple[np.ndarray, np.ndarray]:
    doy = np.arange(91, 301)
    ndvi = base + (peak - base) * (1 / (1 + np.exp(-k1 * (doy - mid_doy))) + 1 / (1 + np.exp(k2 * (doy - senesce))) - 1)
    return doy, ndvi


@pytest.fixture
def season():
    return double_logistic_season
