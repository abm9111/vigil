# VIGIL — Flags Reference

## Syntax

```
/vigil [mode] [--flag value] [target]
```

All flags are optional. Flags can be combined freely.

## Flag Definitions

### `--fix`
**Effect:** Auto-fix all fixable issues, then re-validate.
**Default:** Off (report only)
**Behavior:**
1. Run normal audit
2. For each fixable finding, apply the fix (ruff --fix, eslint --fix, prettier --write, etc.)
3. Re-run affected tool to verify fix
4. Report: "Fixed N issues. M remaining (manual fix required)."
**Interaction:** Compatible with all modes. In `--ci` mode, fixes are applied before exit code is computed.
**Engine:** [engines/fix-engine.md](engines/fix-engine.md)

### `--ci`
**Effect:** Machine-readable output, deterministic exit codes.
**Default:** Off (human-readable terminal output)
**Exit codes:**
- `0` — Nothing at or above the blocking severity (or all fixed) **and** no cluster is N/E
- `1` — CRITICAL or HIGH findings present
- `2` — Tool execution error, **or an applicable cluster had no evidence (N/E)**

The *blocking severity* is HIGH, or MEDIUM under `--strict`. It is not the `--threshold` flag,
which only filters what is printed and never moves this gate.

A green pipeline must never mean "the scanner was missing." See
[engines/ci-adapter.md](engines/ci-adapter.md) for the full evidence-gating rule.
**Output:** SARIF by default, or `--format json` for plain JSON. The artifact also carries a
`scope` block (audited / N/A / N/E / out of scope) and, when non-empty, a `suppressions` array.
Without them, `--only security` and a full clean audit are the same green badge, and a committed
`.vigil/ignore` is recorded nowhere. Exiting 0 with suppressions active additionally warns on
stderr.
**Interaction:** Suppresses color, progress bars, and narrative commentary — never the `scope`
block or the `suppressions` array. The earlier wording, "suppresses AI commentary, findings
only", read as licence to drop the ledger along with the prose.
**Engine:** [engines/ci-adapter.md](engines/ci-adapter.md)

### `--strict`
**Effect:** Treat all MEDIUM+ as blocking (normally only CRITICAL/HIGH block).
**Default:** Off
**Behavior:** Lowers the "fail" threshold from HIGH to MEDIUM. In `--ci` mode, exit 1 on MEDIUM+.
**Interaction:** Stacks with `--ci`. Ignored in `scan` mode (scan is always lenient).

### `--only <cluster>`
**Effect:** Audit a single cluster only.
**Values:** `security`, `code-health`, `api`, `data`, `infra`, `frontend`, `performance`, `compliance`, `ai-ml`, `egress`, `blockchain`
**Default:** All applicable clusters
**Behavior:** Loads only the specified cluster file. Scoring uses only that cluster (100-point scale).
**Interaction:** Disables correlation engine (needs multiple clusters). Multiple `--only` allowed: `--only security --only api`.
**In `--ci`:** the narrowed scope must be emitted in the artifact's `scope` block. A pipeline
badge reads nothing but the exit code, so an unrecorded `--only` turns "we looked at one
cluster" into the same green as a full pass.

### `--ignore <pattern>`
**Effect:** Suppress findings matching pattern.
**Values:** Finding IDs (`VIGIL-SEC-001`), glob patterns (`VIGIL-SEC-*`), severity (`--ignore LOW`)
**Default:** None
**Behavior:** A matching finding is **still reported, at its mechanically-derived severity**.
Suppression changes only its *scoring status* — it stops holding the severity floor down. It is
never hidden, never downgraded, and never removed from its cluster listing. `engines/scoring.md`
is the authority. This entry once described the opposite behaviour, contradicting both that
file and the Ledger line three rows below it — see `lessons/0014`.
**Interaction:** Applied after correlation (so ignoring a constituent doesn't break correlated findings).
**Persistence:** `.vigil/ignore`, where **every entry carries an owner and an expiry**. An entry
with neither is not a suppression — ignore it and keep the cap.
**Ledger:** every suppressed finding is listed beside the grade with the authority that
suppressed it, and under `--ci` it must appear in the artifact's `suppressions` array — see
[engines/scoring.md](engines/scoring.md) and [engines/ci-adapter.md](engines/ci-adapter.md).

### `--format <fmt>`
**Effect:** Output format.
**Values:**
- `terminal` — colored, human-readable (default)
- `json` — structured JSON (finding objects)
- `sarif` — SARIF 2.1.0 (GitHub/Azure compatible)
- `markdown` — Markdown table (for PRs/docs)
**Default:** `terminal` (or `sarif` if `--ci`)
**Interaction:** `--ci` overrides to `sarif` unless explicitly set.

### `--baseline <path>`
**Effect:** Compare against a saved baseline file.
**Values:** Path to `.vigil/baseline.json` (default) or custom path
**Default:** Auto-detect `.vigil/baseline.json` in project root
**Behavior:** Computes delta: new findings, fixed findings, regressions. Adds trend indicators to output.
**Interaction:** Required for `watch` and `compare` modes. Optional for others.

### `--compliance <std>`
**Effect:** Map findings to compliance standard controls.
**Values:** `soc2`, `iso27001`, `owasp`, `ai-provenance` (comma-separated for multiple)
**Default:** None
**Behavior:** Each finding gets tagged with applicable controls (e.g., `SOC2:CC6.1`, `OWASP:A01`).
**Interaction:** Adds compliance summary section to output. Full maps in [compliance-maps/](compliance-maps/).

### `--threshold <severity>`
**Effect:** Display filter — only *print* findings at or above this severity.
**Values:** `critical`, `high`, `medium`, `low`, `info`
**Default:** `low` (report everything except INFO in scan, everything in audit/siege)
**Interaction:** Affects output only, not scoring (all findings count toward score).
**Not the CI gate:** "threshold" here means this display filter. The severity that decides a
`--ci` exit 1 is the blocking severity, moved only by `--strict`. `--threshold critical` hides
HIGH findings from the printout and still exits 1 — the two senses are unrelated.

### `--target <path>`
**Effect:** Audit specific file or directory (instead of project root).
**Values:** File path, directory path, or glob pattern
**Default:** Current working directory (project root)
**Behavior:** Restricts all tool execution to the target path.

## Flag Combinations

| Use Case | Command |
|----------|---------|
| Quick security check | `/vigil scan --only security` |
| Pre-commit gate | `/vigil watch --ci --fix` |
| Full audit with fixes | `/vigil audit --fix` |
| PR review | `/vigil compare --baseline .vigil/baseline.json` |
| SOC2 prep | `/vigil audit --compliance soc2 --format markdown` |
| CI pipeline | `/vigil watch --ci --strict --fix` |
| Single file deep-dive | `/vigil audit --target src/auth.py --only security` |
| Adversarial review | `/vigil siege --compliance owasp,soc2` |

## `.vigil/ignore` File

Persistent suppressions, one per line, each as `pattern | owner | expiry`:

```
# pattern            | owner     | expiry (YYYY-MM-DD)
VIGIL-CODE-012       | platform  | 2026-09-30
VIGIL-PERF-*:LOW     | perf-wg   | 2026-12-31
file:scripts/seed.py | data-eng  | 2026-10-15
```

**An entry missing an owner or an expiry is not a suppression.** Ignore it, keep the cap, and
say in the report that it was ignored and why. This file lives inside the audited repository,
so the audited party authors its own suppressions — that is only workable because every one
names a person and a date. A bare pattern is anonymous and open-ended, which is the audited
party grading itself (`engines/scoring.md`, "Suppression changes scoring status, never the
finding").

**Expired entries revert automatically** and re-apply the cap. An expiry in the past is not a
suppression either.

Suppressed findings still appear in the report and in the `--ci` artifact's `suppressions`
array, with the owner and expiry that authorised them.
