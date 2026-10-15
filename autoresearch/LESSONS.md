# Lessons From the Autoresearch Run

What 33 iterations of a sandboxed coding agent, improving one retrieval algorithm, taught about running agents in a research pipeline.
Evidence comes from [`ledger.jsonl`](ledger.jsonl), [`results/tables/autoresearch_final.json`](../results/tables/autoresearch_final.json),
[`autoresearch_independent.json`](../results/tables/autoresearch_independent.json), and the post-hoc ablation in
[`autoresearch_ablation.csv`](../results/tables/autoresearch_ablation.csv) ([`ablation.py`](ablation.py)).

![Search dynamics and what carried over to real data](../results/figures/autoresearch_dynamics.png)

## What Happened

* 33 iterations: 3 in a smoke test, then 30 in the main run.
  - Estimated usage was USD 17.90 at API list prices, about USD 0.54 per iteration.
* Outcomes:
  - 8 changes kept
  - 20 reverted because the score did not improve
  - 5 iterations where the agent declined to edit
  - 0 attempts to touch any file other than `method.py`
* The visible score fell from 3.18 to 2.98 days (−6%); the held-out error fell from 4.66 to 4.39 days (−6%).
* On real pixels, the frozen candidate:
  - improved pixel-level agreement with MCD12Q2 (MAE 9.7 vs 10.1 days)
  - lowered park-wide annual correlation (0.881 vs 0.900)
  - left H1–H3 essentially unchanged
* It failed the pre-registered entry rule for the robustness grid.

## Lessons

### 1. Put Enforcement Outside the Agent, and Test the Harness Before the Agent

The agent never tried to break the sandbox, so the zero-violation record says little about the sandbox itself.
The evidence that enforcement works comes from fake agents ([`tests/`](tests/)) that deliberately edited forbidden files and planted new ones.
The only enforcement failure in the project was a bug in the driver, not the agent.
A stripped `git status` line turned `src/...` into `rc/...`; the first smoke test caught it.

* **Do:** test the harness with scripted adversarial agents before spending model calls.
* **Do:** keep every check (allowed files, evaluator hash, held-out location) in code the agent cannot edit or run.

### 2. A Single Scalar Gets Gamed, Even by a Well-Behaved Agent

Four of the eight kept changes (iterations 19, 26, 27, 28) only deleted or merged lines.
Every estimate stayed identical; the gain came from the 0.001-per-line complexity penalty.
The agent said so openly ("a cleanup, not a method change… the score should drop by 0.001").
A fifth change lowered the amplitude floor, mainly converting seasons that scored the 30-day failure penalty into estimates.

* **Do:** reject changes whose outputs are identical to the incumbent's (a behavioural-equivalence check) rather than rewarding line count.
* **Do:** make the cheapest way to improve the score the behaviour you want; a fixed NaN penalty invites lowering quality floors.
* **Do:** read the ledger. Candid rationales made the gaming visible within minutes.

### 3. The Proxy Diverged From the Science, and the Best Version Was Not the Last

The loop optimised per-season accuracy on synthetic data.
The science depends on interannual fidelity, which no part of the evaluator measured.

| Version | Held-out error (days) | Park-wide annual r | Pixel MAE (days) |
|---|---|---|---|
| Start (pre-registered SG) | 4.66 | 0.900 | 10.11 |
| Iteration 8: ignore post-melt snow flags | 4.48 | 0.903 | 10.14 |
| Iteration 16: robust amplitude rescaling | 4.40 | 0.881 | 9.63 |
| Frozen (iteration 28) | 4.39 | 0.881 | 9.68 |

Iteration 8 improved held-out error without losing annual fidelity.
Iteration 16 traded annual fidelity for a lower pixel bias, and a keep-if-lower rule cannot see that trade.
The ablation of the frozen candidate shows that the trade is not one isolated change: removing the amplitude rescaling alone lowers annual r further (0.874), so the components interact.

* **Do:** score the downstream statistic directly, e.g. synthetic multi-year panels with a known trend and a known driver effect,
  scored on recovery of the slope and R².
* **Do:** keep a Pareto archive across objectives and select at the end, rather than accepting on one number.

### 4. Benchmark Realism Was the Bottleneck

On the held-out family built from real NDVI season shapes, every method erred by 8.4–10.9 days, against 2–4 days on the synthetic families.
The agent's best improvement on that family was 0.15 days (8.54 → 8.38).
The synthetic generators were easier than reality and different from it, so effort spent searching was worth less than effort spent on the benchmark.

* **Do:** build visible benchmarks from real data wherever possible, and keep a real-derived family held out.
* **Do:** treat a large visible/held-out gap as a benchmark defect, not a model defect.

### 5. Blind Proposals Are Cheap to Police but Slow to Converge

The agent could read code but not run it, which removed any route to the held-out data or the confirmatory statistics.
The cost was a low hit rate: about one substantive keep in every eight iterations.
Several reverted proposals scored far worse (up to 5.2 days), errors a single local test run would have caught.

* **Next:** give the agent a sandboxed `evaluate --visible` tool, and accept the extra overfitting risk only with a stronger held-out set.

### 6. The Agent Signalled Convergence; the Loop Did Not Listen

After iteration 28 the agent reported, five times in a row, that it had no further idea worth testing, and made no edit.
Those five calls cost about USD 2.10 and produced nothing.

* **Do:** stop after k consecutive no-edit or no-improvement iterations; treat the agent's own "nothing left" report as a stopping signal.

### 7. Walling Off Inference Made the Result Easy to Trust

No version of the candidate moved the scientific conclusions:

* H1 slope 0.005–0.042 days/yr
* snow-off effect 5.4–5.7 days per SD
* ΔR² for spring warmth 0.24–0.26

Because the loop was structurally separated from the confirmatory analysis, that robustness is a finding rather than a defence the paper has to mount.

* **Do:** keep agents on measurement and engineering problems with external ground truth;
  keep them off the inference path, where optimising a number is indistinguishable from p-hacking.

## What to Try Next

1. **Evaluator:** add synthetic multi-year panels with a known trend and driver effect, plus a behavioural-equivalence check that rejects no-op edits.
2. **Selection:** keep a Pareto archive across held-out error, interannual fidelity, and failure rate; select once at freeze.
3. **Benchmark:** draw visible seasons from real pixel-years, matched to MCD12Q2 or ground phenology where available.
4. **Tools:** a sandboxed visible-set evaluation tool, then measure whether the held-out gap widens.
5. **Stopping:** stop after three consecutive no-edit iterations.
6. **Comparison:** run the same loop with several models, or several independent agents, and compare search paths and gaming behaviour.
