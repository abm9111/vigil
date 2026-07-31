---
id: 0005
date: 2026-07-30
found_by: kimi
missed_by: author, self-audit
found_detail: cross-model review, with a reproducing probe
missed_detail: the author, who had just 'fixed' this twice
class: a measurement instrument that fails in both directions
status: open
check:
---

# The eval reported 100% recall for an audit containing no analysis — twice, after two fixes

## What was believed

That `run_eval.py` measured whether VIGIL finds seeded defects. It had already been hardened
once: an evidence gate was added after hedged, location-free findings scored 100%, and line
anchoring was added after keyword-sprinkling scored 100%.

## Why it was false

Both fixes were weaker than claimed.

**The evidence gate** accepted `"a ratio of 1:2"` and `"section 2.3:1"` — the pattern was
`:\d+`, so "evidence" degraded to "contains a colon followed by a digit."

**Line anchoring** extracted *every* 1–4 digit number in the finding text, not the cited
location. A probe citing entirely wrong lines, with one incidental number each
(`build_export.py:5 affects 31 rows`), scored **100% recall, PASS**.

The instrument had also failed in the opposite direction earlier — a truncating parser reported
50% for a run that had found everything, and greedy assignment reported 100% by matching
defects to the wrong findings. Six harness bugs in total, every one producing a confidently
wrong number.

## What changed

Citations only (`path.ext:77`, `"line": 77`), never surrounding prose. Deflation of a HIGH by
even one level now fails, because that same deflation moves the product from "not
production-ready" to "production-ready". The probe now scores 33% and FAILS.

`evals/README.md` states plainly that this is a smoke regression over six defects in two
fixtures against one model — it detects that something broke, it does not establish that VIGIL
catches production defect classes.

## Why this class matters

Left **open** rather than mechanized, because the underlying problem is not fixed: matching is
still keyword-plus-location, and anyone who has read the fixture can satisfy every mechanical
criterion without understanding anything. The real fix is structured finding fields
(`docs/OPEN-DESIGN.md` D3).

The generalisable warning: a metric that has been "fixed" is still a metric someone can satisfy
without doing the work. Probe your own instrument adversarially before quoting it — and quote
a *failing* run more readily than a passing one.
