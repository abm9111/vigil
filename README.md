# VIGIL

A codebase auditing skill for [Claude Code](https://claude.com/claude-code). It runs the
deterministic tools your stack already has, correlates what they find across domains, and
scores the result — under rules designed so the grade cannot quietly contradict the findings.

Most of VIGIL is instructional Markdown that an LLM reads and follows. Two Python harnesses
under `evals/` keep it honest.

```
/vigil                 # full audit (default)
/vigil scan            # 30s triage sweep
/vigil watch --ci      # diff-only CI gate
/vigil siege           # adversarial, exhaustive
```

## What makes it different

Three ideas, each of which exists because the obvious design fails in a specific way:

**Severity floors.** A weighted average buries a serious finding in a low-weight cluster. A
HIGH in Compliance (6%) moves the overall by less than a point — so a broken deliverable can
score A. The grade is now capped by the worst unresolved finding: any CRITICAL caps at 59, any
HIGH at 79. The cap is always shown, never silent.

**N/E — "no evidence", distinct from N/A.** A cluster whose scanners never ran is not clean;
it is unexamined. N/A means *does not apply* and is removed from weighting. N/E means *applies,
could not look* — it blocks any pass verdict and exits 2 in CI. A green pipeline must never
mean "the scanner was missing."

**Non-adversarial correlation.** Seven of the ten correlation patterns assume an attacker. Three
do not, because plenty of real damage needs no adversary — someone acting in good faith on an
artifact that quietly lied:

| Pattern | Fires on |
|---|---|
| `TRUST_LAUNDERING` | Machine-generated content presented as authoritative, crossing a boundary |
| `DESTRUCTIVE_BEFORE_VALIDATE` | An irreversible step ordered before the check that would abort it |
| `INTEGRITY_THEATER` | A checksum, manifest or audit log that cannot actually fail |

## Install

Copy or symlink into your Claude Code skills directory:

```bash
curl -fsSL https://raw.githubusercontent.com/abm9111/vigil/main/install.sh | bash

# or, if you would rather read the script first — which for an auditing tool you should:
git clone https://github.com/abm9111/vigil.git ~/.claude/skills/vigil
```

Then `/vigil` in any project. Tool discovery is automatic — see `engines/preflight.md` for the
manifest and install commands for each scanner.

## Layout

| Path | What |
|---|---|
| `SKILL.md` | Router — which files load in which mode |
| `RULES.md` | Iron rules: evidence before opinion, severity definitions, no false positives |
| `clusters/` | Per-domain checks. Each declares a weight and an ID prefix |
| `engines/` | Scoring, correlation, preflight, CI adapter |
| `modes/` | scan · audit · siege · watch · score · compare |
| `compliance-maps/` | SOC 2, ISO 27001, OWASP, AI-transparency mappings |
| `evals/` | Self-audit and fixture measurement — see below |
| `tests/` | Proof that every self-audit check can fail |
| `lessons/` | Ledger of times VIGIL was wrong → [`LEDGER.md`](LEDGER.md) |

## Keeping it honest

A tool that audits other people's evidence should produce its own.

```bash
python3 evals/check_repo.py     # 33 structural checks, <1s, no LLM
python3 evals/check_loadable.py # the skill is actually discoverable
pytest tests/ -q               # every check must be able to FAIL
python3 evals/run_eval.py      # recall / false positives against fixtures
```

`tests/` exists because "negative-tested" is only durable if a machine re-checks it. Each test
copies the repo, breaks exactly one invariant, and asserts the matching check fires — and one
test asserts that *every* documented check has such a test, so adding a check without one is
itself a failure.

`check_repo.py` exists because internal inconsistency in a prose-driven skill is a *functional*
bug: two auditors reading the same rules would compute different scores. Every check was added
after a real gap got past the previous ones — dead links, orphaned clusters, a weight table that
disagreed with itself, compliance citations pointing at nothing, a downgrade rule fenced in one
file and unfenced in another.

`run_eval.py` measures recall against seeded defects in `evals/fixtures/`. **Read
`evals/README.md` before quoting any number from it.** It is a smoke regression over six defects
in two fixtures against one model — it detects that something broke. It does not establish that
VIGIL "catches production defect classes." The `clean-control` fixture, which seeds *zero*
defects so any finding is unearned, is the strongest instrument in the suite.

Recorded runs live in `evals/results/`, including the harness bugs and fixture defects each run
exposed. Those write-ups are more useful than the scores.

## The ledger

[**LEDGER.md**](LEDGER.md) is the dashboard: who surfaced which classes of defect,
what now catches each one, and — the useful half — what *failed* to catch them.

[`lessons/`](lessons/README.md) records times VIGIL — or its own self-audit — was **wrong**:
what was believed, who caught it, what *failed* to catch it, and what now prevents a repeat.

It is the skill's durable memory. A new session inherits the reasoning, not just the checks.
`L17` enforces it: a lesson claiming to be mechanized must name a check that exists, and one
still open must be tracked in `docs/OPEN-DESIGN.md`.

**Nothing here self-applies.** Recording a lesson and mechanising it are two separately
reviewed acts, and a human commits both. An auditing tool that rewrites its own standards is
grading its own homework — `lessons/0003` is what that looks like when it happens.

If you find VIGIL wrong, *that* is the contribution. A pull request saying "VIGIL told me X,
here is why X was false" is evidence; one that edits a rule is an assertion about evidence.

**But never send us your work.** A lesson is about a *class* of error — not your paths, hosts,
architecture, or `.vigil/context.md`, which is designed to enumerate your critical paths and
would be an attack map with your name on it. `L19` scans for the mechanical shapes; it cannot
read prose, so a maintainer reads every lesson before merge. Full guidance in
[`lessons/README.md`](lessons/README.md).

## What is not finished

[`docs/OPEN-DESIGN.md`](docs/OPEN-DESIGN.md) lists the open design work — items needing a
decision rather than an edit, each with the argument already made so the next pass starts from
it. The largest: most clusters still have no probe that can fail, so most of the weighted
average is unevidenced by construction.

## Status

Experimental. Use it as an auditing assistant with a self-checking harness, not as a graded
authority — and treat a *failing* run as more informative than a passing one.

## Licence

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). "VIGIL" is not licensed with the code;
forks should pick a different name.
