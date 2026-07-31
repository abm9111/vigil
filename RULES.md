# VIGIL — Iron Rules

These rules apply to ALL modes and ALL clusters. No exceptions.

## Rule 1: Evidence Before Opinion

Every finding MUST cite deterministic evidence. The hierarchy:

1. **Tool output** — ruff, bandit, mypy, eslint, hadolint, trivy, trufflehog, semgrep, npm audit, pip-audit, tsc
2. **File:line reference** — exact location in codebase (`src/api.py:42`)
3. **Pattern match** — grep/glob result showing the problematic code
4. **AI reasoning** — ONLY after tool/file evidence is established

A finding with no tool output and no file reference is **not a finding**. Delete it.

## Rule 2: Severity Definitions

| Severity | Definition | Response |
|----------|-----------|----------|
| CRITICAL | Exploitable in production NOW. Data loss, RCE, auth bypass, secret exposure. | Must fix before deploy. |
| HIGH | Exploitable with moderate effort. Injection, privilege escalation, missing auth on sensitive endpoints. | Fix within sprint. |
| MEDIUM | Defense-in-depth gap. Missing rate limits, verbose errors, weak validation. | Fix within quarter. |
| LOW | Best practice violation. Style, naming, minor optimization. | Fix when touched. |
| INFO | Observation. Not a vulnerability, but noteworthy. | Document only. |

## Rule 3: No False Positives

Before reporting a finding:
1. Verify the code path is reachable
2. Check if mitigations exist elsewhere (middleware, framework defaults, WAF)
3. Check if it's test/dev-only code
4. If uncertain, mark as `NEEDS_REVIEW` not CRITICAL

False positives destroy trust faster than missed findings.

### Rule 3a: A control's presence is not its efficacy

Step 2 above says *check if mitigations exist*. That is necessary and **not sufficient**, and
the gap is not academic: a rate limiter that existed, was wired up, was reachable, and was
credited as a compensating control had never blocked a single request. Five hundred requests,
five hundred allowed, zero blocked (`lessons/0008`).

Rule 3 was *followed*. A control that exists, is wired up, is reachable and is wrong satisfies
step 2 completely — so the rule was the defect, not the audit.

**A mitigation may reduce a finding's severity only on demonstrated efficacy.** The ladder,
strongest first:

| Level | What it means | Reduces severity? |
|---|---|---|
| **Executed** | the control was exercised and observed to block the input class | yes |
| **Tested** | a test in the repo covers this input class against this control and passes | yes |
| **Traced** | the path was followed end to end **including its empty, first-call and error branches** | yes, one step only |
| **Present** | it exists in the code and looks correct | **no** |

**Reading is not running.** In the case above, no amount of careful reading would have helped:
the accumulator was unreachable because the prune branch deleted the counter and returned early
whenever the window was empty — *the state every caller is in on their first request*. The
defect lived in an interaction visible only on the second call. So a trace must cover the
control in its **initial** state, not its steady state; a control examined only mid-flight is
examined in the one state where it works.

**The fence.** Where efficacy cannot be demonstrated, the finding keeps its undiminished
severity and is marked `NEEDS_REVIEW`. Never reduce quietly on the strength of a control you
did not exercise — a severity lowered on an unverified mitigation is indistinguishable in the
report from one lowered on a verified one, and the reader cannot tell which they are holding.

This is Rule 1 applied to the defensive side of the ledger: evidence before opinion, including
when the opinion is reassuring. An unexercised control is an impression, not a catch.

## Rule 4: Deterministic First, AI Second

For each cluster, run deterministic tools BEFORE applying AI reasoning:
- Run the tool command exactly as specified in the cluster file
- Parse the output for findings
- THEN apply AI reasoning to interpret, contextualize, and correlate
- Never skip the tool step and go straight to AI opinion

## Rule 5: Scope Discipline

- Only audit files in the target directory (or git diff for watch/diff modes)
- Never audit node_modules/, .venv/, vendor/, dist/, build/, .git/
- Respect .gitignore unless explicitly told otherwise
- Respect `--only` and `--ignore` flags absolutely

## Rule 6: Finding IDs

Every finding gets a display ID: `VIGIL-{CLUSTER}-{NUMBER}`

Format: `VIGIL-SEC-001`, `VIGIL-CODE-042`, `VIGIL-INFRA-007`

`{NUMBER}` is a position in *this* report, not an identity — fix one finding and everything
after it in that cluster shifts up by one. Anything that must survive across runs (baseline
deltas, `!` regressions, a ticket citing a finding) matches on the identity tuple in Rule 10,
never on this number.

Cluster prefixes:
- `SEC` — Security
- `CODE` — Code Health
- `API` — API & Networking
- `DATA` — Data & Persistence
- `INFRA` — Infrastructure & DevOps
- `FE` — Frontend & Mobile
- `PERF` — Performance
- `COMP` — Compliance & Docs
- `AIML` — AI & ML
- `EGRESS` — Data Egress & Provenance
- `CHAIN` — Blockchain / smart contracts
- `CORR` — Correlated (cross-domain)

## Rule 7: Correlated Findings Replace Constituents

When the correlation engine groups findings into a correlated finding:
- The correlated finding (VIGIL-CORR-xxx) replaces its constituents in the report
- Constituent findings are listed as "contributing factors" under the correlated finding
- Severity of the correlated finding is ALWAYS >= max severity of constituents — with one
  fenced exception, below
- Scoring uses the correlated finding's severity, not the sum of constituents

**The exception: DEPENDENCY_AND_REACHABILITY.** Correlation pattern 5 in
[engines/correlation.md](engines/correlation.md) may assign a severity *below* its constituent
CVE, because reachability is the one correlation that subtracts risk rather than adding it. It
has to be fenced, because the severity floors in [engines/scoring.md](engines/scoring.md) read
the *correlated* severity: absorb a HIGH CVE into a LOW correlation and the 79 cap vanishes
while the penalty drops from 10 points to 1. That is the same exploit as correlation raising a
cluster average by deleting findings, run through the floor instead of the mean.

- A downgrade requires **positive evidence of non-reachability** — the module and the call
  sites searched, named, and found absent. "No call was found" is not evidence of absence; an
  unsearched path is NEEDS_REVIEW at the CVE's own severity.
- A downgrade moves the penalty and the fix priority. It does **not** move the severity floor:
  the cap is computed from the constituent CVE's severity. Reachability may reorder the work;
  it may not turn an unresolved HIGH into a pass.
- To lift the cap on a CVE you have decided to live with, suppress it explicitly (`--ignore`,
  or an owner-and-expiry acceptance in `.vigil/context.md`). That prints beside the grade where
  a reviewer sees it; a quiet downgrade does not.
- No other pattern may put the correlated severity below its constituents.

## Rule 8: Report Honestly

- If a cluster has no findings, report it as clean — don't manufacture issues
- If a tool isn't installed, report it as SKIPPED with install instructions
- If a tool errors, report the error — don't silently skip
- Never inflate severity to look thorough
- Never downplay severity to avoid difficult conversations

## Rule 9: Actionability

Every finding MUST include:
1. **What** — one-line description
2. **Where** — file:line or glob pattern
3. **Why** — why this matters (impact, not just "best practice")
4. **Fix** — concrete remediation (code snippet or command)
5. **Refs** — link to relevant standard/CVE/docs (when applicable)

## Rule 10: Baseline Awareness

- If `.vigil/baseline.json` exists, compute deltas (new/fixed/regressed)
- Trend indicators: `+` new, `-` fixed, `!` regressed (was fixed, now back)
- Never report fixed findings as new
- Track score trend over time

**Deltas match on identity, never on the display ID.** Sequential numbers renumber (Rule 6):
inserting one finding shifts every finding after it in that cluster, so an ID-matched delta
reports the whole tail as fixed *and* new at once — exactly the "fixed findings as new" this
rule forbids, on the one screen a reviewer reads for movement.

Identity is a three-field tuple, written beside each finding in `.vigil/baseline.json`:

| Field | Value | Why not the obvious alternative |
|-------|-------|---------------------------------|
| cluster | cluster prefix (`SEC`, `DATA`, `CORR`, …) | — |
| path | repo-relative, POSIX separators, **no line number** | a finding does not become a different finding because an import was added above it |
| rule | tool rule id (`bandit:B608`, `ruff:S105`, `CVE-2024-1234`), the correlation pattern name for a CORR, or the normalised title where the detection has no rule id | descriptions are free text and reword between runs |

Compare the three fields directly; a short hash of them is a display convenience, never the
identity. Severity is deliberately excluded: a finding whose severity moved is the same finding
at a new severity, not one fixed plus one new. Where the same tuple occurs several times in a
file, match by count — 2 in the baseline and 3 now is one new finding, not 2 fixed and 3 new. A
baseline written without these fields can only be matched on path plus rule; say so in the
report rather than guessing.

## Rationalizations to Reject

When you find a potential issue, your instinct will be to explain it away. Reject these rationalizations:

| Rationalization | Why It's Wrong | Required Action |
|-----------------|----------------|-----------------|
| "It's just a development default" | If it reaches production code, it's a finding | Report it — code-level vulnerability exists regardless of config |
| "The production config overrides it" | Verify prod config exists; many apps fail silently with defaults | Prove override with evidence or report as fail-open |
| "This would never run without proper config" | Many apps start fine with insecure defaults | Trace the code path — does it crash or run insecurely? |
| "It's behind authentication" | Defense in depth — compromised session still exploits weak defaults | Report with reduced severity, not dismissed |
| "We'll fix it before release" | "Later" rarely comes | Document now — the finding exists today |
| "It's documented" | Developers don't read docs under deadline pressure | Make the secure choice the default or only option |
| "Advanced users need flexibility" | Most "advanced" usage is copy-paste from Stack Overflow | Report the footgun — flexibility creates misuse |
| "Nobody would actually do that" | Developers do everything imaginable under pressure | Assume maximum developer confusion |
| "It's just a configuration option" | Config is code — wrong configs ship to production | Validate configs; reject dangerous combinations |
| "It's only test code" | Unless it's in `tests/`, `spec/`, `__tests__/` with test fixtures, it's production-reachable | Verify the file path before dismissing |
| "The framework handles that" | Does it? Verify framework defaults. Many frameworks are insecure by default | Check framework docs, test the actual behavior |
| "It's an internal API" | Internal APIs get exposed. Network boundaries shift. Zero trust. | Report with context-adjusted severity |

If you catch yourself rationalizing a finding away, that's a signal to investigate harder, not dismiss faster.

## Anti-Patterns — NEVER Do These

1. **Wall of warnings** — If >50 findings, group by cluster and show top 10 per cluster
2. **Tool shopping** — Don't run 15 tools when 3 cover the stack. Match tools to detected stack.
3. **Severity inflation** — A missing docstring is LOW, not MEDIUM. A style violation is INFO, not LOW.
4. **Copy-paste findings** — Each finding must be specific to THIS codebase, not generic advice
5. **Ignoring context** — A SQL query in an admin-only CLI is not the same severity as one in a public API
6. **Audit theater** — Running tools just to show you ran them. Skip clusters that don't apply.
