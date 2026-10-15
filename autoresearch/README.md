# Autoresearch: Agent-Driven Search for a Green-Up Extractor

Results and lessons from the 33-iteration run are in [`LESSONS.md`](LESSONS.md).

A coding agent proposes changes to one file, a fixed evaluator scores them, and the loop keeps only improvements.
The loop is a methods experiment on synthetic data.
It is walled off from the confirmatory analysis in [`prereg.md`](../prereg.md).

## Design Basis: One File, Not a Notebook

The defensible pattern across published agent-loop work is a single editable program plus a fixed external evaluator,
not an agent-driven notebook:

* Karpathy's autoresearch (2026): a coding agent edits one training file against a fixed metric and time budget.
  This is the setup this loop follows.
* Google DeepMind's AlphaEvolve (2025): an LLM proposes program changes,
  and an automated evaluator, not the model, decides what survives.
* OpenAI's MLE-bench (2024): agents run in containers and are graded on held-out data they cannot see,
  with checks for rule-breaking.

## What the Agent Can and Cannot Do

* Edits only [`src/wapusk_greenup/method.py`](../src/wapusk_greenup/method.py).
* Reads the repository, including [`program.md`](program.md), [`evaluate.py`](evaluate.py),
  [`synth.py`](synth.py), and the [ledger](ledger.jsonl).
* Cannot run code, write other files, use the web, or read the held-out benchmark.

The restriction is enforced in two layers.

1. Each `claude -p` call gets `--tools Read,Edit`, `Edit` scoped to `method.py`,
   `Read` denied on the held-out directory and `setup_heldout.py`,
   `--permission-mode dontAsk`, `--safe-mode`, and `--strict-mcp-config`.
2. [`loop.py`](loop.py), not the agent, checks the tree after every call.
   It reverts any change outside `method.py`, deletes stray new files, and discards the iteration.
   It also verifies the SHA-256 of `evaluate.py`, `synth.py`, and the gap library against a lock stored outside the repository,
   before and after every call.

The enforcement path was tested with fake agents in [`tests/`](tests/).
A fake agent that edited `README.md` and planted a file had both reverted and its iteration discarded.

## Benchmark

* **Visible (scored every iteration):** 1,800 synthetic seasons with seed 1, from three curve families.
  - Double logistic
  - Snowmelt step plus linear ramp
  - Two-stage rise
* **Realism shared by all families:**
  - real cloud-gap patterns resampled from 7,088 MOD09GA strict-mask pixel-years
  - snow before melt and occasional late snowfall
  - Gaussian noise plus 5% negative outliers that mimic residual cloud
* **Held out (scored once, after freeze):**
  - fresh random seeds over the visible families
  - a fourth family of normalised real NDVI season shapes
  - stored in `~/.wapusk-autoresearch/` by [`setup_heldout.py`](setup_heldout.py)

**Score:** mean error in days, capped at 30, with NaN counted as 30.
Small penalties apply for line count (0.001 per line) and runtime above 50 ms per call.

## Running

```sh
uv run python autoresearch/setup_heldout.py         # once, by a person
autoresearch/run_loop.sh --iterations 30            # works on branch autoresearch/<date>
autoresearch/freeze.sh                              # hash method.py, score once on held-out data
uv run python autoresearch/independent_check.py     # pre-registered real-data entry criteria
uv run python autoresearch/ablation.py              # post-hoc: score every kept version
uv run python autoresearch/plot_dynamics.py         # figure for LESSONS.md
```

Each call is capped by `--budget-per-call` (default USD 2).
The ledger's `cost_usd` is Claude Code's estimate of each call's token usage at API list prices.
Under a claude.ai subscription login the calls count against plan usage limits rather than being billed per token.

## How the Result Is Used

The frozen candidate never replaces the pre-registered Savitzky–Golay extractor.
It joins the robustness grid as an extra specification only if it beats the baseline on all three of:

* the held-out benchmark
* agreement with MCD12Q2
* the plausibility of the snow-off lag

## Honest Limitations

* The `Read` deny rule and the lock are only as strong as the local user account.
  An agent with shell access could bypass both, which is why it gets none.
* A synthetic benchmark rewards whatever the generator encodes.
  The held-out real-shape family limits this but cannot remove it.
