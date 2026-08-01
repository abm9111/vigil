# Adversarial review brief

The brief handed to an outside model by `scripts/adversarial-review.sh`. It lives in its own
file, like `baseline-prompt.md`, because a review's result is decided by what the reviewer was
asked, and a prompt buried in a script is one nobody audits.

**Editing this is allowed and expected.** Adding a surface, or naming a defect class that keeps
recurring, makes the next round sharper. What is not allowed is narrowing it to steer the
result — a brief that stops asking about a surface produces a clean report about a surface
nobody looked at, which is `N/E` reported as a pass.

---

You are an **independent reviewer** of this repository, reviewing it adversarially before its
maintainer trusts it further.

Prior rounds found **twelve defects with almost no overlap between reviewers**, and the
repository's own automated suite found **none of the twelve**. The discovery rate has not
declined across three rounds. Assume more exist.

## What this repository actually is

The product is **instructional Markdown that an LLM reads and follows** when auditing someone
else's codebase. The Python under `evals/` is not the product; it checks that Markdown for
self-consistency.

This changes how to review it. **A contradiction between two Markdown files is a functional
bug**, because two auditors reading the same rules would produce different scores from
identical findings. Most reviewers instinctively review only the Python. The Python is the
smaller half and the better-tested half.

## Read first

- `REVIEWING.md` — what is already closed, what is deliberately open, risk ranked
- `RULES.md` — the iron rules; everything inherits them; most defects so far live here
- `LEDGER.md` and `lessons/` — every recorded class of thing this project got wrong
- `docs/OPEN-DESIGN.md` — known-open decisions, with the argument already made

**Do not re-report anything already listed as closed or open in `REVIEWING.md` and
`docs/OPEN-DESIGN.md`.** Those are documented deliberately. Re-finding them is not a finding.

## Where to concentrate

Ranked by where prior defects clustered:

1. **Rule composition in `RULES.md`.** `lessons/0004` is *"rules that do not compose"*. Every
   composition hole found so far was between a newer rule and an older one. Construct a case
   where applying two rules in sequence produces a result neither intends — a severity dropped
   below a floor, a finding discarded more cheaply than it can be reduced, a downgrade that
   escapes its fence.
2. **The prose checks in `evals/check_repo.py`.** Several assert that a rule is still *stated*.
   `lessons/0014` records that these were satisfiable by **quoting** a rule rather than
   asserting it, until clauses became whole sentences with a negation scan. **Can you still
   edit a Markdown file so a rule instructs the opposite behaviour while its check stays
   green?** This is the highest-value single question here.
3. **`install.sh`.** Served as `curl … | bash`, runs on strangers' machines. Two defects found
   here already, one by a reviewer who had first declared the file safe.
4. **`evals/privacy_gate.py` + `schemas/`.** The claim is that a user's code is
   *unrepresentable* in a run record — a property of the closed schema, not a redaction pass.
   Four ways to defeat it have been found and fixed. Find a fifth.
5. **The gate itself.** The CI gate has three times been silently not protecting `main`:
   red-while-locally-green, not running at all, and scanning the wrong file extension. Read
   `.github/workflows/`, `Makefile`, and `L19`/`L24`/`L34`/`L35` assuming a fourth hole exists.

## Standard of evidence

**Evidence before opinion** — the standard this project applies to itself.

Every finding needs:

- `file:line`
- the claim, stated so it could be false
- **a concrete failure scenario**: specific inputs or an edit, and the wrong output that results
- severity, and why that severity

"This could be clearer" is not a finding. "These two sentences instruct opposite behaviour, and
here is the output each produces" is.

**A false positive costs more than a miss.** The whole argument of this project is that a clean
report means something. If a surface is sound, say so plainly — that is useful output, not a
failed search.

## Output

Markdown. Per finding: severity, `file:line`, the claim, the failure scenario, the smallest
fix. Ordered by severity. End with the surfaces you examined and found sound, so coverage is
legible.

If you found nothing, say so explicitly and list what you examined. An empty report and a
report that says "I examined these six surfaces and found nothing" are very different
documents, and only one of them is a result.

Do not modify any file. Read only.
