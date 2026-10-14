"""Autoresearch driver. Enforcement lives here, outside the agent.

Each iteration:
  1. verify evaluate.py, synth.py, and the gap library against the lock outside the repository
  2. call `claude -p` with Read and Edit only, Edit limited to method.py, held-out paths denied
  3. revert every changed file other than method.py; discard the iteration if any appeared
  4. re-verify the lock, run the evaluator, keep (commit) or revert method.py
  5. append a ledger row
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
METHOD = "src/wapusk_greenup/method.py"
LEDGER = HERE / "ledger.jsonl"
HELDOUT = Path(os.environ.get("WAPUSK_HELDOUT_DIR", Path.home() / ".wapusk-autoresearch"))


def sh(*args: str, check: bool = True, **kw) -> str:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True, **kw).stdout.strip()


def verify_lock() -> None:
    lock = json.loads((HELDOUT / "lock.json").read_text())
    for rel, digest in lock.items():
        if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"LOCK VIOLATION: {rel} changed. Stopping.")


def changed_files() -> list[str]:
    """Tracked files with changes plus untracked, non-ignored files."""
    tracked = sh("git", "diff", "--name-only", "HEAD").splitlines()
    untracked = sh("git", "ls-files", "--others", "--exclude-standard").splitlines()
    return sorted({f for f in tracked + untracked if f})


def evaluate() -> dict:
    r = subprocess.run([sys.executable, str(HERE / "evaluate.py")], cwd=ROOT, capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        return {"score": float("inf"), "error": r.stderr[-2000:]}
    return json.loads(r.stdout)


def ledger_tail(n: int = 15) -> str:
    if not LEDGER.exists():
        return "(no earlier iterations)"
    rows = [json.loads(line) for line in LEDGER.read_text().splitlines()][-n:]
    return "\n".join(
        f"iter {r['iteration']}: score {r['score']:.3f} ({'kept' if r['kept'] else 'reverted'}) - {r['rationale'][:300]}"
        for r in rows
    )


def call_fake_agent(script: str) -> dict:
    """Testing only: run a local script in place of the agent to exercise the enforcement path."""
    r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True, timeout=300)
    return {"result": r.stdout.strip() or "(fake agent)", "total_cost_usd": 0.0}


def call_agent(best: float, model: str, budget: float) -> dict:
    prompt = (
        (HERE / "program.md").read_text()
        + f"\n\n## Current State\n\nBest score so far: {best:.4f}\n\nRecent iterations:\n{ledger_tail()}\n"
    )
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--tools", "Read,Edit",
        "--allowedTools", "Read", f"Edit({METHOD})",
        "--disallowedTools", f"Read(/{HELDOUT}/**)", "Read(autoresearch/setup_heldout.py)",
        "--permission-mode", "dontAsk",
        "--safe-mode",
        "--strict-mcp-config",
        "--output-format", "json",
        "--max-budget-usd", str(budget),
    ]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=1800)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"result": f"(agent call failed: {r.stderr[-500:]})", "total_cost_usd": None}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=30)
    ap.add_argument("--model", default="opus")
    ap.add_argument("--budget-per-call", type=float, default=2.0)
    ap.add_argument("--fake-agent", help="testing only: script to run instead of the agent")
    args = ap.parse_args()

    if changed_files():
        raise SystemExit("Working tree is not clean; commit or stash first.")
    branch = f"autoresearch/{datetime.now():%Y-%m-%d}"
    if sh("git", "rev-parse", "--abbrev-ref", "HEAD") != branch:
        sh("git", "checkout", "-B", branch)

    verify_lock()
    best = evaluate()["score"]
    start = len(LEDGER.read_text().splitlines()) if LEDGER.exists() else 0
    print(f"start score {best:.4f} on {branch}", flush=True)

    for i in range(start + 1, start + args.iterations + 1):
        verify_lock()
        agent = call_fake_agent(args.fake_agent) if args.fake_agent else call_agent(best, args.model, args.budget_per_call)
        changed = changed_files()
        stray = [f for f in changed if f != METHOD]
        if stray:
            tracked = set(sh("git", "ls-files", "--", *stray).splitlines())
            for f in stray:
                if f in tracked:
                    sh("git", "checkout", "--", f)
                else:
                    (ROOT / f).unlink(missing_ok=True)
            sh("git", "checkout", "--", METHOD)
            if changed_files():
                raise SystemExit(f"Could not restore a clean tree after stray edits: {changed_files()}")
        verify_lock()

        diff = sh("git", "diff", "--", METHOD)
        if stray or not diff:
            result, kept = {"score": float("inf")}, False
        else:
            result = evaluate()
            kept = result["score"] < best - 1e-6
        if kept:
            best = result["score"]
            sh("git", "add", METHOD)
            sh("git", "commit", "-m", f"autoresearch iter {i}: score {best:.4f}\n\n{agent.get('result', '')[:1500]}")
        elif diff:
            sh("git", "checkout", "--", METHOD)

        row = {
            "iteration": i,
            "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "diff_sha256": hashlib.sha256(diff.encode()).hexdigest() if diff else None,
            "score": result["score"],
            "visible": result.get("visible"),
            "kept": kept,
            "stray_edits": stray,
            "rationale": (agent.get("result") or "").strip(),
            "cost_usd": agent.get("total_cost_usd"),
            "model": args.model,
        }
        with LEDGER.open("a") as f:
            f.write(json.dumps(row) + "\n")
        sh("git", "add", str(LEDGER.relative_to(ROOT)))
        sh("git", "commit", "-m", f"autoresearch ledger: iter {i}")
        print(f"iter {i}: score {result['score']:.4f} {'KEPT' if kept else 'reverted'}"
              f"{' STRAY ' + str(stray) if stray else ''} cost {row['cost_usd']}", flush=True)


if __name__ == "__main__":
    main()
