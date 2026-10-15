# Methods Justification

Every method and parameter in the confirmatory pipeline, with its peer-reviewed basis and the backup for any parameter the literature does not fix.
All references were checked against Crossref metadata; the content each is cited for was checked against the full text or abstract.
Sensitivity results come from `results/tables/parameter_sensitivity.csv` and `results/tables/statistical_robustness.json`.

How to read the status line:

* **Peer-reviewed:** a journal article supports the method as used.
* **Peer-reviewed method, chosen parameter:** the method is established, but the specific value is a design choice; the rationale and a sensitivity test are given.
* **Technical documentation:** supported by an official product user guide (not peer-reviewed), stated as such.

Across every variant below, H1 (no detectable trend) and H2 (snow-off) never changed, and H3 (spring warmth) remained significant at α = 0.05.

## Remote Sensing

### NDVI

* **Choice:** NDVI from MOD09GA bands 2 (NIR) and 1 (red).
* **Basis:** Tucker (1979), *Remote Sensing of Environment* 8:127–150, doi:10.1016/0034-4257(79)90013-0.
* **Status:** peer-reviewed.

### Quality Masking

* **Choice:** `state_1km` cloud state clear or not set (bits 0–1), no cloud shadow (bit 2), cirrus none or small (bits 8–9),
  internal cloud clear (bit 10), MOD35 snow clear (bit 12), not adjacent to cloud (bit 13), internal snow clear (bit 15);
  `QC_500m` MODLAND bits 0–1 ≤ 1.
* **Basis:** MOD09 Collection 6 user guide (Vermote et al.), which defines every bit used and states that all cloud information should come from the State QA layer.
* **Status:** technical documentation.
  Bit positions verified against the guide; bit pattern 11 means "not set, assumed clear", and is treated as clear.
* **Backup:** the lenient mask (cloud state, internal cloud, internal snow, MODLAND only) is one axis of the 24-specification grid.

### View-Angle Screen

* **Choice:** sensor zenith < 45°.
* **Basis:** view and solar geometry drive a large share of intra-annual variation in daily MODIS NDVI for sparse canopies
  (Norris & Walker 2020, *Remote Sensing of Environment* 249:112013, doi:10.1016/j.rse.2020.112013).
  The product's own HIGHVIEW flag is set at 60°.
* **Status:** peer-reviewed rationale, chosen parameter; no paper uses exactly 45°.
* **Backup:** 30°, 45°, 60°, and no screen.
  Slopes ranged from +0.03 to +0.16 days/yr with every interval spanning zero;
  the 30° screen leaves only 21 valid years.

### Dormant Baseline

* **Choice:** per pixel, the 5th percentile of snow-free NDVI outside DOY 150–250, pooled across years;
  observed NDVI below it raised to it; snow-flagged days before melt and after the last observation set to it.
* **Basis:**
  - Beck et al. (2006), *Remote Sensing of Environment* 100:321–334, doi:10.1016/j.rse.2005.10.021, introduced a pixel-specific winter NDVI that is constant across years and replaces all values below it.
    Their value is the geometric mean of two late-autumn composite maxima, not a percentile.
  - The 5th-percentile-of-snow-free-observations rule and the filling of snow-flagged observations follow MCD12Q2 Collection 6.1
    (Gray, Sulla-Menashe & Friedl, MCD12Q2 user guide), which pools the product year with its neighbours.
* **Status:** peer-reviewed concept (Beck); percentile rule from technical documentation (MCD12Q2).
* **Backup:**
  - 2nd and 10th percentiles: slopes +0.06 and −0.01 days/yr.
  - Per pixel-year baselines instead of pooled: +0.21 days/yr [−0.33, +0.62].
  - All H2/H3 results unchanged.

### Savitzky–Golay Smoother

* **Choice:** daily linear interpolation of observations and snow anchors, Savitzky–Golay filter, 31-day window, polynomial order 2, two upper-envelope passes.
* **Basis:**
  - Chen et al. (2004), *Remote Sensing of Environment* 91:332–344, doi:10.1016/j.rse.2004.03.014, for the filter with iterative fitting to the upper envelope.
    Chen tested 10-day SPOT VGT composites; the paper states the method applies to daily data but did not test it.
  - Jönsson & Eklundh (2004), *Computers & Geosciences* 30:833–845, doi:10.1016/j.cageo.2004.05.006 (TIMESAT), for a quadratic local fit with a user-set window, adapted to the upper envelope.
* **Status:** peer-reviewed method, chosen parameter.
  Chen's recommended refit window is 9 composites (about 90 days at 10-day spacing).
  A shorter 31-day window was chosen because daily data resolve the rapid, melt-driven rise that a 90-day window would flatten;
  the 91-day window is included in the backup to cover Chen's setting.
* **Backup:** windows of 15, 21, 45, 61, and 91 days.
  Mean dates shifted from DOY 181 to 176; slopes ranged from −0.09 to +0.05 days/yr, all intervals spanning zero.

### Double Logistic

* **Choice:** double logistic with the baseline fixed at the dormant NDVI, five parameters fitted per pixel-year (robustness grid only).
* **Basis:** Beck et al. (2006); logistic fitting of MODIS time series in Zhang et al. (2003), *Remote Sensing of Environment* 84:471–475, doi:10.1016/S0034-4257(02)00135-9.
* **Status:** peer-reviewed.

### Whittaker Smoother

* **Choice:** weighted Whittaker smoother with second-order differences, λ = 200 on a daily grid (robustness grid only).
* **Basis:** Eilers (2003), *Analytical Chemistry* 75:3631–3636, doi:10.1021/ac034173t; applied to NDVI by Atzberger & Eilers (2011),
  *International Journal of Digital Earth* 4:365–386, doi:10.1080/17538947.2010.505664.
  Frasso & Eilers (2015), *Statistical Modelling* 15:91–111, doi:10.1177/1471082X14549288, give data-driven λ selection (V-curve).
* **Status:** peer-reviewed method, chosen parameter.
* **Backup:** λ = 50, 200, 1000; slopes −0.03 to +0.01 days/yr.
  Per-pixel V-curve selection is listed in [future work](future_work.md).

### Threshold Definition

* **Choice:** mid-green-up at 50% of the amplitude above the dormant baseline; 15% in the robustness grid.
* **Basis:**
  - White et al. (1997), *Global Biogeochemical Cycles* 11:217–234, doi:10.1029/97GB00330, defined onset as the day the NDVI ratio (NDVI − min)/(max − min) exceeds 0.5.
  - MCD12Q2 defines Greenup and MidGreenup as 15% and 50% of the EVI2 amplitude (user guide; product assessed in Moon et al. 2019,
    *Remote Sensing of Environment* 226:74–92, doi:10.1016/j.rse.2019.03.034).
    MCD12Q2 uses EVI2, so the comparison is analogous, not identical.
* **Status:** peer-reviewed.
* **Why not Doiron et al. (2013):**
  - Doiron et al., *Applied Vegetation Science* 16:343–351, doi:10.1111/j.1654-109X.2012.01219.x, used the date 1 km AVHRR NDVI reaches 50% of its annual *maximum* on Bylot Island.
  - In Wapusk the snow-free dormant NDVI (median 0.42) exceeds half the summer peak (median 0.60) in 92% of pixels,
    so a 50%-of-maximum crossing never occurs once snow is masked; with snow included it would mark snowmelt rather than growth.
  - Doiron et al. are cited for the ecological link between mid-season NDVI timing and forage nitrogen, not for the threshold.

### Season Validity

* **Choice:** at least 15 snow-free observations in DOY 91–300; amplitude ≥ 0.10 NDVI.
* **Basis:** the amplitude floor matches MCD12Q2 (≥ 0.1; user guide).
  Minimum-observation rules exist (Beck et al. 2006 require 6 observations above winter NDVI on 16-day data) but no daily-data standard was found.
* **Status:** amplitude from technical documentation; observation count chosen.
* **Backup:**
  - Minimum observations 10 and 25: the 25-observation rule leaves 19 valid years, slope +0.15 days/yr [−0.34, +0.53].
  - Amplitude 0.05 and 0.15: slopes +0.02 and +0.07 days/yr.

### Water Screen

* **Choice:** exclude 500 m pixels with more than 10% JRC surface water (occurrence > 50%).
* **Basis:** Pekel et al. (2016), *Nature* 540:418–422, doi:10.1038/nature20584, for the data; 50% occurrence is the common water/land convention.
  No published cutoff for mixed-pixel water contamination in high-latitude phenology was found.
* **Status:** peer-reviewed data, chosen parameter.
* **Backup:** stricter screens of 2% and 5% within the existing sample; slopes +0.03 days/yr in both.
  A looser screen (20%) would require redrawing the sample and was not run.

### Sampling and Aggregation

* **Choice:** stratified random sample of 75 pixels in each of four ESA WorldCover strata; annual value = area-weighted median of pixel dates.
* **Basis:** stratified estimation with area weights follows Olofsson et al. (2014), *Remote Sensing of Environment* 148:42–57, doi:10.1016/j.rse.2014.02.015.
  ESA WorldCover v200 (Zanaga et al. 2022, doi:10.5281/zenodo.7254221) is a dataset, not a peer-reviewed paper.
  Its validation report gives user's accuracies of only 23–31% for herbaceous wetland, so the strata are design strata, not validated land-cover classes.
  Weighting keeps the estimate valid; misclassification reduces precision, not validity.
* **Status:** peer-reviewed design; weighted median is a chosen statistic.
* **Backup:** weighted mean (robustness grid) and unweighted median: slopes 0.00 and +0.04 days/yr.

### Validation Product

* **Choice:** compare with MCD12Q2 v6.1 `MidGreenup_1`, QA best or good.
* **Basis:** Moon et al. (2019); the MCD12Q2 user guide notes that Greenup and Dormancy are unreliable in some low-amplitude high-latitude regions
  and recommends MidGreenup there.
* **Status:** peer-reviewed product assessment; MCD12Q2 is treated as an independent comparison, not ground truth.

### Terra Orbit Drift

* **Basis:** Terra performed constellation exit manoeuvres in October 2022, changing overpass time and viewing geometry
  (Twedt et al., NASA technical manuscript NTRS 20240001409; not peer-reviewed). No peer-reviewed assessment of the effect on land phenology was found.
* **Backup:** excluding 2022–2024 gives +0.21 days/yr [−0.29, +0.79]; the NBAR series (Terra and Aqua combined) gives −0.04 days/yr.

## Climate Predictors

### Snow-Off

* **Choice:** day after the last day in DOY 60–212 with park-mean ERA5-Land `snow_cover` ≥ 50%.
* **Basis:**
  - Muñoz-Sabater et al. (2021), *Earth System Science Data* 13:4349–4383, doi:10.5194/essd-13-4349-2021.
  - ERA5-Land snow cover is a function of modelled depth (full cover at 10 cm), and ERA5-Land overestimates snow-cover duration and spring snow mass in the Northern Hemisphere
    (Urraca & Gobron 2023, *The Cryosphere* 17:1023–1052, doi:10.5194/tc-17-1023-2023;
    Kouki et al. 2023, *The Cryosphere* 17:5007–5026, doi:10.5194/tc-17-5007-2023).
  - No published source defines snow-off as the last day ≥ 50% in ERA5-Land; 50% matches the MODIS convention that NDSI ≥ 0.4 corresponds to roughly half cover
    (Hall et al. 2002, *Remote Sensing of Environment* 83:181–194, doi:10.1016/S0034-4257(02)00095-0).
* **Status:** peer-reviewed data with documented biases, chosen parameter.
  Used as an index of interannual variation, not as an absolute melt date.
* **Backup:**
  - ERA5-Land snow-off is on average 3.3 days later than MODIS NDSI snow-off (consistent with the known bias), with r = 0.81.
  - Thresholds of 30% and 70%: H2 slopes 5.8 and 5.0 days per SD; H3 ΔR² 0.16 and 0.30.
  - Station snow-off (gap-filled) as an alternative predictor: H2 4.4 days per SD.

### Thawing Degree Days

* **Choice:** sum of positive daily mean temperatures at Churchill, 1 April–31 May.
* **Basis:** snowmelt date and spring temperature jointly explain tundra spring phenology
  (Assmann et al. 2019, *Global Change Biology* 25:2258–2274, doi:10.1111/gcb.14639;
  Bjorkman et al. 2015, *Global Change Biology* 21:4651–4661, doi:10.1111/gcb.13051).
  No fixed-date window is standard; the window was chosen to end before the earliest plausible green-up.
* **Status:** peer-reviewed predictor, chosen window.
* **Backup:**
  - Window end 15 May: ΔR² 0.09, p = 0.04.
  - Window end 15 June: ΔR² 0.34, but this window overlaps green-up in the earliest years.
  - The warmth effect is sensitive to the window and should be reported with that range.

### Station Record

* **Choice:** ECCC daily records spliced from climate IDs 5060600, 5060608, and 5060595; remaining gaps filled from ERA5-Land by daily linear regression.
* **Basis:** the homogenized AHCCD Gen3 Churchill series (Vincent, Hartwell & Wang 2020, *Atmosphere-Ocean* 58:173–191, doi:10.1080/07055900.2020.1765728) is the reference record.
* **Status:** peer-reviewed reference used for checking.
* **Backup:**
  - The spliced April–May mean temperature matches the homogenized AHCCD series at r = 0.9995 (mean difference −0.17 °C, 2001–2020, n = 18 complete years).
  - Replacing TDD with AHCCD April–May mean temperature still supports H3 (ΔR² 0.12, p = 0.04, n = 18), more weakly, because mean temperature includes sub-zero days that TDD excludes.

## Statistics

### Trend

* **Choice:** Theil–Sen slope with rank-based 95% CI; Mann–Kendall p-values.
* **Basis:**
  - Sen (1968), *Journal of the American Statistical Association* 63:1379–1389, doi:10.1080/01621459.1968.10480934.
  - Mann–Kendall corrections for autocorrelation:
    trend-free pre-whitening (Yue et al. 2002, *Hydrological Processes* 16:1807–1829, doi:10.1002/hyp.1095),
    pre-whitening (Yue & Wang 2002, *Water Resources Research* 38(6), doi:10.1029/2001WR000861),
    variance correction (Hamed & Rao 1998, *Journal of Hydrology* 204:182–196, doi:10.1016/S0022-1694(97)00125-X).
  - Bürger (2017), *Hydrological Processes* 31:4039–4042, doi:10.1002/hyp.11280, found inflated Type I error for trend-free pre-whitening under strong autocorrelation.
* **Status:** peer-reviewed.
* **Backup:** all four Mann–Kendall variants give p between 0.60 and 0.86; lag-1 autocorrelation of the series is −0.12.

### Power

* **Choice:** minimum detectable trend by Monte Carlo simulation of Mann–Kendall power under AR(1) noise.
* **Basis:** Weatherhead et al. (1998), *Journal of Geophysical Research: Atmospheres* 103:17149–17161, doi:10.1029/98JD00995.
  Weatherhead et al. estimate noise from the series' own residuals; the pre-registered analysis used MCD12Q2 instead so the response was not inspected before the analysis was fixed.
* **Status:** peer-reviewed.
* **Backup:** own-series residual SD 7.6 days gives an MDT of 0.70–0.75 days/yr for lag-1 of 0–0.3; the pre-registered MCD12Q2-based MDT is 0.90–0.95.

### Driver Models

* **Choice:** OLS on standardized predictors; nested F-test for H3; bootstrap CI for ΔR²; leave-one-year-out cross-validation against a climatology baseline.
* **Basis:** standard practice (Efron & Tibshirani 1993, *An Introduction to the Bootstrap*, Chapman & Hall).
* **Status:** peer-reviewed standard methods.
* **Backup:** the percentile bootstrap CI for ΔR² can be biased at n = 24, so a BCa interval is also reported: 0.25 [0.08, 0.47].
  Adjusted R²: 0.49 (snow-off only) and 0.74 (snow-off + TDD).

### Commonality Analysis

* **Basis:** Seibold & McPhee (1979), *Human Communication Research* 5:355–365, doi:10.1111/j.1468-2958.1979.tb00649.x;
  recommended for collinear ecological predictors by Ray-Mukherjee et al. (2014), *Methods in Ecology and Evolution* 5:320–328, doi:10.1111/2041-210X.12166.
* **Status:** peer-reviewed.
