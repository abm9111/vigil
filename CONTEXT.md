# VIGIL Context-Aware Auditing

**Status:** Proposed enhancement (Phase 1 implementation started May 2026)  
**Goal:** Close the gap between generic automated auditing and expert human judgment on complex, high-stakes, or domain-specific codebases.

---

## The Problem

Standard VIGIL runs are excellent at mechanical rigor (lint, types, dependency vulns, OWASP patterns, correlation). However, they are **generalists**.

On projects with any of the following characteristics, pure mechanical auditing consistently under-prioritizes the highest real-world risks:

- Heavy regulatory or processor compliance requirements (e.g. card-network brand-risk programs, GDPR, HIPAA)
- Hybrid architectures (modern frontend + legacy monolith, dual-backend migrations)
- Business-critical controls that are not traditional "vulnerabilities" (suspension lists, descriptor sanitisation, entitlement-balance rules, etc.)
- Projects where the source of truth for security/compliance logic lives in unexpected places (CMS hooks, plugins, cron jobs on a decommissioned host, etc.)
- Situations where "this would be MEDIUM in a normal SaaS" is actually **existential** for this specific business

**Result:** VIGIL produces a correct report, but a strong human auditor with project context produces a *more dangerous* and actionable one.

This enhancement exists to give VIGIL access to the same class of context that expert auditors use.

---

## Core Concepts

### 1. VIGIL Context File

A project can place one or both of these files in the repository root (or `.vigil/` directory):

- `.vigil/context.md` — Human-readable + lightly structured (recommended for most teams)
- `vigil-context.json` — Machine-readable (for CI-heavy teams or generated context)

VIGIL will automatically discover and load the context when present during `audit`, `siege`, `score`, and `watch` modes.

### 2. Control Criticality

Instead of treating all issues equally, context can declare that certain areas are:

- **EXISTENTIAL** — Failure here can kill or severely damage the business (suspended-account bypass, brand-risk term leakage, payment processor termination risk)
- **HIGH_BUSINESS_IMPACT** — Major revenue, legal, or operational damage
- **REGULATORY_MUST** — Direct compliance obligation

These tags change scoring, correlation priority, and report emphasis even when the raw technical severity is only MEDIUM or LOW.

### 3. Domain Profiles

Pre-defined or custom profiles that activate specialized rules and weightings:

- `regulated-payments` (card-network brand risk, PCI-adjacent, processor risk)
- `hybrid-legacy-migration`
- `ai-heavy` (LLM output control, tool-use safety, streaming compliance)
- `high-stakes-ecommerce`
- Custom profiles per organization

### 4. Critical Paths

Explicit declaration of the flows that actually protect the business:

```md
## Critical Paths
1. Suspension enforcement → order creation → payment
2. LLM Streaming → Compliance Filter → Client
3. Payment Line Items → Gateway Sanitizer
```

Findings that touch declared critical paths receive escalation during correlation.

### 5. Architecture & Source-of-Truth Reality

Projects can document uncomfortable truths that generic tools cannot discover:

- "The legacy CMS remains the authoritative source for account suspensions and entitlement balances"
- "Many cross-system calls still point at the decommissioned domain after the 410 hard-close"
- "A single 3,000+ LOC file contains the majority of compliance enforcement logic"

This prevents VIGIL from treating the modern, well-instrumented surface as the complete picture.

---

## File Format (Recommended: context.md)

```markdown
# VIGIL Context — [Project Name]

## Business Risk Model
- [Control name] is EXISTENTIAL because [one sentence reason]
- [Control name] is HIGH_BUSINESS_IMPACT because ...

## Domain Profiles
- regulated-payments
- hybrid-legacy-migration

## Architecture Reality
- ...

## Critical Paths
1. ...
2. ...

## Accepted Risks (optional)
- VIGIL-SEC-042 is accepted until Q3 because ...

## Custom Rules (optional)
- Any finding on the suspension enforcement path must be treated as at least HIGH
```

See `templates/vigil-context.md` for a complete starter.

JSON format is also supported for teams that want to generate context programmatically.

---

## How the Auditor Must Use Context (Rules)

When a context file is present:

1. **Load it early** — before running clusters.
2. **Apply Control Criticality** to re-weight or escalate findings.
3. **Activate Domain Profiles** — these may add extra checks or change default severities.
4. **Use Critical Paths** during correlation (see `engines/correlation.md` update in Phase 2).
5. **Surface context influence** in the final report (e.g. "This finding was escalated because it touches the declared EXISTENTIAL control: Account-Suspension Enforcement").
6. **Never ignore context** to make findings look better or worse. Context is evidence.

The binding requirements are Rules 1–10 in [RULES.md](RULES.md); context does not add a rule. In particular Rule 1 (evidence before opinion) still governs — context changes *priority*, never whether a finding is evidenced.

---

## Impact on Scoring

Context affects scoring **only through severity**, which then flows through the ordinary
penalty table. There are no bonus points, no weight shifts and no multipliers — an earlier
draft of this document described all three, none were ever implemented, and an auditor
following it had to invent the numbers.

- Control criticality escalates a touching finding one severity level.
- Accepted risks change scoring *status* only, and require owner + expiry — see
  [engines/scoring.md](engines/scoring.md).
- A correlation spanning a declared critical path escalates one level under the normal rules
  in [engines/correlation.md](engines/correlation.md).

Domain profiles change *which checks run and how they are prioritised*. They do not change
cluster weights; `engines/scoring.md` is the single authority for those.

The overall score must still be honest — context makes the report *more accurate for this project*, not artificially better or worse.

---

## Worked example

A regulated e-commerce project with a dual-backend architecture. Had this context been
present, the audit would have prioritised very differently:

```markdown
## Business Risk Model
- Account-suspension enforcement is EXISTENTIAL (re-entry by a suspended account = provider termination + legal exposure)
- Card-network brand-risk compliance is EXISTENTIAL
- Descriptor sanitisation on every order path is CRITICAL

## Domain Profiles
- regulated-payments
- hybrid-legacy-migration

## Architecture Reality
- Dual-backend: a modern SPA for the customer surface, a legacy CMS still authoritative for fulfilment, suspensions and several compliance hooks
- Since the old host began returning 410, multiple cross-system dependencies still point at it

## Critical Paths
1. Suspension check (live + daily sync) → order creation → payment
2. LLM streaming output → compliance stream filter → client
3. Order line items → gateway descriptor sanitisers (both backends)
```

**Expected effect on the audit:**
- The suspension-enforcement degradation (calling a decommissioned host) becomes a clear
  **CRITICAL** correlated finding instead of a scattered set of MEDIUMs.
- The multi-thousand-line legacy monolith is flagged with higher severity under Code Health +
  Compliance, because context marks it as the enforcement chokepoint.
- Dependency vulnerabilities still appear, but no longer dominate the top of the report.

---

## Adoption & Migration

1. Start with the template in `templates/vigil-context.md`.
2. Fill in the sections that are actually true for your project (be ruthless).
3. Commit the file (it is not secret — it describes risk priorities, not credentials).
4. Re-run VIGIL audit and compare the output.
5. Iterate. The context file is living documentation of what actually matters.

Teams that maintain good CLAUDE.md / AGENTS.md files will find this transition natural.

---

## Open Questions (Phase 2+)

- Should context also influence `--fix` behavior?
- How do we handle conflicting signals between mechanical findings and declared context?
- Should we support organization-level default context (e.g. company-wide brand-risk rules)?
- Integration with the existing `.vigil/ignore` and baseline system.

---

## Status & Roadmap

- **Phase 1 (Current)**: Core loading + scoring adjustments + template + RULE updates (this document)
- **Phase 2**: Full correlation engine upgrades + Domain Profile activation + companion command (`/vigil-context`)
- **Phase 3**: Profile library + CI examples + advanced critical path tracing

This is the highest-leverage single improvement to VIGIL identified during real usage on complex production systems.

---

**Author note:** This enhancement was driven by direct comparison between a context-rich human audit and a high-quality generic VIGIL run on the same codebase in May 2026. The gap was real and repeatable.
