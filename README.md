# Wapusk Green-Up

Spring green-up timing and its climate drivers in Wapusk National Park, Manitoba, 2001–2024.
Written for the [International Student-led Arctic Monitoring and Research (ISAMR) Project](https://www.isamr.net/home).

## Research Question

Has the timing of spring mid-green-up in Wapusk National Park shifted since 2001,
and how much of its year-to-year variation is explained by snowmelt timing and spring temperature?

The analysis is pre-registered in [`prereg.md`](prereg.md).
The full write-up is [`report/report.qmd`](report/report.qmd).

## Findings

* **No detectable trend (H1).**
  - Theil–Sen slope +0.03 days/yr, 95% CI −0.33 to +0.47, n = 24 years.
  - Across 24 processing specifications the lower bound ranges from −0.33 to −0.72 days/yr,
    and the minimum detectable trend is about 0.7–0.9 days/yr, so this rules out large shifts rather than demonstrating stability.
  - Over 2004–2016 the series is compatible with the 0.56 days/yr advance reported for the nearby Qamanirjuaq calving grounds.
* **Snow-off is associated with about half the variation (H2).**
  - Each standard deviation (15 days) of later ERA5-Land snow-off goes with 5.4 days later mid-green-up (R² = 0.52).
* **Spring warmth adds to snow-off (H3), but its size depends on the temperature window.**
  - April–May thawing degree days at Churchill add ΔR² = 0.25 (BCa 95% CI 0.08–0.47); combined R² = 0.77, cross-validated error 4.1 days.
  - Ending the window on 15 May instead of 31 May cuts the increment to 0.09.
* **Checked against influence, retrieval noise, and predictor source.**
  - All results hold across 24 specifications, a pixel bootstrap, and removal of the most influential years.
  - The series agrees with MCD12Q2 at r = 0.90, a consistency check between two MODIS retrievals rather than independent validation.
* **An agent loop improved the method on synthetic data but not for the science.**
  - A sandboxed coding agent cut held-out synthetic error by 6% over 33 iterations, but traded away interannual fidelity on real pixels.
  - See [`autoresearch/LESSONS.md`](autoresearch/LESSONS.md) for what that teaches about agents in research pipelines.

![Park-wide mid-green-up, 2001–2024](results/figures/greenup_series.png)

## Repository Layout

* [`config.yaml`](config.yaml): datasets, masks, windows, and the pre-registered primary specification
* [`src/wapusk_greenup/`](src/wapusk_greenup/): the pipeline
  - `extract.py`, `station.py`: Earth Engine and ECCC downloads into `data/raw/`
  - `smoothers.py`: pre-registered green-up extractors
  - `phenology.py`, `drivers.py`: per-pixel green-up and annual predictors
  - `stats.py`, `analysis.py`: trend, power, driver models, robustness grid
  - `plots.py`, `cli.py`: figures and the `wapusk` command
* [`data/`](data/): park boundary, the fixed pixel sample, and derived annual tables (raw extracts are gitignored)
* [`results/`](results/): figures and result tables, including `confirmatory.json`
* [`autoresearch/`](autoresearch/): a sandboxed agent loop that searches for a better green-up extractor on synthetic data,
  with its [lessons](autoresearch/LESSONS.md)
* [`docs/methods_justification.md`](docs/methods_justification.md): the peer-reviewed basis and sensitivity test for every method
* [`results/review.md`](results/review.md): the AI referee report on the first draft
* [`notebooks/`](notebooks/): the original 2023 exploration (archived) and an exploratory appendix
* [`DATA.md`](DATA.md): every dataset with its version, licence, and citation

## Setup

Requires Python 3.11+, [uv](https://docs.astral.sh/uv/), and an Earth Engine account registered to a Google Cloud project.

```sh
uv sync
uv run earthengine authenticate
```

Set `gee_project` in [`config.yaml`](config.yaml) to your Cloud project ID.

## Running

```sh
uv run wapusk extract       # Earth Engine + station data into data/raw/ (cached; about 10 minutes)
uv run wapusk phenology     # green-up for every pixel-year and specification
uv run wapusk drivers       # annual predictors
uv run wapusk confirmatory  # pre-registered analysis; runs once and needs a committed prereg.md
uv run wapusk sensitivity   # MCD12Q2, NBAR, stratum, and predictor checks
uv run wapusk multiverse    # 24-specification robustness grid
uv run wapusk parameter-sensitivity  # post-hoc one-at-a-time parameter tests
uv run wapusk stat-robustness        # post-hoc statistical checks
uv run wapusk revision-checks        # post-hoc checks prompted by the referee report
uv run wapusk figures
```

`uv run wapusk all` runs every step after sampling.
`wapusk sample` redraws the pixel sample, which is already committed and should not change.

Render the report with [Quarto](https://quarto.org):

```sh
quarto render report/report.qmd
```

## Tests

```sh
uv run pytest            # unit tests on synthetic data
uv run pytest -m gee     # integration test against the real Earth Engine backend
```

## Use of AI

The pipeline, pre-registration, and first draft of the report were produced by an AI coding agent (Claude Code) under the author's direction,
and an AI referee reviewed the draft.
The author is responsible for the research questions, design decisions, and conclusions.

## Licence

Code is MIT-licensed; see [`LICENSE`](LICENSE).
Data sources keep their own licences; see [`DATA.md`](DATA.md).
