# Wapusk Green-Up

Spring green-up timing and its association with snowmelt and spring warmth in Wapusk National Park, Manitoba, 2001–2024,
with a supplementary study of a sandboxed coding agent improving the method.
Written for the [International Student-led Arctic Monitoring and Research (ISAMR) Project](https://www.isamr.net/home).

* **Interactive brief:** [anniebritton.github.io/ISAMR-Research](https://anniebritton.github.io/ISAMR-Research/)
* **Report:** [`report/report.qmd`](report/report.qmd)
* **Pre-registration:** [`prereg.md`](prereg.md)

## Research Question

Has the timing of spring mid-green-up in Wapusk National Park shifted since 2001,
and how strongly is its year-to-year variation associated with snowmelt timing and spring temperature?

## Findings

* **No detectable trend.**
  Theil–Sen slope +0.03 days/yr (95% CI −0.33 to +0.47); the record can only reliably detect trends of about 0.7–0.9 days/yr.
  Over 2004–2016 the series is compatible with the 0.56 days/yr advance reported nearby by Mallory et al. (2020).
* **Snowmelt and spring warmth.**
  Each standard deviation (15 days) of later ERA5-Land snow-off goes with 5.4 days later green-up (R² = 0.52).
  April–May thawing degree days add ΔR² = 0.25, for a combined R² of 0.77 and a cross-validated error of 4.1 days,
  but the warmth contribution depends on how the temperature window is drawn.
* **Agent loop.**
  A sandboxed coding agent cut held-out synthetic error by 6%, but weakened year-to-year fidelity on real pixels.
  [`autoresearch/LESSONS.md`](autoresearch/LESSONS.md) sets out what that teaches about agents in research pipelines.

![Annual mid-green-up, 2001–2024](results/figures/greenup_series.png)

## Repository Layout

* [`config.yaml`](config.yaml): datasets, masks, windows, and the pre-registered primary specification
* [`src/wapusk_greenup/`](src/wapusk_greenup/): the pipeline
  - `extract.py`, `station.py`: Earth Engine and ECCC downloads into `data/raw/`
  - `smoothers.py`: pre-registered green-up extractors
  - `phenology.py`, `drivers.py`: per-pixel green-up and annual predictors
  - `stats.py`, `analysis.py`: trend, power, driver models, and robustness grid
  - `revision.py`: post-hoc checks requested by the referee report
  - `plots.py`, `site.py`, `cli.py`: figures, data for the interactive brief, and the `wapusk` command
  - `method.py`: the autoresearch agent's candidate extractor, never used in the confirmatory analysis
* [`autoresearch/`](autoresearch/): the sandboxed agent loop, its ledger, evaluation, ablation, and [lessons](autoresearch/LESSONS.md)
* [`data/`](data/): park boundary, the fixed pixel sample, and derived tables; raw extracts are gitignored
* [`results/`](results/): figures, result tables, and the [AI referee report](results/review.md)
* [`report/`](report/): the report and its bibliography
* [`site/`](site/): the interactive brief, deployed to GitHub Pages
* [`docs/`](docs/): [methods justification](docs/methods_justification.md) and [future work](docs/future_work.md)
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
uv run wapusk extract                # Earth Engine + station data into data/raw/ (cached)
uv run wapusk phenology              # green-up for every pixel-year and specification
uv run wapusk drivers                # annual predictors
uv run wapusk confirmatory           # pre-registered analysis; runs once and needs a committed prereg.md
uv run wapusk sensitivity            # MCD12Q2, NBAR, stratum, and predictor checks
uv run wapusk multiverse             # 24-specification robustness grid
uv run wapusk parameter-sensitivity  # post-hoc one-at-a-time parameter tests
uv run wapusk stat-robustness        # post-hoc statistical checks
uv run wapusk revision-checks        # post-hoc checks prompted by the referee report
uv run wapusk figures                # report figures
uv run wapusk site                   # data for the interactive brief
```

`uv run wapusk all` runs every step after sampling.
`wapusk sample` redraws the pixel sample, which is committed and should not change.
The view-angle sensitivity test needs one extra pull: `uv run wapusk extract --source mod09ga_zenith`.

To preview the brief locally, run `uv run wapusk site`, then `python -m http.server -d site` and open `localhost:8000`.
The report renders with [Quarto](https://quarto.org) (`quarto render report/report.qmd`); the Pages workflow renders it automatically.

The autoresearch loop has its own instructions in [`autoresearch/README.md`](autoresearch/README.md).

## Tests

```sh
uv run pytest            # unit tests on synthetic data
uv run pytest -m gee     # integration tests against the real Earth Engine backend
```

## Status

The confirmatory analysis, robustness checks, and referee revisions are complete.
Open items are tracked in [`docs/future_work.md`](docs/future_work.md),
including a clean-clone reproducibility run, a Zenodo archive of the raw extracts, ground phenology for validation, and a second agent loop.

## Use of AI

The pipeline, pre-registration, and first draft of the report were produced by an AI coding agent (Claude Code) under the author's direction,
and an AI referee reviewed the draft.
The author is responsible for the research questions, design decisions, and conclusions.

## Citation

See [`CITATION.cff`](CITATION.cff).

## Licence

Code is MIT-licensed; see [`LICENSE`](LICENSE).
Data sources keep their own licences; see [`DATA.md`](DATA.md).
