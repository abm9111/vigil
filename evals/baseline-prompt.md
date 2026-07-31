# The control prompt

This is what the **without-VIGIL** arm is given. It is the single most contestable artifact in
the whole harness, so it lives in a file where it can be argued with rather than inside
`run_eval.py` where it would be easy to miss.

## The prompt

```
Audit this codebase and report every problem you find.

For each finding give:
  - a severity: CRITICAL, HIGH, MEDIUM, LOW or INFO
  - the file and line it is at
  - what is actually wrong, and why it matters

Run whatever linters, type checkers, security scanners and tests are available
before forming an opinion, and say which ones you ran. If a tool you would want
is not installed, say so rather than guessing.

Cover at least: security and secrets, dependency vulnerabilities, correctness
bugs, error handling, data handling, and test coverage.

Output the findings as JSON.
```

## Why this control and not a weaker one

A benchmark's result is decided by its control, and the temptation is to pick one that flatters.
`"look at this code"` would produce a large, meaningless delta. So this prompt deliberately
hands the control **most of what VIGIL's structure provides**:

| VIGIL provides | The control is given it too |
|---|---|
| Severity vocabulary | asked for, by name |
| Evidence before opinion (`RULES.md` Rule 1) | told to run tools first and name them |
| Tool-gap honesty (N/E) | told to say so rather than guess |
| Cluster coverage | the six broadest categories, named |
| Machine-readable output | asked for JSON |

What the control does **not** get is the thing actually under test: eleven cluster files with
specific probes, the correlation engine, severity floors, the evidence ceiling, and the scoring
model. If VIGIL cannot beat a competent prompt that was handed its vocabulary, that is a real
result about VIGIL and the harness exists to surface it.

This is a deliberately hostile control. That is the point — a friendly one measures nothing.

## What a fair reading of the delta looks like

- **Recall delta** is the headline: did the skill find defects the prompt alone missed?
- **False-positive delta matters just as much and cuts the other way.** A skill that raises
  recall by inventing more findings has not improved anything, which is why `clean-control`
  exists and why both arms are scored by the identical scorer.
- **A near-zero delta is a finding, not a harness bug.** It would mean the structure is
  redundant for that fixture, and the honest response is to record it — see `levnikolaevich`'s
  argument in [`../docs/OPEN-DESIGN.md`](../docs/OPEN-DESIGN.md) that modern models need less
  scaffolding than this project assumes. Nobody has measured it. This is how.

## Changing this prompt

Treat it like `min_recall`: **strengthening the control is always allowed; weakening it to
improve the delta is not.** A weaker control raises VIGIL's apparent value without changing
VIGIL, which is the definition of gaming a benchmark. If you weaken it, say so in the commit
and re-run every published number.
