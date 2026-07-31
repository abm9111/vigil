---
name: vigil
description: "Codebase quality and compliance audit. Use when the user says /vigil for scan/audit/score of application code."
---

# /vigil — Vigilant Infrastructure & Governance Intelligence Layer

Trigger: user says `/vigil` followed by optional mode and flags.

```
/vigil [mode] [--flags] [target]
```

## Modes

| Mode | Time | Depth | What it does |
|------|------|-------|--------------|
| `scan` | 30s | Surface | Quick domain scores, critical findings only |
| `audit` | 5-15min | Deep | Full findings + correlation + compliance gaps |
| `siege` | 20-30min | Exhaustive | Adversarial attack scenarios + blast radius |
| `watch` | 15s | Diff-only | New/fixed/regressed since baseline (CI gate) |
| `score` | 30s | Numeric | Single 0-100 score + trend |
| `compare` | 2-5min | Diff | Side-by-side branch/commit comparison |

Default mode if omitted: `audit`

## Companions

| Command | What | Time |
|---------|------|------|
| `/vigil-diff` | Audit only staged/unstaged changes | 30s |
| `/vigil-explain [ID]` | Deep-dive a specific finding | 1min |
| `/vigil-baseline` | Save current state as comparison baseline | 10s |
| `/vigil-bounty [--platform h1\|bc\|immunefi]` | Generate platform-ready bounty submission | 2-5min |
| `/vigil-recon [--target domain] [--depth quick\|standard\|deep]` | Reconnaissance pipeline → VIGIL handoff | 2-15min |
| `/vigil-triage [--budget N_hours]` | Prioritize findings by exploitability & payout | 3-5min |
| `/vigil-track [add\|update\|status\|report]` | Bounty, CVE, engagement & revenue tracking | 10s |

## Execution Router

For ANY `/vigil` invocation:

1. **Read [RULES.md](RULES.md)** — Iron rules for all auditing (always)
2. **Read [FLAGS.md](FLAGS.md)** — Parse user flags
3. **Detect project stack** — scan for package.json, requirements.txt, Cargo.toml, go.mod, Dockerfile, etc.
4. **Load Context (v2)** — Check for `.vigil/context.md`, `vigil-context.md`, `.vigil/context.json`, or `vigil-context.json`. If found, load and apply using [engines/context-loader.md](engines/context-loader.md). This step happens **before** clusters run.
5. **Run preflight** — per [engines/preflight.md](engines/preflight.md). Probe every tool the
   selected clusters require, compute per-cluster evidence ceilings, and emit the capability
   report. A cluster with no available required tools is **N/E**, and an audit containing an
   N/E cluster can never return a pass verdict.
6. **Load mode-specific files:**

| Mode | Load |
|------|------|
| scan | [modes/scan.md](modes/scan.md), [clusters/code-health.md](clusters/code-health.md), [clusters/security.md](clusters/security.md), [engines/preflight.md](engines/preflight.md), [engines/scoring.md](engines/scoring.md) |
| audit | [modes/audit.md](modes/audit.md), ALL [clusters/](clusters/), [engines/preflight.md](engines/preflight.md), [engines/scoring.md](engines/scoring.md), [engines/correlation.md](engines/correlation.md) |
| siege | [modes/siege.md](modes/siege.md), ALL [clusters/](clusters/), ALL [engines/](engines/), ALL [compliance-maps/](compliance-maps/), ALL [domains/](domains/) |
| watch | [modes/watch.md](modes/watch.md), [clusters/code-health.md](clusters/code-health.md), [clusters/security.md](clusters/security.md) |
| score | [modes/score.md](modes/score.md), ALL [clusters/](clusters/), [engines/scoring.md](engines/scoring.md) |
| compare | [modes/compare.md](modes/compare.md), ALL [clusters/](clusters/), [engines/scoring.md](engines/scoring.md) |

7. **Skip N/A clusters** — only load clusters relevant to detected stack. N/A (does not apply)
   and N/E (applies, no tools available) are different states — see [engines/scoring.md](engines/scoring.md).
8. **Run deterministic tools FIRST** — every finding must start with tool output, not opinion
9. **AI reasoning SECOND** — interpret, correlate, prioritize tool output
10. **Score and report** — per [engines/scoring.md](engines/scoring.md). Apply severity floors
    and evidence ceilings; never emit a pass verdict while a cluster is N/E.
11. **Write a run record, then ask** — per [engines/telemetry.md](engines/telemetry.md). One
    content-free JSON file in the audited repo's own `.vigil/runs/`. Local only; **never
    transmitted.** The run is **not finished** until the user has been told the record exists
    and asked whether to share it — default **no**, enter selects no, a non-interactive session
    counts as no, and a decline is never re-asked. Sharing writes a bundle the user attaches to
    a PR themselves; VIGIL has no endpoint.

## Flag Quick Reference

See [FLAGS.md](FLAGS.md) for full details.

| Flag | Effect |
|------|--------|
| `--fix` | Auto-fix fixable issues, re-validate |
| `--ci` | Machine-readable output (SARIF/JSON), exit codes |
| `--strict` | Treat warnings as errors |
| `--only <cluster>` | Audit single cluster (e.g., `--only security`, `--only egress`) |
| `--ignore <id>` | Suppress specific finding IDs |
| `--format <fmt>` | Output format: `terminal` (default), `json`, `sarif`, `markdown` |
| `--baseline <path>` | Compare against saved baseline |
| `--compliance <std>` | Map findings to standard: `soc2`, `iso27001`, `owasp` |

## Cluster Reference

| Cluster | File | Covers |
|---------|------|--------|
| Code Health | [clusters/code-health.md](clusters/code-health.md) | Lint, types, tests, coverage, git hygiene, DX |
| Security | [clusters/security.md](clusters/security.md) | OWASP, secrets, deps, supply chain |
| API & Networking | [clusters/api-and-networking.md](clusters/api-and-networking.md) | REST/GraphQL design, client patterns |
| Data & Persistence | [clusters/data-and-persistence.md](clusters/data-and-persistence.md) | DB, migrations, data integrity |
| Infrastructure & DevOps | [clusters/infrastructure-and-devops.md](clusters/infrastructure-and-devops.md) | Docker, CI/CD, IaC, observability |
| Frontend & Mobile | [clusters/frontend-and-mobile.md](clusters/frontend-and-mobile.md) | React, a11y, i18n, mobile |
| Performance | [clusters/performance.md](clusters/performance.md) | Perf, concurrency, resource usage |
| Compliance & Docs | [clusters/compliance-and-docs.md](clusters/compliance-and-docs.md) | Regulatory, documentation |
| AI & ML | [clusters/ai-and-ml.md](clusters/ai-and-ml.md) | ML pipelines, model drift, bias |
| Blockchain | [clusters/blockchain.md](clusters/blockchain.md) | Solidity, Vyper, Move, smart contracts, DeFi |
| Data Egress & Provenance | [clusters/data-egress-and-provenance.md](clusters/data-egress-and-provenance.md) | Exports, bundles, PII in files, AI-content labelling, reproducibility |

## Skill Integration

| When you need | Use |
|---------------|-----|
| Quick lint/format fix | `/build-guardian` (hooks, <1s) |
| Deep multi-domain audit | `/vigil audit` (this skill) |
| Security config scan | `/security-scan-ecc` (Claude config only) |
| Strategic decision about findings | `/crux analyze` |

## Reference Files

| File | Contents |
|------|----------|
| [RULES.md](RULES.md) | Iron rules, severity definitions, evidence requirements |
| [evals/README.md](evals/README.md) | Fixture-based recall / false-positive measurement + repo self-audit |
| [lessons/README.md](lessons/README.md) | Ledger of times VIGIL was wrong, and what now catches that class |
| [proof/README.md](proof/README.md) | Times VIGIL was right on a real codebase — the other half of the record |
| [FLAGS.md](FLAGS.md) | All flags with defaults and interactions |
| [engines/correlation.md](engines/correlation.md) | 10 cross-domain correlation patterns — 7 adversarial, 3 non-adversarial |
| [engines/preflight.md](engines/preflight.md) | Tool probing, evidence ceilings, capability report (runs first) |
| [engines/scoring.md](engines/scoring.md) | 0-100 weighted scoring + grades, severity floors, N/E |
| [engines/fix-engine.md](engines/fix-engine.md) | Auto-fix + re-validate loop |
| [engines/ci-adapter.md](engines/ci-adapter.md) | SARIF/JSON output + exit codes |
| [engines/semgrep-orchestrator.md](engines/semgrep-orchestrator.md) | Semgrep/CodeQL parallel scanning + SARIF merge |
| [engines/report-generator.md](engines/report-generator.md) | Consulting deliverables (ComplianceSprint, SiegeReport, Retainer) |
| [engines/contract-orchestrator.md](engines/contract-orchestrator.md) | Slither + Aderyn + Echidna smart contract pipeline |
| [engines/tracking.md](engines/tracking.md) | Bounty, CVE, engagement & revenue tracking |
| [engines/context-loader.md](engines/context-loader.md) | Context file discovery, parsing, and application (v2) |
| [engines/telemetry.md](engines/telemetry.md) | Content-free run records — how VIGIL learns from real use without ingesting it |
| [docs/FIELD-LOOP.md](docs/FIELD-LOOP.md) | The full loop with ten contributors, and every place it is allowed to stop |
| [corpus/README.md](corpus/README.md) | Contributed bundles — why rates count contributors, not rows |
| [CONTEXT.md](CONTEXT.md) | Design and usage guide for project context awareness (v2) |
| [compliance-maps/](compliance-maps/) | SOC2, ISO 27001, OWASP 2025 mappings |
| [companions/](companions/) | 7 micro-commands (diff, explain, baseline, bounty, recon, triage, track) |
| [adapters/](adapters/) | Cursor, Copilot, portable adapter configs |
