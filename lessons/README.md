# Lessons

A ledger of times VIGIL — or its own self-audit — was **wrong**, and what was done about it.

This is the skill's durable memory. Not a changelog: a changelog records what changed, this
records what was *believed and false*, who caught it, and what now prevents a repeat.

## Why it exists

Every check in `evals/check_repo.py` from L7 onward was written after something slipped past
the ones before it. That pattern worked, but it lived in docstrings and in whoever happened to
be in the session. A new session inherited the checks and none of the reasoning — so the same
class of gap could be reintroduced by someone with no way to know it had already bitten.

The ledger makes the reasoning part of the repo. A fresh session reads `lessons/` and inherits
what was learned, not just what was built.

## The one rule that keeps it safe

**A lesson is a record of fact. It never changes VIGIL's behaviour by itself.**

Writing a lesson and mechanising it are two separate, separately reviewed acts. Nothing here
self-applies, self-patches, or self-updates. The human commits, always.

This is deliberate. An auditing tool that rewrites its own standards is grading its own
homework — and this repo has direct evidence of how that goes: see `0003-unverified-verification`,
where a claim of "manually verified" was itself unverified, inside a document written to guard
against exactly that.

## Format

One file per lesson, `NNNN-short-slug.md`, with frontmatter:

```yaml
---
id: 0007
date: 2026-07-30
found_by: cross-model review (Grok)      # who caught it
missed_by: check_repo L1-L13, two prior reviews   # what DIDN'T catch it
class: cross-file composition            # the generalisable shape
status: mechanized                       # mechanized | unmechanizable | open
check: L15                               # required iff status: mechanized
---
```

Then prose: what was believed, why it was false, what the evidence was, what changed.

**`missed_by` is the most valuable field.** Knowing what failed to catch something tells you
where the next gap is. "Found by a human reading carefully" and "found by L8" are very
different signals — and the current ledger shows the automated self-audit missing four of
five, which is worth knowing before trusting a green run.

### Controlled vocabulary

`found_by` and `missed_by` are **comma-separated identifiers**, not prose — the dashboard
parses them. Prose belongs in `found_detail` / `missed_detail`, which nothing parses.

| Id | Means |
|---|---|
| `author` | Whoever was implementing at the time |
| `self-audit` | `check_repo.py` |
| `subject-model` | The model being audited, catching it about itself |
| `harness-design` | A review of the eval harness design |
| `grok`, `kimi` | Cross-model review |
| *anything else* | Shown verbatim — use your GitHub handle |

Splitting free prose on commas once produced contributor rows reading "mid-run" and
"unprompted". Keep the ids clean.

### The dashboard

[`LEDGER.md`](../LEDGER.md) is generated from these files by `evals/build_ledger.py` and
kept honest by `L18`. Contributors rank by **distinct classes surfaced**, never by lesson
count: rewarding volume would incentivise splitting one finding into five, which is the exact
gaming pattern `engines/scoring.md` documents for N/A redistribution. Do not change that
metric without reading why it is what it is.

## Status values

| Status | Means | Requirement |
|---|---|---|
| `mechanized` | A check now catches this class | `check:` must name a check that exists |
| `unmechanizable` | Genuinely not machine-checkable | Must say *why*, in the body |
| `open` | Should be mechanized, isn't yet | Must appear in `docs/OPEN-DESIGN.md` |

`L17` in `evals/check_repo.py` enforces all three. A lesson cannot claim to be mechanized
without the check existing, and an `open` lesson cannot quietly disappear.

## Adding one

1. Copy `TEMPLATE.md`, take the next number.
2. Fill it in — especially `missed_by`.
3. Decide whether the class is mechanizable. If yes, write the check *in the same commit*.
4. Run `python3 evals/check_repo.py`. L17 will reject an inconsistent ledger.
5. Commit. A human reviews; nothing lands automatically.

## Never send us your work

**A lesson is about a class of error, not about your codebase.**

This is the rule that matters most, and it is not paranoia — this repo previously shipped a
live business's domains, payment-compliance posture and architecture in its own documentation.
It took four sweeps to clear, because each instance described the same business in different
words. Three independent reviews had read those files without flagging them. See
[`0006`](0006-context-file-is-an-attack-map.md).

### What must never appear in a lesson

| Never | Why |
|---|---|
| Absolute paths (`/Users/<you>/work/...`) | Names you, your employer, and your project |
| Real hostnames, internal or external | Maps infrastructure |
| Emails, tickets, customer or vendor names | Identifies people and relationships |
| Anything key-shaped | Obvious, and it has happened to better projects |
| **Your `.vigil/context.md`** | It is *designed* to enumerate existential controls and critical paths. Pasted in, it is an attack map with a byline |
| A described weakness in a named system | The most dangerous item here, and the only one no scanner catches |

That last row is the real risk. A useful lesson says *"VIGIL rated X as LOW and it should have
been HIGH"* — and to make it concrete you reach for your real finding. What lands is a public,
indexed, permanent description of your organisation's security gap, attributed to you.

### What to send instead

Reduce to the shape. VIGIL's own reasoning is the model: nothing in this ledger names a real
system, and none of the lessons are weaker for it.

> ❌ "On acme-payments, VIGIL rated the unauthenticated `/internal/refund` endpoint LOW."
>
> ✅ "VIGIL rated an unauthenticated internal-only endpoint LOW because the route was not in a
> public router. The reachability check trusted the router table; the service was reachable
> from a peer over the mesh."

The second is *more* useful — it states the class. The generalisable part is almost never the
proprietary part, so redaction usually costs nothing.

If a lesson cannot be written without your system in it, it is not a lesson yet. It is an
incident report, and it belongs in your own tracker.

### What enforces this

`L19` scans `lessons/` and `evals/results/` for absolute home paths, non-example hostnames,
emails, API-key shapes and private-key blocks. It is deliberately noisy in one direction: it
would rather flag a legitimate citation than let one real hostname through. If it flags a real
standards URL, add it to `ALLOWED_HOSTS` with a reason.

**L19 cannot read prose.** "We rely on a legacy service for authorisation and it is not covered
by tests" has no path, no host, no key — and every detail an attacker wants. A maintainer reads
every lesson before merge. If you are not sure, redact more; nobody has ever regretted a lesson
being too generic.

## For a public repo

Lessons are the best contribution surface this project has. A pull request that says *"VIGIL
told me X, here is why X was wrong"* is more valuable — and far safer to accept — than a pull
request that edits a rule. The first is evidence; the second is an assertion about evidence.

If you found VIGIL wrong, that is the contribution. Send the lesson.
