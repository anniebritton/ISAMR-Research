# Pre-Registration: Spring Green-Up in Wapusk National Park, 2001–2024

This file fixes the confirmatory analysis before it runs.
`wapusk confirmatory` refuses to run unless this file is committed, and records its SHA-256 in `results/tables/confirmatory.json`.
Any later change to the analysis is listed under [Deviations](#deviations) and reported in the paper.

## Research Question

Has the timing of spring mid-green-up in Wapusk National Park shifted since 2001,
and how much of its year-to-year variation is explained by snowmelt timing and spring temperature?

## Prior Exposure to the Data

This analysis is not blind.

* The original notebook (`notebooks/00_original_exploration.ipynb`, 2023) fitted linear trends to a raw half-max NDVI date
  over 2000–2021 and printed slopes of +0.38 and +0.11 days/yr from identical code.
  Those numbers are unreliable and are not used.
* Before this file was written, the following were computed and inspected:
  - Per-pixel green-up dates for every specification, summarised only as counts, medians, and SDs pooled over all years.
    No annual series, trend, or relationship with any predictor was viewed.
  - The annual predictors and their correlations with each other (not with green-up).
  - The MCD12Q2 annual series, used only for the power analysis below.

## Hypotheses

* **H1 (estimation):**
  the Theil–Sen slope of park-wide mid-green-up DOY against year, 2001–2024, with a 95% CI.
  - Expectation: negative (earlier green-up).
  - Inference rests on the CI, read against the minimum detectable trend below.
  - Mann–Kendall p and the Yue et al. (2002) trend-free pre-whitened p are reported alongside.
* **H2:** later snow-off is associated with later mid-green-up.
  - Test: OLS `greenup ~ snow_off` (standardised); supported if the 95% CI on the slope lies above zero.
* **H3:** spring thawing degree days explain variance beyond snow-off.
  - Test: nested F-test of `greenup ~ snow_off + tdd` against `greenup ~ snow_off`, plus ΔR² with a 5,000-replicate bootstrap 95% CI.
  - Expectation: negative TDD coefficient.
  - Because warmth also drives snowmelt, the partition of R² into unique and shared parts (commonality analysis) is reported and interpreted as a causal chain, not as independent effects.

`alpha = 0.05`.
No correction is applied across H1–H3; each answers a distinct question and all three are reported regardless of outcome.

## Power

The minimum detectable trend was computed by simulation before any trend in this study's response was viewed.

* Reference variability: MCD12Q2 `MidGreenup_1`, area-weighted park median, detrended.
  - Interannual SD 9.2 days, lag-1 autocorrelation 0 (truncated at 0).
* With n = 24, Mann–Kendall at α = 0.05 reaches 80% power at **0.9 days/yr** (about 21 days over the record).
* Interpretation rule: a CI that spans zero is reported as "no detectable trend at this sensitivity", never as "no change".

Source: `results/tables/power_analysis.json`, `results/tables/power_curve.csv`.

## Response Variable

Mid-green-up: the day of year, per 500 m pixel, at which smoothed NDVI first reaches the dormant baseline plus 50% of the seasonal amplitude.

* **Data:** MOD09GA collection 6.1 daily surface reflectance, DOY 60–320, 2001–2024.
* **Pixels:** 300 pixels on the native MODIS grid, 75 per land-cover stratum (ESA WorldCover v200 modal class),
  limited to pixels with ≤ 10% JRC surface water; fixed in `data/aoi/sample_points.geojson`.
* **Primary mask (`strict`):** state_1km cloud state clear or not set, no cloud shadow, internal cloud flag clear,
  MOD35 snow flag clear, not adjacent to cloud, internal snow flag clear, cirrus none or small, sensor zenith < 45°,
  QC_500m MODLAND quality ideal or less-than-ideal.
* **Baseline:** per pixel, the 5th percentile of all snow-free NDVI outside DOY 150–250, pooled across years (after Beck et al. 2006).
* **Snow anchors:** snow-flagged days before the first and after the last snow-free observation enter as baseline values.
* **Primary smoother:** Savitzky–Golay on the daily interpolated series, window 31 days, order 2,
  two upper-envelope passes (Chen et al. 2004), over DOY 91–300.
* **Validity:** at least 15 snow-free observations in the window, amplitude ≥ 0.10 NDVI, crossing before the peak and after the window start.
* **Park-wide value:** area-weighted median across valid pixels.
  - Weight = stratum dry-land share ÷ number of valid pixels in that stratum that year.
  - A year with fewer than 30% valid pixels is missing.

Doiron et al. (2013) found that the date NDVI reaches 50% of its annual *maximum* predicts the peak in forage nitrogen on Bylot Island.
This study uses 50% of the *amplitude* above a snow-free baseline instead.
That form does not depend on winter snow NDVI and matches MCD12Q2 `MidGreenup`, the validation product.

## Predictors

* **Snow-off (primary):** the day after the last day in DOY 60–212 with park-mean ERA5-Land `snow_cover` ≥ 50%.
* **Thawing degree days (primary):** the sum of positive daily mean temperatures, DOY 91–151 (Apr 1–May 31), at Churchill.
  - Source: ECCC climate IDs 5060600 (2001–2005) and 5060608 (2006–2024), with 5060595 filling gaps.
  - Remaining missing days are filled from ERA5-Land through a daily linear calibration.
  - The window ends before the earliest plausible mid-green-up.

Why snow-off comes from ERA5-Land, decided on predictor completeness and agreement before any green-up relationship was viewed:

* The Churchill station has no usable spring snow-on-ground record in 9 of 24 years.
* Where available, station snow-off correlates with park-wide estimates at r ≈ 0.57.
* ERA5-Land and MODIS NDSI snow-off agree at r ≈ 0.81, despite independent sources.
* Neither primary predictor uses the MODIS snow flags that shape the NDVI series.

## Secondary and Sensitivity Analyses

These are reported in full but cannot overturn the primary result.

* **Lag:** Theil–Sen trend in the mid-green-up minus snow-off lag.
* **Robustness grid:** H1–H3 re-estimated across
  - 3 smoothers (Savitzky–Golay, double logistic, Whittaker)
  - 2 thresholds (50% and 15% of amplitude)
  - 2 masks (strict, lenient)
  - 2 aggregations (weighted median, weighted mean)
  
  That makes 24 specifications.
  The grid is summarised as the distribution of estimates and the share of specifications whose CI excludes zero.
* **Alternative products:** MCD43A4 NBAR NDVI (Savitzky–Golay, 50%); MCD12Q2 `MidGreenup_1` annual trend.
* **Validation:** pixel-year and annual r, MAE, and bias against MCD12Q2 `MidGreenup_1` (QA best or good).
  - Low agreement (annual r < 0.5) is reported as a limitation before results are discussed.
* **Alternative predictors:** station snow-off (gap-filled from ERA5-Land), ERA5-Land TDD.
* **By stratum:** Theil–Sen trend per land-cover stratum.
* **Exploratory:** Spearman correlations with maximum spring snow depth (ERA5-Land) and spring precipitation (station).

## Autoresearch Separation

The autoresearch loop (`autoresearch/`) searches for a better green-up extractor using synthetic data only.
Its candidate (`src/wapusk_greenup/method.py`) is never used in the confirmatory analysis.
It may join the robustness grid as a 25th specification only if, after freezing, it beats the Savitzky–Golay baseline on all three of:

* held-out synthetic recovery
* agreement with MCD12Q2
* the plausibility of the snow-off lag

## Deviations

The SHA-256 recorded in `results/tables/confirmatory.json` is that of this file at commit `cba988e`, before this section was filled in.
Everything above this section is unchanged since then.

1. **Post-hoc methods audit (2026-10-14), added after the confirmatory run.**
   A literature check of every method found several parameters the literature does not fix
   (see [`docs/methods_justification.md`](docs/methods_justification.md)).
   One-at-a-time sensitivity tests (`results/tables/parameter_sensitivity.csv`) and statistical robustness checks
   (`results/tables/statistical_robustness.json`) were added.
   They are reported alongside the confirmatory result and do not replace it.
2. **Citation correction, no change to the method.**
   The baseline section above attributes the percentile baseline to Beck et al. (2006).
   Beck et al. introduced the pixel-specific winter NDVI that replaces lower values; the 5th-percentile-of-snow-free-observations rule
   follows the MCD12Q2 Collection 6 dormant-value step. The report cites both accordingly.
3. **Code refactor, no change to results.**
   `smoothers.greenup_doy` gained optional arguments (smoothing window, Whittaker λ, threshold reference) for the sensitivity tests.
   Defaults reproduce the confirmatory pixel dates exactly (maximum absolute difference 3 × 10⁻¹⁴ days).
4. **Referee-prompted checks (2026-10-14), added after the confirmatory run.**
   An AI referee report (`results/review.md`) prompted the post-hoc checks in `results/tables/revision_checks.json`
   ([`src/wapusk_greenup/revision.py`](src/wapusk_greenup/revision.py)): a pixel bootstrap, bootstrap intervals for the commonality components,
   influence diagnostics, station-only and MODIS snow-off predictors, wetland versus non-wetland strata, snow-anchor binding,
   and the 2004–2016 trend.
   The report's interpretation was revised to follow the pre-registered reading of the commonality analysis (a single causal chain, not independent effects),
   which the first draft had departed from.
5. **Autoresearch melt-plausibility criterion.**
   The entry criteria for the agent's candidate were fixed above, but the operational definition of "plausibility of the snow-off lag" was not.
   It was implemented as the share of pixel-years whose green-up precedes the pixel's own MODIS melt,
   and its melt definition was corrected once after the first run; the candidate had already failed another criterion.
6. **Timeline and AI use.**
   Extraction finished at 23:08:41 UTC, this file was committed at 23:12:06 UTC, and the confirmatory run started at 23:12:10 UTC,
   all within one working session by an AI coding agent (Claude Code) under the author's direction.
