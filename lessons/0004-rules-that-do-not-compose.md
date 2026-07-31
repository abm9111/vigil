---
id: 0004
date: 2026-07-30
found_by: grok, kimi
missed_by: self-audit, grok
found_detail: cross-model review; a second instance found later
missed_detail: check_repo L1-L14; each rule is correct read alone
class: cross-file composition — two sound rules, one unsound combination
status: mechanized
check: L15, L16 (partial — see below)
---

# Correlation could raise the score by deleting findings, twice, through two different channels

## What was believed

That correlation and scoring composed correctly. Each rule read fine in isolation: correlated
findings replace their constituents (Rule 7); scoring uses the correlated severity; severity
floors cap the grade by the worst unresolved finding.

## Why it was false

**Channel one — the average.** Constituents were removed from their clusters, but no rule
assigned the correlated finding's penalty to *any* cluster. Three HIGHs in Security take that
cluster to 70; correlate them into one CRITICAL and Security returns toward 100 with the
penalty charged to nobody. Escalating severity while *raising* the average.

**Channel two — the floor.** Rule 7 said correlated severity is "ALWAYS >= max of
constituents", but correlation pattern 5 downgrades unreachable CVEs. Since floors read the
correlated severity, a HIGH CVE absorbed into a LOW correlation lifts the 79 cap and drops the
penalty from 10 to 1. The first fix closed the average; the same exploit remained through the
floor.

**And once more, in a third file.** `modes/siege.md` restated the reachability ladder with no
fence at all — so the Rule 7 carve-out was bypassable by running the adversarial mode, which is
where it was most likely to be used.

## What changed

Correlated findings now carry a primary cluster and charge the penalty there. Ignoring a
correlation restores its constituents. Pattern 5 is fenced explicitly: a downgrade requires
positive evidence of non-reachability, and moves the penalty and fix order but **never the
floor**. L15 now fails any file restating the ladder without its fence.

## Why this class matters

Three Criticals across two reviews came from this shape, and none were visible in a diff —
every individual file read correctly. It is the hardest class here and only partially
mechanized: L15 catches this specific ladder, L16 protects one specific formula, but general
cross-file semantic contradiction is not machine-checkable today (see `docs/OPEN-DESIGN.md`).

The practical rule: when a rule is restated anywhere, the restatement inherits every fence the
original carries. A rule copied without its exceptions is a loophole with a citation.
