---
id: 0002
date: 2026-07-30
found_by: subject-model
missed_by: author, harness-design
found_detail: the audited model itself, unprompted, mid-run
missed_detail: harness design review; the run scored a perfect 0
class: a benchmark the model can read is not a benchmark
status: mechanized
check: L12 (answer-key location), run_eval.py hard refusal
---

# A fixture scored 0 false positives while the answer key sat inside the audited directory

## What was believed

That `clean-control` — a fixture with zero seeded defects — was measuring VIGIL's
false-positive rate. It returned zero findings, the ideal result.

## Why it was false

`expected.json` was inside the fixture directory. With only two files in scope, the auditor
read it while enumerating the directory, and said so without being asked:

> "The audited directory contains `expected.json`, which is this fixture's answer key… If you
> are running this to measure VIGIL's false-positive rate, **this run is not a valid
> measurement**: the auditor saw the key."

A perfect score, and worthless. Worth noting the failure was caught by the *subject*, not the
experimenter — the experimenter had already written up the result.

## What changed

Manifests moved to `evals/expected/<fixture>.json`, outside every audited path. `run_eval.py`
now hard-refuses to score a fixture that still contains an `expected.json`, exiting 2 rather
than producing a number. L12 re-checks the location on every self-audit.

## Why this class matters

Applies to every eval, not this one. Before trusting any score, check what was inside the
scope — answer keys, prior results, the grading rubric, a git history containing the fix. The
model does not have to be adversarial for the measurement to be void; it only has to read what
is in front of it.
