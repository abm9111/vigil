# Contributing

The most valuable thing you can send is **evidence that VIGIL was wrong**.

That is not a formality. This project's core claim is that an auditing tool should be able to
produce its own evidence — and three of the five defect classes it now catches were found by
outside reviewers, not by its own 19 checks. The dashboard in [`LEDGER.md`](LEDGER.md) shows
the automated self-audit missing four of six. A second reader is not redundancy here; it is the
main detection mechanism.

## Send a lesson, not a rule edit

A pull request saying *"VIGIL told me X, here is why X was false"* is evidence. One that edits
a rule is an assertion about evidence — and a maintainer would have to re-derive your reasoning
to trust it.

Read [`lessons/README.md`](lessons/README.md) first. It covers the format, the controlled
vocabulary, and — most importantly — **what must never appear in a lesson**.

### Never send us your work

A lesson is about a *class* of error, not about your codebase. No absolute paths, no real
hostnames, no `.vigil/context.md`, and above all no description of a weakness in a named
system. `L19` catches the mechanical shapes; it cannot read prose, so every lesson is read by
a maintainer before merge.

This repo previously shipped a live business's domains and compliance posture in its own
documentation, through three reviews, and took four sweeps to clear
([`lessons/0006`](lessons/0006-context-file-is-an-attack-map.md)). The policy exists because
the failure is easy, not because it is unlikely.

## Working on the code

```bash
pip install -e ".[dev]"

python3 evals/check_repo.py         # 19 structural checks, <1s, no LLM
pytest tests/ -q                    # every check must be able to fail
mypy && ruff check .                # config lives in pyproject.toml
python3 evals/build_ledger.py       # regenerate LEDGER.md after adding a lesson
```

All of the above runs in CI. None of it needs an API key.

`evals/run_eval.py` is **not** run in CI: it invokes the Claude Code CLI and costs money per
run. Score a saved transcript with `--from-file` if you need to exercise it.

### Two conventions worth knowing

**When a gap gets past the checks, add a check — not just a patch.** The patch fixes one
instance; the check fixes the class. Every check from L7 onward exists because something
slipped past the ones before it, and `tests/test_check_repo.py` asserts that every documented
check has a test proving it can fail.

**Never lower a threshold to make a run pass.** `min_recall` and `max_false_positives` are the
contract; `L12` holds the floors in code so lowering one takes a visible two-file edit. A
failing eval means something regressed or a fixture found a real gap — both are information,
and editing the threshold discards it.

## What gets rejected

- A rule change with no evidence behind it
- A lesson containing anything identifying a real system
- A new check with no test showing it fires
- Widening `acceptable_extra` without verifying each entry against the fixture — this has
  happened once and is recorded in `evals/expected/data-export-pipeline.json`

## Publishing

`L21` blocks unfilled placeholders — `OWNER/REPO`, `<this-repo>` — but only once a git remote
exists. While the repo is local the URL is genuinely unknown and a placeholder is correct;
adding a remote is the moment it becomes wrong. So the first `git remote add` will turn the
self-audit red until the real URL is filled in, in:

- `README.md` — the clone command
- `CHANGELOG.md` — the release link
- `.github/ISSUE_TEMPLATE/config.yml` — the security-advisory and lessons links

`LICENSE` is deliberately exempt. Its appendix carries `[yyyy]` and `[name of copyright
owner]` as part of the canonical Apache-2.0 text; filling those in would stop it being the
licence it claims to be. Attribution lives in `NOTICE`.

## Scope

VIGIL is deliberately not a scanner. It orchestrates tools you already have and reasons across
their output. Proposals to vendor a scanner, add a runtime dependency, or make it a service are
out of scope. Proposals that make a cluster's evidence *real* — see **D1** in
[`docs/OPEN-DESIGN.md`](docs/OPEN-DESIGN.md) — are the most useful direction right now.

## Licence

Contributions are accepted under Apache-2.0. "VIGIL" is a name, not part of the licence grant;
forks should pick a different one.
