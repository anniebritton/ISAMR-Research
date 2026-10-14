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
  - The record can only detect trends of about 0.9 days/yr or more with 80% power,
    so this rules out large shifts rather than demonstrating stability.
* **Snow-off explains about half the variation (H2).**
  - Each standard deviation (15 days) of later ERA5-Land snow-off delays mid-green-up by 5.4 days (R² = 0.52).
* **Spring warmth adds to snow-off (H3).**
  - April–May thawing degree days at Churchill add ΔR² = 0.25 (95% CI 0.09–0.48).
  - Combined R² = 0.77, with a leave-one-year-out error of 4.1 days.
* **Robust and validated.**
  - All three results hold across 24 processing specifications.
  - The park-wide series tracks MCD12Q2 `MidGreenup` at r = 0.90.

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
* [`autoresearch/`](autoresearch/): a sandboxed agent loop that searches for a better green-up extractor on synthetic data
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

## Licence

Code is MIT-licensed; see [`LICENSE`](LICENSE).
Data sources keep their own licences; see [`DATA.md`](DATA.md).
