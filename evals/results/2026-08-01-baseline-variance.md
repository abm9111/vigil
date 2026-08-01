# Baseline, first attempt — the variance is larger than the effect

**Date:** 2026-08-01 · **Runs:** 1 per arm · **Verdict: the question is still unanswered, and
now I know why.**

## The measurement that matters

The same arm, on the same fixture, with identical code and an identical prompt, run twice:

| | recall | false positives | defects matched |
|---|---:|---:|---:|
| treatment, run 1 | **0%** | 3 | 0 of 6 |
| treatment, run 2 | **83%** | 4 | 5 of 6 |

Eighty-three points of spread between two draws of the same distribution. Run 1 emitted three
findings; run 2 emitted twelve.

**Any effect this harness was built to detect is smaller than its own noise.** A single run is
not a measurement, and every number produced from one — including every number in this
directory's earlier files — is one sample presented as a quantity.

## What that invalidates

`min_recall: 0.8` has been enforced since the harness existed, and `L12` holds it in code
specifically so lowering it takes a visible two-file edit. That discipline is sound and the
threshold it protects is, on this evidence, **a coin flip**. Unchanged code could pass or fail
depending on the draw.

The honest reading of `evals/results/2026-07-30-run1.md` — "83% recall" — is now *one sample
that happened to land at 83%*, not a property of the tool.

## The delta, stated with its caveat

From the runs that completed, on `--runs 1`, which the above says is not enough:

| Fixture | control | VIGIL | delta |
|---|---|---|---|
| `clean-control` | 100% recall, **6 false positives** | 100% recall, **0 false positives** | −6 FP |
| `data-export-pipeline` | 83% recall, 2 FP | 83% recall, 4 FP | 0 recall, +2 FP |

Read literally that is *"VIGIL beat the control on 0 of 1 measurable fixtures"*, and it is what
the harness prints. **Do not quote it.** With 83 points of run-to-run spread, neither row
distinguishes a real effect from a draw.

The one row that is *suggestive* rather than measured: on a fixture seeding **no** defects, a
competent prompt invented six findings and VIGIL invented none. That is what the discipline
layer claims to do, on the fixture `RULES.md` calls the sharpest signal in the suite. One
sample. Suggestive, not shown.

## What it cost to learn this

Roughly ten CLI invocations, of which most measured nothing, across four harness defects each
found by the next attempt rather than by a test:

- isolation via `CLAUDE_CONFIG_DIR` also severed credentials — the control arm could not run
- `--disable-slash-commands` is documented as *"Disable all skills"* and does not hide them
- the skill was stashed *inside* the skills tree, where it stayed discoverable under its new
  name — caught only because that name happened to contain the string it was checked for
- both filesystem guards used `rglob`, which does not follow symlinks, and the skill is
  installed **as** a symlink

The worst outcome was not any of those. It was the run where a wrapper bug removed the skill
from **both** arms, the treatment arm scored 0%, and the harness printed *"VIGIL beat the
control on 0/2 fixtures — fixtures with no improvement are a result about VIGIL, not a harness
failure."* That sentence was mine. It was wrong, it was quotable, and it would have been
published as an unusually honest null result.

`implausible()` and the symmetric arm guards exist because of it, and both fired on their next
outing.

## What would actually answer the question

**`--runs 5` per arm, minimum**, reporting median and full range — 20+ invocations. Anything
less measures the draw.

And the limit no run count fixes: both fixtures are small synthetic repos written by this
project. This anchors *fixture* numbers, not field performance. A real answer needs both arms
against a real codebase with independently established ground truth, which nothing here
supports yet.

**`D5` stays open.** It is better characterised than it was this morning — the blocker is
sample size and fixture realism, not tooling — but it is not answered.
