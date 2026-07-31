# VIGIL Engine: Preflight

**Runs BEFORE any cluster.** Establishes what evidence this machine can actually produce, so
the report never claims coverage it does not have.

## Why this exists

`engines/semgrep-orchestrator.md` describes a semgrep + CodeQL pipeline. On a machine where
semgrep is not installed, an audit ran to completion, scored Security 96/100, and never
mentioned that its primary SAST tool had not executed. The score was arithmetically correct
and epistemically false.

Rule 1 demands evidence before opinion. Preflight is where VIGIL finds out how much evidence
it is going to get, and tells the user before spending their time.

## Procedure

1. **Detect stack** — manifest files present (`package.json`, `pyproject.toml`,
   `requirements.txt`, `Cargo.toml`, `go.mod`, `Dockerfile`, `*.sol`, `*.tf`).
2. **Select clusters** — per stack. Clusters that do not apply are marked **N/A**.
3. **Probe tools** — for each applicable cluster, check every required and optional tool.
4. **Compute ceilings** — per [engines/scoring.md](scoring.md) evidence-coverage table.
5. **Emit the capability report** — always, in every mode including `--ci`.
6. **Fail closed** — if a cluster has zero required tools available, mark it **N/E** and
   suppress any pass verdict for the whole audit.

Probe with the tool's own version flag, never with `which` alone — a shim on PATH that errors
on invocation is worse than an absent binary:

```bash
# `git` is on the list because the egress cluster requires it. Ubiquitous tools are the ones
# that get assumed rather than probed, and an assumed tool cannot be reported as missing.
for t in git ruff mypy bandit pip-audit semgrep gitleaks trufflehog detect-secrets \
         eslint tsc hadolint trivy slither aderyn; do
  printf '%-16s ' "$t"
  command -v "$t" >/dev/null 2>&1 && { "$t" --version 2>&1 | head -1; } || echo "MISSING"
done
```

## Tool Manifest

**Required** means the cluster cannot be evidenced without it. **Optional** means it deepens
coverage but its absence does not blind the cluster.

### Python

| Tool | Cluster | Req | Covers | Install |
|------|---------|-----|--------|---------|
| `ruff` | code-health | ✔ | Lint, dead code, bugbear, security subset (`S`) | `uv tool install ruff` |
| `mypy` | code-health | ✔ | Type correctness | `uv tool install mypy` |
| `bandit` | security | ✔ | Python-specific vuln patterns | `uv tool install bandit` |
| `pip-audit` | security | ✔ | Dependency CVEs | `uv tool install pip-audit` |
| `semgrep` | security | — | Cross-language taint + custom rules | `brew install semgrep` |

### JavaScript / TypeScript

| Tool | Cluster | Req | Covers | Install |
|------|---------|-----|--------|---------|
| `eslint` | code-health | ✔ | Lint, react-hooks, a11y | `npm i -D eslint` |
| `tsc` | code-health | ✔ | Type correctness | `npm i -D typescript` |
| `npm audit` | security | ✔ | Dependency CVEs | ships with npm |
| `semgrep` | security | — | Taint analysis | `brew install semgrep` |

### Secrets — cluster `security`, all three optional individually, **at least one required**

| Tool | Covers | Install |
|------|--------|---------|
| `gitleaks` | Working tree + full git history | `brew install gitleaks` |
| `trufflehog` | Verified live credentials | `brew install trufflehog` |
| `detect-secrets` | Entropy + baseline workflow | `uv tool install detect-secrets` |

History matters: a secret removed from HEAD but alive in git history is still exposed. Prefer
`gitleaks` for the history sweep; note in the report if only working-tree scanning ran.

### Infrastructure / Containers

| Tool | Cluster | Req | Covers | Install |
|------|---------|-----|--------|---------|
| `hadolint` | infra | ✔ | Dockerfile correctness, root user | `brew install hadolint` |
| `trivy` | infra | ✔ | Image + IaC CVEs, misconfig | `brew install trivy` |

### Smart contracts

| Tool | Cluster | Req | Covers | Install |
|------|---------|-----|--------|---------|
| `slither` | blockchain | ✔ | Solidity static analysis | `uv tool install slither-analyzer` |
| `aderyn` | blockchain | — | Rust-based Solidity linter | `cargo install aderyn` |
| `echidna` | blockchain | — | Property fuzzing | `brew install echidna` |

### Data egress & provenance

Needs no third-party binaries — its checks are shell, `git`, and byte inspection. That is
**not** the same as being exempt from the probe-must-fail rule below, and an earlier version of
this section wrongly implied it was ("can never be N/E").

Its probe is the check suite itself, and it can fail: `git` absent or the target not a
repository makes `git check-ignore` unusable, so the egress questions about what is committable
cannot be answered. Required: `git`. When it is missing, this cluster degrades like any other.

## Capability Report

Emit before findings, in every mode:

```
━━━ Preflight ━━━
Stack     : Python 3.14 (pandas, pyarrow) · no JS · no Docker · no contracts
Clusters  : 6 applicable · 4 N/A (api, frontend, blockchain, ai-ml)

Tools     ruff 0.15.10 ✓    mypy 2.1.0 ✓     bandit 1.9.4 ✓
          pip-audit 2.9.0 ✓ gitleaks 8.30.1 ✓ detect-secrets 1.5.47 ✓
          semgrep ✗ MISSING (optional: security) → brew install semgrep

Coverage  security     4/4 required ✓  + 1 optional missing   ceiling 100
          code-health  2/2 required ✓                          ceiling 100
          egress       1/1 required ✓ (git)                    ceiling 100
```

When a required tool is missing, say what it costs:

```
Tools     bandit ✗ MISSING (required: security) → uv tool install bandit
Coverage  security     3/4 required            ceiling 85  ⚠ partial evidence
          → Python-specific vuln patterns were NOT examined.
```

When a cluster loses all required tools:

```
Coverage  security     0/4 required            N/E  ⛔ no evidence
          → Audit is INCOMPLETE. No pass verdict will be issued.
```

## A tool must resolve inside the subject's environment

Probing that a binary *runs* is not probing that it can *see the subject*. `lessons/0007`
records a type checker that ran, exited 0 and reported a codebase clean while being unable to
import a single one of that codebase's dependencies. The project's own CI, running the same
tool from inside the project environment, found 6 errors in 4 files.

This is worse than a missing tool in one specific way: **a missing tool is loud and a
misresolved one is silent, and the silent failure points at clean.** Preflight exists to stop
VIGIL claiming coverage it does not have, so a failure mode that manufactures coverage is
aimed directly at it.

**Resolve, then compare.** Record the absolute path of every tool and whether it lies inside
the subject's environment:

```bash
# Python — does the tool the shell finds match the one the project's interpreter sees?
command -v mypy
python -c 'import mypy, pathlib; print(pathlib.Path(mypy.__file__).parent)' 2>/dev/null \
  || echo "the project interpreter cannot import mypy at all"

# JavaScript — a global eslint reads none of the project's plugin resolution
ls node_modules/.bin/eslint 2>/dev/null || echo "no project-local eslint"
```

**Prefer the project-local invocation and record which you used:** `python -m mypy` over bare
`mypy`, `./node_modules/.bin/eslint` or `npx --no-install eslint` over a global `eslint`. Where
the project ships its own runner — `uv run`, `poetry run`, `npm run lint`, a `Makefile` target —
that runner *is* the correct invocation, and the CI workflow is where to find it. `lessons/0007`
was found by CI disagreeing with a local run; reading the workflow first would have found it
sooner.

**The trap that makes this fail clean.** Analyzers that accept an "ignore unresolvable imports"
setting — `mypy`'s `ignore_missing_imports`, a linter with unresolved-module suppression — do
not error when the environment is wrong. They degrade every affected value to a permissive type
and pass. So the absence of errors is evidence of nothing until imports are known to resolve:

> If the analyzer cannot import the subject's dependencies, its clean result is **not
> evidence**. Treat that cluster's type-safety portion as **N/E**, not as scored.

**Rule 6 below makes the consequence binding.**

## A probe must be able to fail

The sharpest test for whether a cluster's evidence is real: **could the probe ever report
failure?** "grep is installed" cannot fail, so it converts "probed nothing meaningful" into
ceiling 100 — the N/E vocabulary wrapped around the old lie.

For clusters whose checks are mostly `grep` rather than a named binary, one of two options is
honest, and nothing else is:

1. **Name a discriminating tool as required** and accept N/E when it is absent —
   `go vet`, `cargo clippy`, an OpenAPI validator, `sqlfluff`.
2. **Formalise the check suite as the probe** — versioned, enumerated, with a per-check
   execution ledger ("these N named checks each executed"), recorded in the baseline alongside
   tool versions. A suite that is merely *described* is not a probe.

The larger hole today is not the 85 ceiling: it is that most clusters declare **no required
tools at all**, so most of the weighted average is unevidenced by construction. Until every
applicable cluster has a probe that can fail, treat a high overall score as an upper bound
rather than a measurement.

## Rules

1. **Never skip silently.** A tool that did not run appears in the report with its install
   command. Rule 8 already required this; preflight is the mechanism that makes it happen.
2. **Never substitute reasoning for a missing tool.** If `bandit` is absent, do not "reason
   about" Python vulns and report them at tool confidence. Reason freely, but mark such
   findings `NEEDS_REVIEW` and leave the cluster at its reduced ceiling.
3. **A tool that errors counts as missing.** Report the stderr. A crashed scanner is not a
   clean scan.
4. **Version-pin what you can.** Record tool versions in `.vigil/baseline.json`. A score that
   moved because a linter added a rule is not a regression in the code, and trend tracking
   that cannot tell the difference is noise.
5. **Preflight output is part of the deliverable.** When the audit is handed to someone else,
   the coverage ledger travels with the findings — otherwise they inherit a number without
   knowing what it was based on.
6. **A tool resolved outside the subject's environment cannot contribute to a ceiling of 100.**
   Record the resolved path beside the version in the capability report and in
   `.vigil/baseline.json`. Treat the reduction exactly as a missing tool is treated — because
   epistemically it is one: the run produced output about a project it could not fully see.
   Never treat "it exited 0" as coverage without knowing what it was able to read
   (`lessons/0007`).
