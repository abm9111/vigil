# Third-model review — 2026-08-01

A third independent reviewer, run after Grok and Kimi, on the pre-publication tree
(`6df1330`). Engine: GPT-5.5, reasoning effort high, read-only sandbox, throwaway clone.
The brief named what was already closed and asked for a ninth defect.

**Result: three findings, all confirmed by reproduction rather than by argument.** Two more
were found in the same session by attacking the checks directly — those are `lessons/0014`.

At the time of this review the repository ran **35 structural checks and 167 tests**. They
found none of the five.

## What the third model found

### 1 · An array without `items` reopens the closed-schema guarantee — HIGH

`evals/privacy_gate.py` descended into a list only when the schema declared `items`, so
`{"type": "array"}` accepted every element unexamined. `L25` checks strings and objects and
never required `items`. Reproduced:

```
validate() errors : []
scan_leaks() hits : []
L25 did NOT object
```

on `{"notes": ["auth bypass in the internal refund workflow"]}`.

Latent — no such field existed — but the guarantee in `CONTRIBUTING.md` and `SECURITY.md` is
that a description of your work has *no field to occupy*, and this was a field to occupy. The
leak scanner would not have caught it either: it looks for paths, hosts and key shapes, and a
sentence describing an architecture has none.

**Fixed.** Both the gate and `L25` refuse an array with no `items`. The one legitimate case —
`bundle.records`, whose elements `check_bundle()` validates against the record schema — must
now say so with `x-validated-by`, because "validated elsewhere" and "not validated" were
indistinguishable from inside the validator.

### 2 · Suppression semantics contradicted each other — HIGH

`FLAGS.md` said a suppressed finding is hidden from output and excluded from scoring.
`engines/scoring.md` said it is always reported at its mechanically-derived severity and that
acceptance never deletes, downgrades, or removes it. `FLAGS.md` also contradicted itself three
lines later.

Two auditors following different files produce different reports from identical findings.

Worse: `.vigil/ignore` was specified as bare patterns, one per line, in a file that lives
**inside the audited repository**, against `scoring.md`'s *"Never accept a suppression that is
anonymous or open-ended — that is the audited party grading itself."* A repo could suppress its
own HIGH findings and keep a green gate — the shape `SECURITY.md` names as an in-scope
vulnerability.

**Fixed.** `FLAGS.md` now matches `scoring.md`; every `.vigil/ignore` entry carries an owner
and an expiry, and an entry with neither is not a suppression. `L36` holds the two files
together.

### 3 · Stale check counts where `L24` could not see — LOW

`Makefile` and `.pre-commit-config.yaml` both claimed 33 checks while 35 ran. `L24` scanned
Markdown and `.github/*.yml` — neither of those, and they are the two files a contributor
actually invokes.

**Fixed.** Both are in scope, with a negative test on a non-Markdown gate surface.

## Surfaces it examined and reported sound

`install.sh`; Rule 1a / 3a / 7 / 10a composition; CI/Makefile command parity; the current
run-record schema; the privacy-gate fixtures.

Reporting a surface as sound is useful output, not a failed search — a false positive costs
more here than a miss, because the argument of this project is that a clean report means
something.

## What this round says about the method

| Round | Reviewer | Found | Overlap with prior |
|---|---:|---:|---|
| 1 | Grok | 4 | — |
| 2 | Kimi | 4 | near zero |
| 3 | GPT-5.5 | 3 | none |
| 3 | direct attack on the checks | 2 | none |

Three rounds, no decline in yield, no meaningful overlap. The automated suite has now found
**0 of 12**.

The honest reading is not that the checks are worthless — they catch regressions, and every one
exists because something got past the ones before it. It is that **a check written by whoever
wrote the thing it checks tests the failure mode that person already imagined.** Every finding
in this table came from somewhere else.
