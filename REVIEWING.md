# Reviewing VIGIL

You have been invited to review this before it goes public. This page exists so you can be
useful in ten minutes instead of an hour, and so you do not spend that hour re-finding things
that are already known.

**What would help most: find a ninth defect.** Two cross-model reviews found eight between them
with almost no overlap, and the automated suite found none of the eight. The discovery rate has
not dropped, so the working assumption is that more exist.

## Orient in two minutes

The product is **instructional Markdown that a model reads and follows**. The Python under
`evals/` checks that Markdown for self-consistency; it is not the product. A contradiction
between two Markdown files is a functional bug — two auditors reading the same rules would
compute different scores.

```bash
make check        # 33 structural checks, 143 tests, mypy, ruff — offline, no API key, ~20s
make help         # every target
```

| Read first | Why |
|---|---|
| [`RULES.md`](RULES.md) | The iron rules. Everything inherits these. Most defects found so far live here |
| [`docs/OPEN-DESIGN.md`](docs/OPEN-DESIGN.md) | Known-open decisions, with the argument already made |
| [`LEDGER.md`](LEDGER.md) | Times VIGIL was wrong, and which mechanism caught each |
| [`evals/results/`](evals/results/) | Prior review findings — **check here before reporting** |

## Already reviewed — please do not re-find these

Two sandboxed cross-model reviews ran 2026-08-01. All eight findings are fixed, each with a
regression test. Full write-up in
[`evals/results/2026-08-01-cross-model-review.md`](evals/results/2026-08-01-cross-model-review.md).

Summary of what is already closed: two rule-composition holes (Rule 1a vs 3a, Rule 3a vs Rule
7's floor fence), four leaky prose-check patterns, a gameable check count, three privacy-gate
holes that failed open, an installer that destroyed uncommitted work, and two direct rule
contradictions.

## Known-open — documented, not defects

Reporting these is not useful; they are stated in `docs/OPEN-DESIGN.md` on purpose.

- **`--baseline` has never been run.** VIGIL's core claim — that the skill beats a competent
  prompt — is unmeasured. This is the largest honest gap and it is stated in the README.
- **D1**: five of eleven clusters have no probe of their own, so they carry weight while
  measuring nothing. Confirmed in the field: a real run reported `ceiling: 85` on each.
- **Fingerprinting**: `stack` × `tools` × counts × ceilings could plausibly identify a known
  repo. Not a path leak; residual, and not yet written down.
- **`L28` cannot prove obedience.** It proves the consent instruction is *stated*. The one real
  run wrote its record, disclosed it, and never asked the question.
- **Prose checks have a convention, not a fix.** Nine instances of the same silent-green
  failure so far. See "Mutating a prose check" in [`AGENTS.md`](AGENTS.md).

## Where the risk actually is, ranked

1. **`install.sh`** — served as `curl … | bash`, runs on strangers' machines. Two defects found
   here already, one by a reviewer who had declared the file safe.
2. **`RULES.md`** — three rules added recently (1a, 3a, 10a). `lessons/0004` is *"rules that do
   not compose"*; both composition holes found so far were between a new rule and an old one.
3. **`evals/privacy_gate.py` + `schemas/`** — the claim is that a user's code is
   *unrepresentable* in a run record, not redacted. Three ways to defeat it have been found.
   Try for a fourth.
4. **`evals/check_repo.py`** — five checks assert a rule is still *stated* via regex. Can you
   edit the Markdown so a rule means the opposite while its regex still matches?

## What makes a good report here

The same standard the project applies to itself: **evidence before opinion.** A finding needs
`file:line`, what is wrong, and why it matters. "This could be clearer" is not a finding;
"these two sentences instruct opposite behaviour" is.

Say plainly if a surface is fine. A false positive costs more than a miss here — the whole
argument is that a clean report must mean something.

**Do not send anything from your own codebase.** No paths, no hostnames, no findings from your
own repos. See [`lessons/README.md`](lessons/README.md); this repo shipped a live business's
domains once and it took four passes to clear.
