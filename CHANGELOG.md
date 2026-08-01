# Changelog

Notable changes. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
versions are not yet semantic — this is pre-1.0 and the audit output format may change.

## [0.5.0] — 2026-08-01

The release where the project got measured by people who did not write it, and lost.

### Added
- **One-line installer** (`install.sh`) that *verifies* rather than announcing success: it runs
  `check_loadable.py` and exits non-zero if the skill is undiscoverable. Wrapped in `main()`
  so a truncated download cannot execute a half-script.
- **Rule 1a — a scanner hit is a pointer to a question, not an answer** (`L32`). Tool output
  locates something to investigate; treating it as a settled finding is how a scanner's false
  positive becomes an auditor's HIGH.
- **Rule 3a — a control's presence is not its efficacy** (`L31`). A control may only reduce
  severity on demonstrated effect, and never below a floor Rule 7 fences.
- **Rule 10a — every report names the tree it audited** (`L33`). The same repository returned
  32, 1 and 0 secret findings depending on whether the working tree, history or tracked tree
  was scanned. All three were correct; only one answered the question the report claimed to be
  answering (`lessons/0010`).
- **Preflight resolves tools inside the subject's environment** (`L30`), not the auditor's.
- **`corpus/`** — the first contributed bundle, from a real run against code this project did
  not write, alongside `proof/0003`.
- **`REVIEWING.md`** — what is closed, what is deliberately open, ranked by risk, for people
  reading this adversarially.
- **`docs/BASELINE.md`** and `scripts/run-baseline.sh` — the with/without-VIGIL comparison,
  with every guard's reason written down, because the obvious version of each one produced a
  confident wrong number.
- **`L34`** — the Makefile gate and the CI workflow must run the same commands in the same
  environment.
- **Code of conduct**, self-audit badge, GitHub Discussions.

### Changed
- The run-record schema was **rebuilt against the first real record**, having failed it on
  100+ counts. A schema written before seeing one real instance passes every self-test and
  fails on first contact (`lessons/0007`).
- The baseline harness split into `--arm control` / `--arm vigil` / `--compare`. One process
  meant isolating the control isolated everything: both arms ran without the skill, the
  treatment arm scored 0%, and the harness reported *"VIGIL beat the control on 0/2 fixtures."*
- Commercial and comparison material removed from the skill's documentation (**D2**).

### Fixed
- **Eight defects found by two cross-model reviews, of which the 33 checks and 160 tests found
  zero.** Grok: rule-composition holes where Rule 1a let a finding be dropped more cheaply
  than Rule 3a let one be reduced, plus four prose checks whose regexes matched their own
  inverted text. Kimi: the privacy gate **failing open three ways** — an unanchored `pattern`
  under `re.search`, an empty `{}` schema constraining nothing, and `$ref` resolving only one
  step — and an installer `git reset --hard` destroying uncommitted work. Full record in
  `evals/results/2026-08-01-cross-model-review.md`.
- The control-arm guard probed the paid CLI before its own free filesystem check, so CI was red
  for three commits while `make check` was green (`lessons/0011`). `make test` now runs with
  CI's `PATH`.
- `L21` no longer flags documentation that *names* a placeholder as one that *uses* it.

### Known limitations
- **D5 — whether VIGIL beats a competent bare prompt is still unanswered.** Not for lack of
  tooling: the same arm, on the same fixture, with identical code, returned **0% and 83%
  recall** on consecutive draws. The harness's variance exceeds the effect it measures, so
  every single-run number here — including the enforced `min_recall: 0.8` — is a draw from a
  distribution. Needs `--runs 5` minimum and fixtures this project did not write.
- **D1 — 5 of 11 clusters carry scoring weight while requiring no tool**, so much of the
  weighted average is unevidenced by construction. Read `docs/OPEN-DESIGN.md` before relying
  on a VIGIL score.

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
- **Multi-contributor corpus** — `corpus/`, `schemas/bundle.schema.json` and
  `learn.py --corpus`. Rates are computed per contributor and then contributors are counted, so
  one heavy submitter cannot outvote nine others; a signal needs 3+ contributors and 60%
  agreement. `docs/FIELD-LOOP.md` walks the whole loop at ten users, including the four places
  it is deliberately allowed to stop.
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

[0.5.0]: https://github.com/abm9111/vigil/releases/tag/v0.5.0
<!-- 0.4.0 predates tagging and points at its final commit. A tag placed there retroactively
     would run today's gate against a tree that was correctly not yet publish-ready. -->
[0.4.0]: https://github.com/abm9111/vigil/commit/3bbe3a88a6fccfdd618678e385a3f0cda63b8514
