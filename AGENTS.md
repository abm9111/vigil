# AGENTS.md

Instructions for a coding agent working **on this repository**. If you are looking for what
VIGIL does when *run*, that is `SKILL.md` and `README.md` — this file is about changing it.

## What this repo is

An auditing skill whose "code" is mostly instructional Markdown that a model reads and
follows. The Python under `evals/` and `tests/` supports it; it is not the product.

That inversion matters. A contradiction between two Markdown files is a **functional bug**,
not a style issue: two auditors reading the same rules would compute different scores. Most
of the self-audit exists to catch exactly that.

## Before you finish any change

```bash
python3 evals/check_repo.py       # 34 structural checks · <1s · no LLM, no network
python3 evals/check_loadable.py   # the skill is still discoverable
pytest tests/ -q                  # every check must be able to FAIL
mypy && ruff check .              # config in pyproject.toml
python3 evals/build_ledger.py     # only if you added a lesson
```

All of it runs offline and without an API key. CI runs the same commands, so a green local
run means a green pipeline.

**`evals/run_eval.py` is the exception** — it invokes the Claude CLI and costs money per run.
Never call it without `--from-file`. The same applies to `check_loadable.py --live`, and
doubly to the baseline arms (`--arm control` / `--arm vigil`), which are two runs per fixture.

The baseline arm answers the question every other number here depends on — *does the skill beat
a competent prompt?* — and it is allowed to come back negative. If it does, that is a result
about VIGIL. **Strengthening `evals/baseline-prompt.md` is always allowed; weakening it to
improve the delta is gaming the benchmark.**

## Four rules that are not negotiable

**When a gap gets past the checks, add a check — not just a patch.** The patch fixes one
instance; the check fixes the class. Every check from L7 onward exists because something
slipped past its predecessors, and `tests/test_check_repo.py` asserts that every documented
check has a test proving it can fail. Adding a check without that test fails the suite.

**Never lower a threshold to make a run pass.** `min_recall` and `max_false_positives` are the
contract. `L12` holds the floors in `check_repo.py` — in code, not in the manifests it
validates — so lowering one takes a visible two-file edit. A failing eval means a regression
or a fixture finding a real gap; both are information, and editing the threshold discards it.

**A rule restated anywhere inherits every fence the original carries.** A rule copied without
its exceptions is a loophole with a citation — see `lessons/0004`, where the same exploit
reappeared through a second file after being closed in the first. `L15` now enforces one
instance of this.

**Never commit anything identifying a real system.** No absolute paths, no hostnames, no
`.vigil/context.md` content. `L19` catches the mechanical shapes and cannot read prose. This
repo previously shipped a live business's domains through three reviews (`lessons/0006`).

**Never add a free-text field to the run-record schema.** The privacy guarantee for field
telemetry is structural, not procedural: a path or finding description has no field to occupy,
so it is unrepresentable rather than redacted. One `{"type": "string"}` added to capture "just
the tool version" reopens the whole surface while every existing test still passes. `L25`
refuses it — if you find yourself wanting to disable that check, the design has changed and
that is a conversation, not a commit.

## Mutating a prose check

Several checks (`L28`, `L30`-`L33`) assert that a rule is still *stated* in a Markdown file,
because the thing they guard is executed by a model reading that file — there is no function to
unit-test. This family does real work and has one specific failure mode:

**A loose alternative in the pattern fails silently, toward green.** Five instances so far:
`L28` matched a bare `default —` that survived the default being flipped to *yes*; `L30`
assumed a plain line break in a clause that wraps inside a blockquote; `L31` had `**no**` as an
alternative, which matched an unrelated bolded "no" and stayed green after *not sufficient* was
inverted to *sufficient*. In every case the check reported the rule intact while the rule said
the opposite.

Two rules follow, and they are cheap:

**Key every alternative to text that changes when the meaning changes.** `default is no`
inverts to `default is yes` and the pattern fails, which is what you want. `default —` survives
the inversion, so it guards nothing.

**Mutate by inverting the rule, never by deleting it.** A deletion test only proves the pattern
needs its text present. An inversion proves it keys on the part carrying the meaning — and it
is also the realistic erosion, since nobody deletes a safety rule, they soften it. Converting
`L30` and `L31` from deletions to inversions immediately exposed the `L31` pattern above.

**`tests/test_prose_clauses.py` enforces both.** It inverts every clause individually and
asserts that clause's own check reports it — because a five-clause check passes its
single-mutation test if any one clause fires, leaving the other four free to match incidental
text. Adding it found two more instances immediately: `L28`'s default clause alternated across
two statements of the same rule, so inverting one left the other matching, and its off-switch
clause matched an incidental second mention of `telemetry: off`. Add a probe there for every
new prose check.

## Where things live

| Path | Role |
|---|---|
| `SKILL.md` | Router — which files load in which mode |
| `RULES.md` | Iron rules. Rule 1 (evidence before opinion) governs everything |
| `engines/scoring.md` | **Single authority** for cluster weights. Headers restate it; `L13` enforces the match |
| `clusters/`, `modes/`, `engines/` | The instructional surface |
| `evals/` | Self-audit, fixture measurement, ledger generation |
| `tests/` | Proof that each check can fail |
| `lessons/` | Times VIGIL was wrong → `LEDGER.md` |
| `proof/` | Times VIGIL was right on someone else's code → `LEDGER.md` |
| `schemas/`, `corpus/` | Field-learning input: closed record schema, contributed bundles |
| `docs/FIELD-LOOP.md` | The whole loop at ten contributors, and where it is allowed to stop |
| `docs/OPEN-DESIGN.md` | Open decisions, with the argument already made |

## If you are asked to improve VIGIL

Read `docs/OPEN-DESIGN.md` first. **D1** is the largest real gap: 2 of 11 clusters have a probe
that can fail, so most of the weighted average is unevidenced by construction. Work there beats
adding surface area.

Do not add runtime dependencies. VIGIL orchestrates tools the user already has and imports
nothing beyond the standard library; that is a design constraint, not an oversight.

## Codex / other hosts

The skill is written for Claude Code but the content is host-agnostic — Markdown plus stdlib
Python. `check_loadable.py` currently validates Claude Code's discovery contract only. If you
add another host, add its loadability check rather than assuming the contracts match.
