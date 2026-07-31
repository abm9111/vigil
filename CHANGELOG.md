# Changelog

Notable changes. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions are not yet semantic — this is pre-1.0 and the audit output format may change.

## [0.4.0] — 2026-07-31

The release where the project started producing its own evidence.

### Added
- **Severity floors** — the overall grade is capped by the worst unresolved finding, so a
  number can no longer contradict the findings it summarises.
- **N/E ("no evidence")**, distinct from N/A. A cluster whose scanners never ran blocks any
  pass verdict and exits 2 in CI; a green pipeline cannot mean "the scanner was missing".
- **Correlation patterns 8-10** — `TRUST_LAUNDERING`, `DESTRUCTIVE_BEFORE_VALIDATE`,
  `INTEGRITY_THEATER`. Non-adversarial: no attacker required.
- **Data Egress & Provenance cluster** — exports, PII in files rather than schemas,
  AI-content labelling, reproducible builds.
- **`evals/check_repo.py`** — 26 structural self-checks, each with a test proving it fails.
- **Field learning loop** — `engines/telemetry.md` plus `schemas/run-record.schema.json`,
  `evals/privacy_gate.py` and `evals/learn.py`. Run records are content-free *by construction*
  (closed schema, every string an enum) and never leave the machine without an explicit human
  act. `proof/` records what VIGIL found on real codebases, the counterpart to `lessons/`.
- **`lessons/`** — a ledger of times VIGIL was wrong, with `LEDGER.md` generated from it.
- **`tests/`** — pytest suite; every check must be demonstrably able to fail.
- Apache-2.0 `LICENSE` + `NOTICE`, `SECURITY.md`, `CONTRIBUTING.md`, CI, issue/PR templates.

### Fixed
- Correlation could *raise* the overall score by deleting findings from their clusters, and
  again through the severity-floor channel via CVE reachability downgrades.
- `scan` mode reported "PRODUCTION READY" from a two-cluster, 30-second sweep.
- `Auth & Access` carried 14% of the weight table with no cluster file and no mechanics, so
  two auditors could compute different scores from identical findings.
- The context subsystem instructed machinery that did not exist (four dead references).
- Six eval-harness bugs, each producing a confidently wrong number in one direction or the
  other. Recorded in `evals/results/` and `lessons/0005`.
- EU AI Act Art. 50(4) was misapplied in the compliance map; corrected against the primary
  source and the scope limits documented.

### Security
- Removed a live business's domains, compliance posture and architecture from the skill's own
  documentation (`lessons/0006`). `L19` now scans contributed material for paths, hosts,
  emails and key-shaped strings.

[0.4.0]: https://github.com/OWNER/REPO/releases/tag/v0.4.0
