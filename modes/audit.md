# VIGIL Mode: Audit

**Time budget:** 5-15 minutes
**Depth:** Deep — all findings, correlation, compliance mapping
**Loads:** ALL clusters + scoring + correlation engines

## Execution

### Step 1: Stack Detection + Cluster Selection (10s)

Same as scan mode. But load ALL applicable clusters.

### Step 2: Run All Cluster Audits (3-10min)

For each applicable cluster, execute in order:

1. **Security** — [clusters/security.md](../clusters/security.md) (always first)
2. **Code Health** — [clusters/code-health.md](../clusters/code-health.md)
3. **Data & Persistence** — [clusters/data-and-persistence.md](../clusters/data-and-persistence.md)
4. **API & Networking** — [clusters/api-and-networking.md](../clusters/api-and-networking.md)
5. **Infrastructure & DevOps** — [clusters/infrastructure-and-devops.md](../clusters/infrastructure-and-devops.md)
6. **Frontend & Mobile** — [clusters/frontend-and-mobile.md](../clusters/frontend-and-mobile.md)
7. **Performance** — [clusters/performance.md](../clusters/performance.md)
8. **AI & ML** — [clusters/ai-and-ml.md](../clusters/ai-and-ml.md)
9. **Data Egress & Provenance** — [clusters/data-egress-and-provenance.md](../clusters/data-egress-and-provenance.md) (any project that emits data artifacts, not just web apps)
10. **Blockchain** — [clusters/blockchain.md](../clusters/blockchain.md) (Solidity/Vyper/Move present)
11. **Compliance & Docs** — [clusters/compliance-and-docs.md](../clusters/compliance-and-docs.md)

This list must name **every** file in `clusters/`. A cluster absent here does not run in audit
mode even though the router says "ALL clusters" — the mode file is the operative instruction.
`evals/check_repo.py` check L7 enforces the match.

Each cluster:
1. Run deterministic tool commands
2. Parse tool output into findings
3. Apply AI reasoning for context and prioritization
4. Assign severity and finding IDs

### Step 3: Cross-Domain Correlation (1-2min)

Per [engines/correlation.md](../engines/correlation.md):

1. Collect all findings from all clusters
2. Run all 10 correlation pattern matchers
3. For each match: create correlated finding (VIGIL-CORR-xxx)
4. Correlated findings replace their constituents in the report
5. Severity escalation per correlation rules

### Step 4: Compliance Mapping (if --compliance flag)

Per compliance map files:
- Tag each finding with applicable controls
- Generate compliance gap summary
- Highlight unmapped controls (gaps)

### Step 5: Scoring (30s)

Per [engines/scoring.md](../engines/scoring.md):
1. Score each cluster 0-100
2. Apply weights
3. Compute overall score
4. Compare to baseline (if exists)

### Step 6: Report

## Output Template

```
VIGIL audit — {project} @ {commit_short} ({date})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Stack: {detected_stack}
Clusters: {N} audited, {M} N/A, {K} N/E (no evidence)

━━━ Preflight ━━━
Tools     {tool} {version} ✓ ...
          {tool} ✗ MISSING ({required|optional}: {cluster}) → {install_cmd}
Coverage  {cluster}  {n}/{m} required   ceiling {100|85|N/E}

{if correlated findings:}
━━━ Correlated Findings (Cross-Domain) ━━━
VIGIL-CORR-001  CRITICAL  {attack narrative}
  ├─ VIGIL-SEC-003  missing auth on /admin/users
  ├─ VIGIL-DATA-007  raw SQL in user query handler
  └─ VIGIL-API-012  PII in response body (email, phone)
{...}

━━━ Findings by Cluster ━━━

Security ({score}/100 {grade})
  VIGIL-SEC-001  HIGH    Hardcoded API key in config.py:23
  VIGIL-SEC-002  MEDIUM  Missing rate limiting on /api/login
  {fix suggestions inline}

Code Health ({score}/100 {grade})
  VIGIL-CODE-001  MEDIUM  12 ruff violations (F401×3, E501×9)
  VIGIL-CODE-002  LOW     No type annotations on 8 public functions
  {fix suggestions inline}

{...each cluster...}

━━━ Score Summary ━━━
SEC     {score}/100  {grade}  {trend}  (weight: 22%)
CODE    {score}/100  {grade}  {trend}  (weight: 10%)
API     {score}/100  {grade}  {trend}  (weight: 10%)
DATA    {score}/100  {grade}  {trend}  (weight: 12%)
INFRA   {score}/100  {grade}  {trend}  (weight: 10%)
FE      {score}/100  {grade}  {trend}  (weight: 10%)  {or N/A}
PERF    {score}/100  {grade}  {trend}  (weight: 8%)
COMP    {score}/100  {grade}  {trend}  (weight: 6%)
AIML    {score}/100  {grade}  {trend}  (weight: 8%)   {or N/A}

EGRESS  {score}/100  {grade}  {trend}  (weight: 10%)
CHAIN   {score}/100  {grade}  {trend}  (weight: 8%)   {or N/A}

{if NO cluster is N/E:}
OVERALL: {score}/100  {grade}  {trend} {delta}
{if capped:}  (capped from {raw} by {finding_id} {severity})
{PRODUCTION READY | NOT PRODUCTION READY}

{if ANY cluster is N/E — these lines REPLACE the block above; emit no grade letter
 and no pass verdict, per engines/scoring.md:}
OVERALL: INCOMPLETE — {K} of {N} clusters had no evidence ({which tools missing})
Partial score across examined clusters: {score}/100 — {n} of {m} examined;
{cluster} ({weight}%) excluded. NOT a pass verdict, and NOT comparable to a
full-coverage score or to a baseline.

{if --compliance:}
━━━ Compliance Summary ━━━
{standard}: {covered}/{total} controls mapped
  Gaps: {list of unmapped controls}

━━━ Recommendations ━━━
1. {highest impact fix}
2. {second highest}
3. {third highest}
```

## Rules for Audit Mode

- Run ALL applicable clusters, not just security
- Run correlation engine — this is the differentiator
- Report ALL severities (unless --threshold flag)
- Include fix suggestions for every finding
- Time budget is advisory, not hard limit — accuracy > speed
- Group findings by cluster, correlated findings at top
