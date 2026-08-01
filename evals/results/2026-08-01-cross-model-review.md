# Cross-model review — 2026-08-01, immediately before publishing

Two sandboxed reviewers, one brief, four named surfaces. Both ran read-only against the tree at
`c13e2d0`. Eight defects between them, **near-zero overlap**, and the automated suite — 33
structural checks and 119 tests at the time — found **none of them**.

Everything here is fixed with a regression test. Recorded so the next reviewer does not spend
an hour re-finding it.

## Why the numbers matter more than the findings

| Detector | Defects found |
|---|---|
| Self-audit + test suite, over a full day of development | **0 of 8** |
| Reviewer A, one pass | 4 |
| Reviewer B, one pass | 4 more |
| Author, re-reading own highest-risk file | 1 |

`CONTRIBUTING.md` already claimed a second reader was the main detection mechanism. This is the
measurement behind that claim, and it is stronger than the claim was.

**The discovery rate did not fall between rounds.** Two independent passes each yielded four.
That is the shape of a codebase where more defects remain, not one converging on clean — which
is why this repo went to invited private review rather than straight to public.

## The finding that should worry a reader most

Reviewer A examined `install.sh` and concluded *"safe default blast radius."* Reviewer B then
found that its update path ran `git reset --hard` over any allowlisted checkout, silently
destroying a contributor's uncommitted work — in the same file, within the hour.

**A reviewer's clean verdict was wrong.** Treat every "this surface is fine" here, including
this document's, as provisional.

## Rule composition — two holes, both `lessons/0004`

Both were between a rule added that week and one that had been there for months. Neither was
visible to any check.

**Withdrawal was cheaper than reduction.** Rule 1a authorised dropping a finding entirely,
gated on "and it holds", while Rule 3a put a four-level evidence ladder in front of a *one-step
severity reduction*. The stronger act had the weaker gate. Fixed: a mitigation comment now
enters the ladder at **Present**, which reduces nothing, and a withdrawn hit is reported *as
withdrawn* rather than vanishing into coverage notes.

**A severity floor could be erased through a second channel.** Rule 7 fences the floor for
reachability downgrades — the cap is computed from the constituent's severity, not the
correlated one. Rule 3a had no floor fence at all, so control credit was a global route to the
exploit Rule 7 closed locally. Worse, `engines/scoring.md` stated the cap rule *inverted* while
citing Rule 7 as its authority — in the file that computes the floor.

## The prose-check family — instances six through nine

Five checks assert a rule is still *stated* in Markdown via regex. Four more patterns were
found matching text that states the **opposite** rule, because the negation fell outside the
matched span. Each confirmed by running the real clause regex against inverted prose.

The meta-test written that morning to catch exactly this was itself too weak: it required one
inversion probe per *check*, so a five-clause check passed if any one clause fired. It now
requires one per **clause** — and failed on write, exposing 16 unprobed clauses.

Nine instances of one failure mode, three separate attempts to close it. The convention is in
`AGENTS.md`; it is a convention, not a fix.

## The privacy gate failed open three ways

The module whose stated purpose is that a user's code is *unrepresentable* — not redacted —
admitted free text through three routes, each verified open before the fix:

- an **unanchored pattern**: `re.search` let `[a-z]+` accept a long string containing a path,
  because a fragment matched. A pattern is a constraint on the whole value or it is not one.
- an **empty `{}` property schema**: a node asserting nothing accepted anything, and reads as an
  oversight rather than a hole in review.
- a **chained `$ref`**: resolution took exactly one step, leaving `$ref` on the node. `$ref` is
  a known keyword, so the unknown-keyword guard stayed silent and the node validated as
  unconstrained — **failing open while the module docstring promised fail-closed.**

That last one is the sharpest lesson in this document. The docstring said FAILS CLOSED in
capitals. It was wrong, and nothing tested the claim.

## Calibration notes on the reviewers

Worth recording, because a review's value depends on whether it overclaims.

- Reviewer B flagged one composition chain as *"a real ambiguity, not a proven erasure"* and
  correctly identified a check failure in its own sandbox as a directory-name artifact rather
  than a defect. Both calls were right.
- Reviewer A rated the gameable check count higher than warranted: disabling a check did leave
  the count unchanged, but the mutation test already caught it and CI runs both. Real defect,
  overstated severity.
- Neither invented findings. Every claim tested here reproduced.

## What this does not establish

That the repo is now clean. Eight found, eight fixed, and no reason to believe the ninth does
not exist — see the discovery-rate table above. What it establishes is that the automated
suite is not a substitute for a second reader, which is what this project said before it had
the evidence.
