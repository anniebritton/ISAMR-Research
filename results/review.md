# Referee Report

**Manuscript:** "Snowmelt and Spring Warmth, Not Time, Govern Green-Up Timing in Wapusk National Park, 2001–2024" (`report/report.qmd`)

## Summary of the submission

The manuscript estimates spring mid-green-up for Wapusk National Park from 2001 to 2024. Mid-green-up is the day NDVI reaches 50% of its seasonal amplitude above a snow-free baseline. It is computed for 300 stratified MODIS pixels, using daily MOD09GA NDVI smoothed with Savitzky–Golay, and aggregated to an area-weighted median for each year. There is no detectable trend (Theil–Sen +0.03 d/yr, 95% CI −0.33 to +0.47). ERA5-Land snow-off explains about half of the year-to-year variance (R² = 0.52). April–May thawing degree days (TDD) at Churchill add ΔR² = 0.25. The analysis was pre-registered, re-run across a 24-specification grid, and compared with MCD12Q2. An appendix reports a sandboxed agent-driven search for a better green-up extractor.

The design is unusually transparent and nearly all reported numbers reproduce. The main problems lie in interpretation:
- causal framing that the pre-registration itself rules out;
- a misreported variance partition;
- precision claims that hold only for the primary specification;
- no propagation of uncertainty from the response or predictors into a regression fitted to n = 24.

## Major issues

**1. Causal and "no change" framing goes beyond the evidence and the pre-registration's own rules.**
- *Location:* title; Discussion `report/report.qmd:157`, `:163–165`; Conclusion `:180`.
- *Problem:* "Govern", "Not Time", "suggests a mechanism", "warmth matters to the pace of green-up after melt" and "warmth contributing … independently of it" are causal claims drawn from a correlational regression with n = 24. "Not Time" in the title reads as "no change", which the pre-registered interpretation rule forbids (`prereg.md:49`). The pre-registration also says the commonality partition is "interpreted as a causal chain, not as independent effects" (`prereg.md:37`). The Conclusion does the opposite.
  - The mechanism claim also fails on its own terms. The TDD window ends on 31 May, but ERA5 snow-off falls after DOY 151 in 4 of 24 years (2002: 158, 2004: 162, 2009: 163, 2012: 165; `data/processed/drivers.csv`). In those years April–May TDD is pre-melt warmth, so it cannot measure "the pace of green-up after melt".
- *Fix:* Retitle (e.g., "…No Detectable Trend, Strong Association with Snowmelt and Spring Warmth…"). Replace "govern" and "independently" with associational language. Follow the pre-registered reading of the commonality analysis, or disclose the departure from it as a deviation.

**2. The commonality partition is misreported.**
- *Location:* `:139`, `:164`.
- *Problem:* The values 0.19, 0.25 and 0.33 (`confirmatory.json` → `commonality`) are fractions of *total* variance (R² units). The text calls them fractions of "the explained variance". As shares of the explained variance (0.765) they are 24%, 33% and 43%. The Discussion's "share a third of the explained variance" is therefore wrong: the shared component is 43% of the explained variance, or a third of the total. No uncertainty is given for any component.
- *Fix:* Correct the wording and add bootstrap CIs for each component.

**3. The precision of the trend estimate, and the comparison with Mallory et al., hold only for the primary specification.**
- *Location:* Abstract `:18`, `:20`; Discussion `:158–160`; Conclusion `:179`.
- *Problem:* "Advances faster than about a third of a day per year are inconsistent" depends on the primary specification. In `multiverse.csv`, 14 of 24 CIs extend below −0.56 d/yr: every 15%-threshold specification and both lenient double-logistic 50% specifications. Their lower bounds reach −0.72. So Mallory's rate (7.25 d over 2004–2016 ≈ 0.56 d/yr) lies *inside* most of the grid. "All three findings held across 24 specifications" is true for the sign and significance of H1, but not for the bound the paper emphasises.
  - The metrics also differ by construction, not just possibly. Mallory et al. report the *start* of green-up, while this paper uses the midpoint. Yet the manuscript says only that the metric "may not match".
  - "An order of magnitude larger than any trend the CI allows" (`:158`) compares days with days per year. Over 23 years the CI allows a total shift of about −7.5 to +10.9 days, the same order as the ±15-day swings between years.
- *Fix:* Report the range of CI bounds across the grid next to the primary bound. Estimate the trend over 2004–2016 for a like-for-like comparison, and say Mallory used start of green-up. Restate the swing comparison in the same units.

**4. Uncertainty in the response and predictors is not propagated.**
- *Location:* Methods `:87`, `:105`; Results `:136–140`.
- *Problem:* Each annual park-wide value is a weighted median of 227–300 pixel retrievals. Pixel-level agreement with MCD12Q2 is only r = 0.55 (MAE 10.1 d). Yet the annual values are treated as known exactly. Predictor error is also ignored. ERA5 and MODIS snow-off differ by 36 days in 2012 (165 vs 129) and by 14 days in 2010 (107 vs 117). Errors in the predictors bias their slopes toward zero, and their effect on ΔR² and the commonality shares is unknown.
  - Several quantities have no reported uncertainty:
    - the combined-model coefficients (3.6 and −4.1 d/SD);
    - the leave-one-year-out errors;
    - the annual validation r;
    - the commonality components.
  - The BCa interval for ΔR² was computed (0.084–0.474; `statistical_robustness.json`) but never reported, although Methods says both kinds were used (`:105`).
  - A percentile bootstrap of ΔR² is bounded below by zero, so an interval that excludes zero is weak evidence. The F-test is the better inferential basis.
- *Fix:* Bootstrap pixels within strata within years, and carry that variability through H1–H3. Report CIs for every quantity listed above. Run H2/H3 with MODIS snow-off as a predictor-error sensitivity check.

**5. The driver models are fitted to 24 points with a few high-leverage years, and H3 is fragile.**
- *Location:* `:137–139`, `:150`.
- *Problem:* TDD is strongly skewed, ranging from 0.0 (2009) and 2.3 (2004) up to 182.8 (2023). The two latest green-up years (2004 and 2009, about DOY 195) are also the two years with near-zero TDD and the latest snow-off. 2023 combines record TDD with early green-up, in a Terra drift year. ΔR² swings from 0.09 to 0.34 with the TDD window. The 15 June window (DOY 166) overlaps the green-up dates of early years (2006: DOY 164.9), so its 0.34 is partly circular. The manuscript nonetheless presents this as evidence about sensitivity.
- *Fix:* Report Cook's distance and leverage. Show H2/H3 with 2004, 2009 and 2023 each left out. Consider a log or rank transform of TDD. Remove the DOY 166 variant, or flag it as overlapping the response.

**6. Station snow-off is not an independent check.**
- *Location:* `:148`.
- *Problem:* The station snow-off series is filled from calibrated ERA5 in 9 of 24 years (`drivers.csv`, `snow_off_station_source`). Those include the two most influential years, 2004 and 2009. "Changed none of the conclusions" is therefore partly ERA5 compared with itself. Using station data only, H2 also weakens noticeably (R² 0.35 vs 0.52).
- *Fix:* Re-run on the 15 years with genuine station data and report the result.

**7. What the response measures in a park dominated by herbaceous wetland.**
- *Location:* Methods `:73–83`; validation `:121`.
- *Problem:* Herbaceous wetland makes up 57% of the dry-land weight. In fen and peatland, NDVI after melt is held down by standing meltwater and saturated surfaces. So the 50% crossing may partly track surface drying rather than leaf development. That would inflate the snow-off association for reasons unrelated to vegetation. Snow anchoring at the baseline (`:74`) also mechanically constrains the crossing to fall after MODIS-detected melt. MODIS snow-off correlates with ERA5 snow-off at r = 0.81, so the claim that the design "avoids building a mechanical correlation" (`:94`) is only partly true.
  - The explanation for the 15% threshold (`:147`), "onset… more tightly coupled to melt", is not supported for the strict mask. There R² barely changes (0.515 → 0.523), and the larger slope per SD mostly reflects more variance in the response.
- *Fix:*
  - Report the distribution of days between the first snow-free observation and the crossing, and how often the anchors bind.
  - Repeat H2 within the non-wetland strata.
  - Discuss surface water and NDVI with an appropriate citation.
  - Consider NDWI or LSWI as a covariate.

**8. MCD12Q2 is not independent validation, and the annual r is not computed as described.**
- *Location:* Abstract `:20`; `:113`; `:119–121`.
- *Problem:* MCD12Q2 is derived from the same MODIS reflectance (NBAR EVI2). Agreement with it shows consistency between products, not accuracy. The reported annual r = 0.904 is computed in `src/wapusk_greenup/phenology.py:144`. It uses *unweighted* medians of matched pixel-years where MCD12Q2 QA is best or good (5,126 of 6,845). It is not the area-weighted park-wide series the text describes. My recomputation from `greenup_annual.csv` and `mcd12q2_annual.csv` gives about 0.90, so the conclusion stands, but the method description is wrong. The claim that the +8.6-day bias is a "constant offset" (`:121`) is asserted, not shown.
- *Fix:*
  - Describe the computation correctly, or switch to the park-wide series.
  - Plot the annual bias against year, especially 2022–2024.
  - Call MCD12Q2 a consistency check.
  - Add any independent ground reference available, such as PhenoCam or Churchill-area field phenology.

**9. Post-hoc analyses are only partly disclosed as deviations from the pre-registration.**
- *Location:* Methods `:101–106`, `:112`.
- *Problem:* Methods presents the following as planned analyses:
  - the Hamed–Rao and Yue–Wang Mann–Kendall variants;
  - the BCa interval;
  - the minimum detectable trend from the series' own variability;
  - the AHCCD check.

  All of them come from the post-hoc `statistical_robustness.json`, which is listed under Deviation 1 in `prereg.md`. The manuscript labels only the one-at-a-time parameter tests as post-hoc. The interpretation departures (issue 1) are not disclosed at all.
  - The extraction timestamps also need explaining. `data/processed/extraction_manifest.json` shows every input extracted between 23:06 and 23:08 UTC on 2026-10-14, six minutes before the confirmatory run. Yet the pre-registration says per-pixel dates were computed before it was written.
- *Fix:* Mark every post-hoc analysis in Methods. Add a deviations paragraph to the manuscript. Give the commit timestamps of `cba988e` and of the first extraction.

**10. The target population is narrower than "Wapusk National Park".**
- *Location:* `:58–59`; the title.
- *Problem:* 28% of candidate pixels (1,701 of 6,000) were excluded as too wet, along with pixels outside the four strata. Inference therefore applies to the drier ~70% of the park, which plausibly sits in different positions along the coast-to-inland gradient.
- *Fix:* State the population explicitly, and show a map of the excluded areas.

## Minor issues

1. `:93`: station snow-off agreement is given as r = 0.58, while `prereg.md:87` says ≈ 0.57. The tables give 0.580 against ERA5 and 0.561 against MODIS. Say which comparison is meant.
2. `:101`: "…and with trend-free pre-whitening, since the last is known to inflate Type I error" reads as if the inflation were the reason for using TFPW. Rephrase: TFPW was pre-registered, and the other variants were added *because* TFPW can inflate Type I error.
3. `:128`: "SD 7.5 against 9.2" compares the raw sample SD with a detrended SD (ddof = 2). The like-for-like value is 7.64 (`statistical_robustness.json`).
4. TDD windows are defined by day of year, so in leap years "1 April–31 May" is actually 31 March–30 May, and "15 May" (DOY 135) is 14 May.
5. Several post-hoc variants lost years and the text doesn't say so: 30° zenith (21 years), ≥25 observations (19 years). The precipitation correlation uses n = 22, and 2009, an extreme year, is missing.
6. The pre-registered rule that a year is missing below 30% valid pixels (`prereg.md:70`) is never mentioned. No year triggered it, but it should be stated.
7. Several numbers appear in no results table, so they cannot be verified: 11% and 17% usable pixel-days; dormant NDVI median 0.42 and peak median 0.60, with the 92% figure; TDD SD of 48 degree-days; the 7,088 real pixel-years in the appendix. Add them to a table.
8. The claim that ESA WorldCover's user's accuracy for herbaceous wetland is 23–31% (`:59`) needs a citation.
9. Olofsson et al. give estimators for means and proportions. The weighted *median* is reasonable, but say it is a plug-in estimator.
10. Discussion `:160`: Assmann et al. (2019), which is already cited, found that regional sea ice did *not* explain tundra phenology. The Hudson Bay sea-ice speculation should acknowledge this.
11. Schmidt et al. (2023) is a single site (Zackenberg, NE Greenland), not "coastal Arctic sites" (`:161`).
12. The lag trend (+0.42 d/yr, CI −0.30 to +1.02) has a wider interval than the minimum detectable trend. Say that it is uninformative rather than "no trend".
13. MOD09GA coverage is short in 2001 (244 days), 2002 (252) and 2022 (249) (`extraction_manifest.json`). Note this alongside the Terra caveat.
14. The appendix is a methods experiment. Its relevance to a remote-sensing ecology journal is marginal, so move it to the Supplement. The finding that four of eight kept changes only reduced the line-count penalty is worth keeping. The real-NDVI held-out "template" family has an error of 8.4 days, against 2–4 days for the synthetic families. This suggests the synthetic benchmark represents real seasons poorly, and the paper should say so.
15. The appendix's lag-plausibility criterion was operationalised ("zero pixel-years before melt") and corrected after its first run. The correction is disclosed, but the operational definition was never fixed in the pre-registration.

## Number checks

I checked about 70 numbers against `confirmatory.json`, `sensitivity.json`, `multiverse.csv`, `power_analysis.json`, `power_curve.csv`, `statistical_robustness.json`, `parameter_sensitivity.csv`, `exploratory_correlations.csv`, `greenup_by_stratum.csv`, `autoresearch_final.json`, `autoresearch_independent.json`, `method_lock.txt`, `autoresearch/ledger.jsonl` (kept/reverted counts, USD 17.90 total, no stray edits), `data/processed/*.csv` and the sample-point metadata (53,164 cells, 28% too wet, 57/33/7/2% shares). Rounded values match except for the following:

| Location | Manuscript sentence | Table / source value | Problem |
|---|---|---|---|
| `:139` | "attributed 0.19 of the explained variance uniquely to snow-off, 0.25 uniquely to TDD, and 0.33 to their shared component" | `commonality`: 0.186 / 0.250 / 0.329, total 0.765 | These are shares of total variance. As shares of explained variance: 24% / 33% / 43% |
| `:164` | "snow-off and spring warmth share a third of the explained variance" | 0.329 / 0.765 = 0.43 | 43% of explained variance (a third of total variance) |
| `:159` | "about 0.56 days/yr … a rate that lies outside the confidence interval estimated here" | Primary CI low −0.327, but `multiverse.csv` lower bounds reach −0.721; 14 of 24 ≤ −0.56 | True only for the primary specification |
| `:158` | "these swings are an order of magnitude larger than any trend the confidence interval allows" | CI × 23 yr = −7.5 to +10.9 d, vs ±15 d swings | Same order of magnitude; mixes units |
| `:165` | "predictable from spring conditions available by the end of May" | `drivers.csv` `snow_off`: 158, 162, 163, 165 in 2002, 2004, 2009, 2012 (> DOY 151) | The predictor is not available by 31 May in 4 of 24 years |
| `:20`, `:119` | "the park-wide series tracked … MCD12Q2 closely (r = 0.90)" | 0.904 from unweighted medians of matched pixel-years (`phenology.py:144`); park-wide vs park-wide recomputed ≈ 0.90 | Value holds; the computation described is wrong |
| `:93` vs `prereg.md:87` | "station snow-off correlated with park-wide estimates at only r = 0.58" | 0.580 (vs ERA5), 0.561 (vs MODIS); pre-registration says ≈ 0.57 | Minor inconsistency |
| `:128` | "(SD 7.5 against 9.2 days)" | Raw SD 7.48; detrended SD 7.64 vs MCD12Q2 detrended 9.19 | Bases differ; the conclusion is unaffected |

## Reference checks

I verified the references marked "web" during this review. The ones marked "known" have bibliographic details matching my own knowledge but weren't searched individually.

| Key | Exists | Supports the citation? |
|---|---|---|
| doiron2013 | Yes (web) | Mostly. The 1 km AVHRR detail and NDVI50 r² = 0.87 are confirmed. But secondary sources describe NDVI50 both as "50% of annual maximum" and as "halfway between seasonal minimum and maximum". If the latter is right, the claimed departure (`:81–83`) is overstated. Check the original. |
| mallory2020 | Yes (web) | Yes: 7.25 d from 2004 to 2016, with migration and calving advancing alongside. The metric is *start* of green-up (see major issue 3). |
| gray2019guide | Yes (web) | Yes. The dormant value is the 5th percentile of snow-free values, and the guide recommends MidGreenup in low-amplitude high-latitude regions. |
| assmann2019 | Yes (web) | Yes, for both claims (phenology advanced only where snowmelt advanced). The paper also argues against the sea-ice speculation. |
| schmidt2023 | Yes (web) | Partly. It is a single site (Zackenberg), not "sites". |
| urraca2023 | Yes (web) | Yes. ERA5-Land consistently overestimates snow-cover duration. |
| kouki2023 | Yes (web) | **No.** It reports ERA5-Land snow-cover extent as accurate; the overestimate is in SWE. Remove it, or cite it for SWE only. |
| burger2017 | Yes (web) | Yes. TFPW has high Type I error under autocorrelation. |
| norris2020 | Yes (web) | Yes. View and solar geometry drive MODIS NDVI artefacts (studied in western US pinyon-juniper). |
| chen2004 | Yes (web) | Likely. m = 4 on 10-day composites gives a window of about 90 days; full text not read. |
| karpathy2026 | Yes (web) | Yes. Single editable file, fixed evaluator, keep/discard loop. |
| novikov2025 | Yes (arXiv 2506.13131) | Yes. Programs scored by automated evaluators. |
| chan2024 | Yes (arXiv 2410.07095) | Partly. MLE-bench is a benchmark of graded Kaggle tasks, not an iterative single-program loop. |
| beck2006 | Yes (known) | Yes. Pixel-specific winter NDVI and double logistic. |
| zhang2003 | Yes (known) | Yes. Logistic-model phenology. |
| eilers2003 / atzberger2011 | Yes (known) | Yes. Whittaker smoother. |
| jonsson2004 | Yes (known) | Yes. TIMESAT upper-envelope fitting. |
| white1997 | Yes (known) | Yes. 0.5 NDVI-ratio threshold. |
| moon2019 | Yes (known) | Yes, but secondary for the MCD12Q2 50%-EVI2 rule. Cite the guide or Friedl as primary. |
| tucker1979 | Yes (known) | Acceptable for NDVI (Rouse et al. 1974 is the origin). |
| hall2002 | Yes (known) | Yes. NDSI 0.4 threshold. |
| sen1968, hamed1998, yuewang2002, yue2002, weatherhead1998 | Yes (known) | Yes. Each matches its stated use. |
| seibold1979, raymukherjee2014 | Yes (known) | Yes. Commonality analysis. |
| efron1993 | Yes (known) | Yes. Percentile and BCa bootstrap. |
| olofsson2014 | Yes (known) | Yes, for stratified estimation (see minor issue 9). |
| bjorkman2015 | Yes (known) | Yes. Warming and snow jointly affect tundra phenology. |
| vincent2020 | Yes (known) | Yes. Third-generation AHCCD. |
| gorelick2017, pekel2016, munozsabater2021, zanaga2022 | Yes (known) | Yes, as data and platform citations. |
| vermote2021, schaaf2021, hall2021, friedl2022 (product DOIs) | Yes (known) | Yes. The DOIs match the V061 products. |

## Recommendation: Major revision

The core work is sound. The sample is fixed and committed, the analysis was pre-registered with an explicit power analysis and interpretation rule, the robustness grid is broad, and almost every number in the text reproduces from the result tables. The null trend and the strong snow-off association are probably robust. However, the manuscript:
- draws causal and mechanistic conclusions that its own pre-registration rules out;
- misstates the variance partition that those conclusions rest on;
- reports a precision bound, and a contradiction of Mallory et al., that hold for the primary specification but not for most of the grid;
- treats noisy annual aggregates and reanalysis predictors as exact in a regression with n = 24 and a few high-leverage years.

It also doesn't examine whether NDVI mid-green-up in a wetland-dominated landscape partly tracks meltwater drying rather than leaf-out. All of these can be fixed with existing data and reframing, without new collection. That makes this a major revision rather than a rejection.

---

I didn't edit or create any files; the report is above. There's an untracked `results/review.md` from before this session that I didn't open or change. If you want this report saved there, that would overwrite whatever it contains.

Sources:
- [Mallory et al. 2020, Oecologia](https://link.springer.com/article/10.1007/s00442-020-04604-0); [CBC summary](https://www.cbc.ca/news/canada/north/qamanirjuaq-caribou-migration-1.5555378)
- [MCD12Q2 C6 User Guide](https://lpdaac.usgs.gov/documents/1310/mcd12q2_v6_user_guide.pdf); [C6.1 User Guide](https://lpdaac.usgs.gov/documents/1417/MCD12Q2_User_Guide_V61.pdf)
- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- [Assmann et al. 2019](https://onlinelibrary.wiley.com/doi/10.1111/gcb.14639)
- [Schmidt et al. 2023](https://www.cell.com/current-biology/fulltext/S0960-9822(23)00823-0)
- [Kouki et al. 2023](https://tc.copernicus.org/articles/17/5007/2023/); [Urraca & Gobron 2023](https://tc.copernicus.org/articles/17/1023/2023/)
- [Bürger 2017](https://www.researchgate.net/publication/318407427_On_trend_detection); [zyp package notes](https://cran.r-project.org/web/packages/zyp/zyp.pdf)
- [Norris & Walker 2020](https://www.sciencedirect.com/science/article/abs/pii/S0034425720303837)
- [Chen et al. 2004 PDF](https://silvis.forest.wisc.edu/wp-content/uploads/pubs/Non-SILVIS/Chen_etal_2004_RSE.pdf)
- Doiron et al. 2013 secondary descriptions: [Gauthier et al. 2013](https://www.uqar.ca/app/uploads/2024/05/2013_gauthier_et_al_prsl-b.pdf?v=1716913697), [PLoS ONE 2014](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0108331)
