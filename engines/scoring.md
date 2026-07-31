# VIGIL Engine: Scoring

## Score Formula

Each cluster starts at 100, loses points per finding, and is then capped by the evidence
ceiling preflight computed for it:

```
cluster_score = min(ceiling, max(0, 100 - sum(penalties)))
```

`ceiling` is 100, 85, or N/E — see **Evidence Coverage — the N/E state** below. **The ceiling
caps the result; it never subtracts from it.** A cluster on partial evidence carrying 12 points
of penalties scores `min(85, 88)` = **85** — not 73, and not 88.

The two other readings the old wording permitted are both worse. Subtracting from the ceiling
(`85 - 12 = 73`) charges the repo twice for one absent binary: once in lost coverage, once in
points. Applying the ceiling only to clusters that are already clean gives 88, so a cluster with
12 points of real findings would outscore a clean cluster on the same partial evidence — the
findings would be *raising* the score.

### Penalty Table

| Severity | Penalty |
|----------|---------|
| CRITICAL | 25 pts |
| HIGH | 10 pts |
| MEDIUM | 4 pts |
| LOW | 1 pt |
| INFO | 0 pts |

### Correlated Finding Scoring

When a correlated finding replaces constituents:
- Use the correlated finding's severity for penalty
- Do NOT sum constituent penalties
- Example: 3 MEDIUMs (12pts) correlated to 1 CRITICAL (25pts) = 25pts penalty, not 12pts

**Every correlated finding MUST be assigned to a primary cluster, and its penalty applied
there.** Without this rule correlation *improves* the headline score by deleting findings:
three HIGHs in Security take that cluster to 70, but correlating them into one CRITICAL and
removing the constituents leaves Security back near 100 with the penalty charged to nobody.
Escalating severity while raising the average is the opposite of what correlation is for.

Pick the primary cluster by where the *root cause* lives, not where the symptom surfaced, and
name it in the report:

```
VIGIL-CORR-001  HIGH  [TRUST_LAUNDERING]  primary: EGRESS (−10)
  ├─ VIGIL-EGRESS-004  (constituent, removed from cluster listing)
  └─ VIGIL-COMP-002    (constituent, removed from cluster listing)
```

Constituents are removed from the per-cluster listing but the correlated penalty lands in a
cluster, so the per-cluster table still shows where the damage is.

**Suppressing a correlated finding restores its constituents.** `--ignore VIGIL-CORR-001`
after its constituents were replaced would otherwise leave *nothing* unresolved, lifting the
severity floor and returning an A — suppressing one ID to erase several findings. If a CORR is
ignored, its constituents return to the report and to scoring at their original severities.
Ignoring a correlation is a statement about the *link*, never about the underlying findings.

### Cluster Weights

| Cluster | Weight | Rationale |
|---------|--------|-----------|
| Security | 22% | Most impactful domain — breaches are existential |
| Data & Persistence | 12% | Data loss/corruption is second to breaches |
| API & Networking | 10% | External attack surface |
| Infrastructure & DevOps | 10% | Deployment and operational risk |
| Architecture & Code Health | 10% | Long-term maintainability |
| Frontend & Mobile | 10% | Client-side attack surface, a11y and i18n obligations |
| Performance | 8% | User experience and cost |
| Compliance & Docs | 6% | Regulatory and operational |
| AI & ML | 8% | Growing risk domain |
| Data Egress & Provenance | 10% | What leaves the repo, and whether it is labelled honestly |
| Blockchain | 8% | On-chain code is immutable once deployed and directly custodies value |

**This table is the single authority for cluster weights.** Cluster files restate their weight
in the header for readability; if the two ever disagree, this table wins and the header is the
bug. `evals/check_repo.py` check L13 enforces the match — two clusters had drifted before it
existed, which meant two auditors could compute two different overall scores from the same
findings and both claim to be following the rules.

**Weights are normalised, not absolute.** The N/A formula below divides by the sum of
*applicable* weights, so this column need not total 100. Adding a cluster does not require
rebalancing the others.

**"Auth & Access" is a display-only lens, not a weighted cluster.** It previously carried 14%
in this table while having no cluster file, no ID prefix, and no defined mechanics — so two
auditors could disagree on whether an auth finding was penalised once (Security) or twice
(Security + lens), and on whether the normalisation denominator was 114 or 128. Both readings
produced different overall scores from identical findings.

It is now **0% weight**. Auth findings are ordinary `VIGIL-SEC-*` findings, penalised once in
Security. Reports may still *group* them under an "Auth & Access" heading for readability —
that grouping changes no arithmetic.

### N/A Cluster Handling

When a cluster doesn't apply (e.g., no frontend, no ML):
1. Remove from weight calculation
2. Redistribute weight proportionally to remaining clusters
3. Example: No frontend (10%) → remaining 90% becomes 100%, each cluster's weight scales up by 1/0.9

#### N/A must be earned — the incentive runs the wrong way

Removing a cluster deletes its penalty and up-weights the cleaner ones, so **an auditor gets a
better score by under-detecting applicability than by finding issues.** The realistic adversary
is not malicious: marking N/A is one sentence, establishing applicability is work, and the
formula pays for the shortcut. When the cheap action and the rewarded action coincide, the
mechanism gets gamed without anyone deciding to cheat.

**Applicability triggers.** Every cluster declares file patterns that *forbid* N/A. Preflight
already detects the stack mechanically; the same scan invalidates unjustified N/As:

| Cluster | Triggers that forbid N/A |
|---------|--------------------------|
| Frontend & Mobile | `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`, `index.html` |
| Blockchain | `*.sol`, `*.vy`, `foundry.toml`, `hardhat.config.*`, `Anchor.toml` |
| AI & ML | `*.ipynb`, imports of `torch`/`tensorflow`/`sklearn`/`transformers`, `openai`/`anthropic` SDK |
| Data & Persistence | `migrations/`, ORM imports, `*.sql`, `schema.prisma` |
| API & Networking | route/handler dirs, `openapi.*`, `*.proto`, `graphql` schema |
| Infrastructure & DevOps | `Dockerfile`, `*.tf`, `.github/workflows/`, `k8s/`, `docker-compose.*` |
| Data Egress & Provenance | export/bundle dirs, `*.csv`/`*.parquet`/`*.xlsx` over 100 KB, archive writers |
| Security · Code Health · Performance · Compliance | **never N/A** — every codebase has these |

An N/A asserted while a trigger matches is **`N/A CONTESTED`**: the cluster is forced
applicable, and if it cannot then be examined it becomes N/E — which blocks the pass verdict.
That inverts the gradient: a contested N/A is now *worse* than examining the cluster.

**Triggers cannot be complete**, and pretending otherwise is its own error — a stray notebook
does not mean ML applies. So every N/A also carries a one-line evidence statement naming what
was searched:

```
Blockchain — N/A: no *.sol, no foundry.toml, no Anchor.toml (root + 2 levels)
```

Prose alone is audit theatre; triggers alone miss judgement calls. Together, an unjustified N/A
requires either a false statement in the report or a stack the trigger genuinely cannot see —
rare, and reviewable.

```
adjusted_weight[i] = base_weight[i] / sum(applicable_base_weights)
```

### Overall Score

```
overall = sum(cluster_score[i] * adjusted_weight[i]) for all applicable clusters
```

## Grade Scale

| Grade | Range | Meaning |
|-------|-------|---------|
| A+ | 95-100 | Exceptional — minimal findings, all LOW/INFO |
| A | 90-94 | Excellent — production-ready with confidence |
| B | 80-89 | Good — production-ready, minor improvements possible |
| C | 70-79 | Adequate — functional but needs attention |
| D | 60-69 | Below standard — significant gaps |
| E | 40-59 | Poor — major remediation needed |
| F | 0-39 | Failing — critical issues, not deployable |

### Production-ready requires a score AND full coverage

**A pass verdict needs both:**

1. `overall >= 80`, after severity floors, **and**
2. every applicable cluster at ceiling **100** — no cluster at 85 (partial evidence), none N/E.

Any cluster below full coverage yields **"INCOMPLETE — evidence partial"**, never a pass, no
matter how good the number looks.

The 85 ceiling alone was a grade penalty, not an evidence statement. All clusters at 85 with
zero findings gave overall 85 → B → "production-ready, address findings when convenient" —
while the tools that would have found the HIGHs never ran. That is the same lie as scoring an
unexamined cluster 100, just quieter. Partial evidence degrades the **verdict**, not only the
number.

This stays usable only if required-tool lists are **small and honest**. `ruff`/`mypy` are
genuinely gating; `semgrep` is correctly optional. **If a tool is missing on most normal
machines, it was misclassified as required — that is a manifest bug, not a reason to weaken the
gate.** Users without a tool still get the full report and a partial score; they just do not get
the word "pass."

## Severity Floors (Gate Override)

The weighted average can bury a serious finding in a low-weight cluster. A HIGH in Compliance
(6%) moves the overall by less than a point — so an export bundle that could cross an air gap
carrying unlabeled model output under a false provenance date still scored **94/A**. The number
said ship; the findings said stop.

**The grade must never contradict the findings.** After computing `overall`, apply a ceiling:

| Max unresolved severity | Overall capped at | Grade ceiling |
|-------------------------|-------------------|---------------|
| CRITICAL | 59 | E |
| HIGH | 79 | C |
| MEDIUM | 89 | B |
| LOW / INFO only | no cap | — |

Rules:
- The cap is a **ceiling, never a penalty**. It can only lower a score, never raise one.
- "Unresolved" excludes findings suppressed by `--ignore` or accepted in the context file.
  Everything else counts, including `NEEDS_REVIEW`.
- **`NEEDS_REVIEW` counts at its suspected severity**, and the report must name that suspicion:
  `NEEDS_REVIEW (suspected CRITICAL)`. Rule 3 says to mark an uncertain finding `NEEDS_REVIEW`
  rather than CRITICAL — a statement about confidence in the *claim*, not a severity. This table
  is keyed on severity, so reading `NEEDS_REVIEW` as one inverts the rule it came from: doubting
  a CRITICAL would remove the cap, which makes doubt the cheapest route through the gate and
  dissolves the floor the honesty valve exists to feed. Uncertainty about exploitability is a
  reason to look harder, never a discount. One with no suspected severity fails closed at the
  highest its evidence could support — naming it is the auditor's job, not the reader's guess —
  and it holds the cap until it is *resolved*: confirmed at a real severity, withdrawn under
  Rule 3's false-positive test, or accepted with an owner and an expiry like any other cap
  lift.
- Correlated findings apply at their **correlated** severity (per Rule 7), not their
  constituents'.
- Per-cluster scores are **not** capped. They stay uncapped so the report still shows *where*
  the damage is; only the headline verdict is gated.

Always show the cap — a silently lowered number reads as an arithmetic error:

```
OVERALL: 79/100  C  (capped from 94 by VIGIL-CORR-001 HIGH)
NOT PRODUCTION READY — 1 HIGH unresolved
```

### Suppressions must be visible next to the grade

Suppressing a finding via `--ignore` or a context-file risk acceptance is the one supported
way to lift a cap. That makes it the one thing a reader must not have to go looking for —
otherwise "A, 94/100" and "A, 94/100 because we hid the HIGH" are indistinguishable.

Whenever any finding is suppressed, print the count on the score line and enumerate what was
suppressed and on whose authority:

```
OVERALL: 94/100  A   (3 findings suppressed — see below)
  VIGIL-SEC-004  HIGH    --ignore on the command line
  VIGIL-DATA-009 MEDIUM  accepted in .vigil/context.md until Q3 (owner: platform)
```

A suppressed CRITICAL or HIGH lifts the cap but never disappears. If suppressions cannot be
listed, do not apply them — an unexplained lifted cap is worse than an uncapped score.

### Suppression changes scoring status, never the finding

`context-loader.md` states the Golden Rule: **context can escalate risk; it can never hide or
downgrade a mechanical finding.** That and cap-lifting are the same rule seen from two sides,
and stating them separately made them read as a contradiction:

- The finding is **always reported**, at its mechanically-derived severity. Acceptance never
  deletes it, downgrades it, or removes it from the cluster listing.
- Acceptance changes only its **scoring status** — it stops holding the severity floor down.
- Every acceptance requires an **owner and an expiry**, and appears in the suppression ledger
  beside the grade. An acceptance with neither is not an acceptance; ignore it and keep the cap.
- Expired acceptances revert automatically and re-apply the cap.

**Provenance caveat:** `.vigil/context.md` and `.vigil/ignore` live inside the audited
repository, so the audited party authors its own suppressions. That is workable *because* every
one is printed with owner and expiry. Never accept a suppression that is anonymous or open-ended
— that is the audited party grading itself.

## Evidence Coverage — the N/E state

Rule 1 is evidence before opinion. A cluster whose tools never ran has **no evidence**, and
scoring it 100 asserts "clean" when the truth is "not looked at." An empty tool result is a
tooling outcome, not a finding.

Each cluster declares required and optional tools ([engines/preflight.md](preflight.md)).
After preflight, each cluster gets a ceiling from what actually executed:

| Required tools that ran | Cluster ceiling |
|-------------------------|-----------------|
| all | 100 |
| some (≥1 missing) | 85 — an A is unreachable on partial evidence |
| none | **N/E** |

**N/E is not N/A.** Keep them distinct in every report:

| State | Meaning | Weighting |
|-------|---------|-----------|
| **N/A** | Cluster does not apply to this stack (no frontend, no contracts) | Removed; weight redistributed |
| **N/E** | Cluster applies but could not be examined | **Not** removed, **not** scored |

Any cluster at N/E makes the audit incomplete. Report the overall as:

```
OVERALL: INCOMPLETE — 1 of 6 clusters had no evidence (security: semgrep, bandit unavailable)
Partial score across examined clusters: 91/100 — 5 of 6 examined; security (22%) excluded
NOT a pass verdict · NOT comparable to a full-coverage score or to a baseline.
```

**N/E clusters leave both sides of that fraction.** They contribute no points, and their weight
leaves the denominator:

```
partial = sum(cluster_score[i] * base_weight[i]) / sum(base_weight[i])
          over EXAMINED clusters only — N/A and N/E alike are out of both sums
```

Every other denominator is worse. Keeping N/E weight in it while scoring those clusters 0
invents findings nobody observed — the mirror image of scoring an unexamined cluster 100. And
leaving it unstated, where "not removed, not scored" left it, means two auditors publish two
different numbers from identical evidence.

The arithmetic matches the N/A redistribution above; what may be done with the result does not.
An N/A denominator yields a *score*, because the removed clusters genuinely do not exist. An
N/E denominator yields a number computed over a smaller repo than the one audited, and the
missing part is missing precisely because nobody looked at it — so it is the part most likely to
be bad. In the example above it is Security's 22% that dropped out of the denominator: 91 looks
good because the heaviest cluster in the table is the one that went unexamined.

So always print the partial score with the coverage it was computed over, never bare, and
compute no `▲`/`▼` against a baseline while any cluster is N/E — see **A ceiling change is not a
code change** below.

Never emit a pass verdict, a grade letter, or a `--ci` exit 0 while any applicable cluster is
N/E. Missing tools fail closed: an audit that could not look is not an audit that found nothing.

## Trend Tracking

### Baseline File (`.vigil/baseline.json`)

```json
{
  "version": 1,
  "timestamp": "2026-03-27T10:30:00Z",
  "commit": "abc1234",
  "overall_score": 74,
  "overall_grade": "C",
  "clusters": {
    "security": { "score": 65, "grade": "D", "findings_count": 8, "ceiling": 100 },
    "code-health": { "score": 85, "grade": "B", "findings_count": 12, "ceiling": 100 }
  },
  "findings": [
    {
      "id": "VIGIL-SEC-001",
      "severity": "HIGH",
      "description": "Hardcoded API key",
      "file": "config.py",
      "line": 23
    }
  ]
}
```

### Trend Indicators

| Symbol | Meaning |
|--------|---------|
| ▲ | Improved (score increased) |
| ▼ | Declined (score decreased) |
| → | Unchanged (±1 point) |

### Delta Display

```
OVERALL: 78/100 C ▲+4
```

Delta is current - baseline. Positive = improvement.

#### A ceiling change is not a code change

A cluster's ceiling is a property of **the auditor's machine**, not of the repository.
`brew install semgrep` lifts Security from 85 to 100 and moves the overall by points with the
working tree untouched — and a `▲` beside a number is read as "the code got better."

So the baseline records each cluster's ceiling (and its tool versions, per preflight rule 4),
and a delta is reported only once those match:

- **Ceilings unchanged** — report the delta normally.
- **A ceiling rose** — split it. The coverage move is reported separately and never folded into
  the findings delta:

```
OVERALL: 91/100 A ▲+6  (+6 coverage: security ceiling 85→100, semgrep now installed)
                       (+0 findings: nothing has been fixed since the baseline)
```

- **A ceiling fell** — a coverage regression, not a code regression, and the more dangerous
  direction: it reads as the code getting worse when the truth is that the audit went blind.
  Name the tool that stopped running.

A baseline written on one machine and compared on another is not a trend line — it is two
different audits subtracted from each other.

## Score Interpretation Guide

For the output report, include actionable interpretation. **Coverage is the first column
because it is the first check** — a number on its own never earns the phrase "production-ready"
(see *Production-ready requires a score AND full coverage* above):

| Coverage | Score Range | What to Tell the User |
|----------|-------------|----------------------|
| any cluster N/E | any | "INCOMPLETE — an applicable cluster could not be examined. No verdict, no grade letter." |
| any cluster below ceiling 100 | any | "INCOMPLETE — evidence partial. This number is an upper bound; install the missing tools and re-run." |
| full | 95+ | "Exemplary. Maintain current practices." |
| full | 80-94 | "Production-ready. Address remaining findings when convenient." |
| full | 70-79 | "Not production-ready. Fix HIGH findings before deploy." |
| full | 60-69 | "Significant gaps. Dedicate a sprint to remediation." |
| full | 40-59 | "Major issues. Stop feature work, focus on fundamentals." |
| full | <40 | "Critical state. Immediate remediation required." |

Without that column the 80-94 row stood alone as a verdict, and it is the one sentence in this
file most likely to be pasted into a status update away from every condition on it. An 85 built
entirely from tools that never ran produced exactly those words — the failure the coverage rule
above was written to stop, reintroduced further down the same file by a table that did not
repeat it.
