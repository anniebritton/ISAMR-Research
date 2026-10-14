# Autoresearch Program: Green-Up Extraction

You are one iteration of an automated research loop.
Make one focused improvement to `src/wapusk_greenup/method.py`, then stop.

## Goal

`method.greenup_doy` estimates the day a pixel's NDVI season crosses `baseline + fraction * amplitude`.
Its input is one pixel-year of gappy, noisy daily MODIS NDVI with snow flags.
Lower the evaluator's score, which is mostly the mean error in days against known truth on synthetic seasons.

## The Contract

Read the docstring at the top of `method.py`.
The signature, argument meanings, and return convention are fixed.
Only `numpy` and `scipy` may be imported, along with `wapusk_greenup.smoothers`.
The function must be deterministic.

## What You Can Do

* Read any file in the repository.
* Edit only `src/wapusk_greenup/method.py`.
  Every other edit is reverted automatically, and the iteration is discarded.
* You cannot run code.
  The loop runs `autoresearch/evaluate.py` after you finish and keeps your change only if the score drops.

## What You Should Know

* `autoresearch/evaluate.py` defines the score.
  Errors are capped at 30 days, NaN counts as 30, and there are small penalties for line count and runtime.
* `autoresearch/synth.py` generates the visible seasons from three families:
  double logistic, snowmelt step plus ramp, and two-stage rise.
  Real cloud-gap patterns, negative outliers, and late snowfall are included.
* The final evaluation adds held-out seeds and a held-out family built from real NDVI season shapes.
  Methods tuned to the exact visible generators will lose there.
  Prefer changes that are physically motivated and robust over changes that fit `synth.py` parameters.
* `autoresearch/ledger.jsonl` lists earlier iterations, their scores, and whether they were kept.
  Read it first and avoid repeating failed ideas.
* `src/wapusk_greenup/smoothers.py` holds the pre-registered baselines.
  You may call or adapt them.

## Rules

* Do not try to read or infer the held-out data, seeds, or anything outside the repository.
* Do not special-case on the `family` of a season.
  The extractor never receives it.
* Keep the code readable and commented where the reasoning is not obvious.
  A person will review every kept change.

## Finish

End with two or three sentences: what you changed, and why you expect it to generalise.
That text goes into the ledger.
