# Referee Instructions

You are a skeptical referee for a remote-sensing ecology journal.
Review the manuscript `report/report.qmd` and its supporting material, then write a referee report.

## Read

* `report/report.qmd` and `report/references.bib`
* `prereg.md`, which fixed the analysis before it ran
* `results/tables/confirmatory.json`, `sensitivity.json`, `multiverse.csv`, `power_analysis.json`
* `results/tables/autoresearch_final.json` and `results/method_lock.txt` if present
* Any source file under `src/wapusk_greenup/` needed to check a claim

## Check

1. Every number in the manuscript against the result tables.
   Quote the sentence and the table value for each mismatch.
2. Claims the evidence does not support, including causal language from correlational results.
3. Missing or misreported uncertainty.
4. Deviations from `prereg.md` that the manuscript does not disclose.
5. Each reference: does it exist, and does it say what the manuscript cites it for?
   Use web search to verify.
6. Methodological weaknesses a reviewer at this journal would raise.

## Output

Write the report in Markdown with these sections:

* Summary of the submission (3–5 sentences)
* Major issues, numbered, each with the location, the problem, and a concrete fix
* Minor issues, numbered
* Number checks: a table of every mismatch found (or "none found")
* Reference checks: one line per reference with verdict
* Recommendation: accept, minor revision, major revision, or reject, with one paragraph of justification

Do not edit any file.
