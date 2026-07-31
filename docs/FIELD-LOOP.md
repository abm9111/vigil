# The field loop, with ten people using VIGIL

How a run on someone's laptop becomes a change to VIGIL — and every place the loop is
deliberately allowed to stop.

Written at n=10 because that is where the interesting failures start. At n=1 everything works
and nothing is learned; at n=10 the statistics can lie, one contributor can dominate, and the
privacy surface stops being hypothetical.

## The loop

```
  ON EACH CONTRIBUTOR'S MACHINE                    IN THIS REPO
  ─────────────────────────────                    ────────────
  1  /vigil audit
        │
        ▼
  2  .vigil/runs/<ts>.json          ← closed schema; content-free BY CONSTRUCTION
        │                             gitignored by their repo; never transmitted
        ▼
  3  privacy_gate.py --dir           ← fails closed
        │
        ▼
  4  learn.py --dir                  ← their own four signals (useful to them alone)
        │
        │   ......... a human decides to share. nothing automatic crosses this line .........
        │
        ▼
  5  corpus/<handle>.json  ──PR──▶   6  L27 + CI re-gate every bundle
                                          │
                                          ▼
                                     7  learn.py --corpus
                                          │  counts CONTRIBUTORS, not rows
                                          ▼
                                     8  signal? ≥3 contributors, ≥60% agree
                                          │
                                          ▼
                                     9  --draft-lesson  →  human writes the WHY
                                          │
                                          ▼
                                    10  lessons/NNNN + a check  →  LEDGER.md
```

Steps 1–4 are the whole loop for nine users out of ten, and that is fine. A contributor who
never opens a PR still gets step 4, which is the part that helps *them*.

## What changes at ten that is invisible at one

### The heavy user problem

Ten contributors. One runs VIGIL fifty times against an unusual monorepo; the other nine run it
twice each. That is 68 runs, and 74% of the rows belong to one person.

Pool the rows and you get:

| Statistic | Pooled | Truth |
|---|---|---|
| `VIGIL-EGRESS` no-evidence | **74%** — crosses the bar | 1 of 10 contributors |
| `VIGIL-CODE` false positives | **74%** — crosses the bar | 1 of 10 contributors |

Both would open a rule change affecting everyone, on evidence from one codebase, and the large
`n` would make it look well-supported. Nothing in the numbers reveals the concentration —
**and by design nothing can**, because records carry no repo identity to group by.

So the corpus statistic counts people:

> compute each rate **per contributor**, then count how many contributors exceed the threshold

One person with fifty runs gets one vote. On the same data the signal correctly reads *1 of 10,
10% agreement, no signal*. When seven of ten genuinely see it, it fires.

Removing the identifiers is what forces this, and it is the better statistic anyway. A rate
that survives being computed per-person is a rate about VIGIL; one that needs pooling is
usually a rate about somebody's repo.

### Stack skew

Eight Python contributors and two Go ones do not produce a fact about VIGIL — they produce a
fact about VIGIL on Python. `learn.py --corpus` prints the stack distribution under every
signal for exactly this reason. Read `VIGIL-EGRESS is unevidenced` as *unevidenced on the
distribution that submitted*, always.

### Version skew

Ten people are never all on the same version. If a rule changed between them, the pooled rate
for that cluster is meaningless. The corpus report warns when versions are mixed rather than
silently averaging across a behaviour change.

### Duplicate submissions

Two contributors auditing the same open-source repo submit overlapping evidence, and **there
is no way to detect it** — deduplication would need a repo identifier, which is the thing
deliberately not collected.

This is a real, accepted cost, and it is stated rather than papered over. It inflates
agreement, which is why the agreement bar is 60% and not 51%, and why a signal opens a draft
rather than changing anything.

## Where the loop is allowed to stop

Four places, all intentional:

**After step 4.** Most users never contribute. The local report is the value they get; the
project gets nothing, and that is an acceptable default for a security tool.

**At step 6.** A bundle that fails the gate is rejected **whole**, not filtered. If one record
smuggled a path, the submitter's redaction process is what failed, and keeping the clean ones
would launder that failure.

**At step 8.** Below three contributors there is no signal, only a description of somebody's
codebase.

**At step 9 — the important one.** The loop ends at a *draft*. An aggregate can say a rule
misfires; it can never say why. The why is the only part a maintainer cannot re-derive, and it
is the entire content of a useful lesson.

Auto-filing lessons would fill `lessons/` with the worthless half of a lesson and inflate every
number on the dashboard — which is the exact gaming pressure `build_ledger.py` already refuses
by ranking contributors on classes mechanized rather than lessons filed. A self-improving loop
that optimises its own scoreboard is the failure mode this project documents in
[`../engines/scoring.md`](../engines/scoring.md), not a feature to add.

## Why there is no server

No endpoint, no telemetry key, no opt-out to configure, no privacy policy to trust.

An auditing tool that phones home with findings is shipping a map of its users'
vulnerabilities, and no amount of encryption changes what the payload *is*. The transport is a
pull request because a PR is reviewable, revocable before merge, and already public — the
contributor can read exactly what they are sending, which is not true of any background upload.

The cost is real: participation will be a fraction of what a silent uploader would collect. A
smaller honest corpus is worth more than a larger one that nobody consented to, and for a tool
whose entire pitch is *evidence before opinion*, the alternative is not available.

## Running it

```bash
# contributor
python3 evals/privacy_gate.py --dir .vigil/runs
python3 evals/learn.py        --dir .vigil/runs

# maintainer
python3 evals/privacy_gate.py --dir corpus/ --bundles
python3 evals/learn.py        --corpus corpus/
python3 evals/learn.py        --corpus corpus/ --draft-lesson
```

Details: [`../engines/telemetry.md`](../engines/telemetry.md) ·
[`../corpus/README.md`](../corpus/README.md) · [`../proof/README.md`](../proof/README.md)
