---
id: 0013
date: 2026-08-01
found_by: author
missed_by: self-audit, L19, ci, grok, kimi
found_detail: a pre-publication sweep grepped the tracked tree directly instead of trusting the check that covers it
missed_detail: L19 globbed *.md in the contributed directories; the artifacts that carry resolved paths are *.json
class: a privacy check aimed at the surface a human writes, while the machine-written artifact beside it leaked
status: mechanized
check: L19
---

# The check that forbids real paths in contributed material scanned the prose and not the data

## What was believed

That `evals/results/` was covered. `L19`'s own docstring names it as one of the three
contributed surfaces, its pattern for a home directory is correct, and its comment records a
previous fix in exactly this area:

> No username is exempt. An earlier version excluded the maintainer's own login to silence a
> false positive, which made the check blind to precisely the paths most likely to leak from
> the maintainer's machine — and baked that login into the repo.

So the pattern had already been hardened against this leak, deliberately, with the reasoning
written down. The directory was in scope. The check reported clean.

## Why it was false

```python
surfaces += list(results.glob("*.md"))
```

A **run result is JSON.** The Markdown in `evals/results/` is the write-up a human composes
afterwards, and a human composing a write-up does not paste their home directory into it. The
artifact the tool emits does, because recording where each scanner resolved to is the whole
point of preflight evidence:

```json
"ruff":  {"version": "0.15.10", "path": "/Users/<maintainer>/<env>/bin/ruff"},
"mypy":  {"version": "2.1.0",   "path": "/Users/<maintainer>/<env>/bin/mypy"},
```

Nine occurrences across two files, including a local username, a tooling-environment name, and
an absolute path to the project's own config quoted inside a prose justification field. Found
by grepping the tracked tree by hand while deciding whether the repo could be published —
**not** by the check whose entire purpose is that question.

Widening the glob immediately surfaced a second thing the `.md`-only scan had never seen: a
hostname in a JSON field. That one was a legitimate citation and is now allowlisted with its
reason. Both had been invisible for the same reason.

## What changed

`L19` scans `*.md` **and** `*.json` across `lessons/`, `evals/results/`, `proof/` and
`corpus/`. The artifacts were scrubbed to `<ambient-env>`, which preserves the finding — the
audited project resolves its tools from an ambient environment it does not declare — while
removing whose machine it was.

A negative test now mutates the **JSON** artifact, not only the Markdown.

`corpus/` was added at the same time. `L27` already re-runs the privacy gate over every
bundle, but that validates a bundle against the closed schema, which is a different question
from whether a free-text field names somebody. Two checks over one directory asking different
questions is not redundancy.

## Why this class matters

The repository's defining claim is that a run record is content-free **by construction** —
closed schema, every string an enum, no field a path can occupy. That claim holds, and it is
about `.vigil/runs/`. `evals/results/` is a *different* artifact with no schema at all, and
the strength of the guarantee next door is part of why nobody looked.

The general shape: **a control scoped to the human-authored surface, beside a machine-authored
one that is strictly more likely to carry the thing being controlled for.**

| Reviewed | Emitted beside it, unreviewed |
|---|---|
| the incident write-up | the attached log bundle, with tokens in query strings |
| the PR description | the CI job output it links to |
| the bug report | the core dump, the HAR file, the profiler trace |
| the model card | the eval artifacts, carrying raw prompts |
| this repo's `results/*.md` | this repo's `results/*.json` |

Machine-written artifacts are the leaky ones precisely because nobody composed them. There is
no moment where an author decides what to include, so there is no moment where they decide to
leave something out. When scoping a redaction control, the question is not *which directory*
but **which file in it was written by a program**.

The narrower operational lesson: three cross-model reviewers and a 34-check self-audit had all
been over this repository, and the leak was found by one `git grep` run because someone was
about to publish and did not want to rely on the check. Before an irreversible step, verify the
property directly rather than asking the mechanism that claims to guarantee it.
