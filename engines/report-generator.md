# VIGIL Engine: Consulting Report Generator

**Purpose:** Generate professional security audit deliverables for consulting engagements (ComplianceSprint, SiegeReport, ManagedVIGIL retainer reports).

## Report Types

### ComplianceSprint (tier $, 3-day delivery)

**Target audience:** CTO/CISO at an SME or startup
**Length:** 15-25 pages
**Tone:** Executive + technical hybrid

```
COMPLIANCE SPRINT REPORT
========================

Prepared for: {client_name}
Prepared by: {your_name}, {your_title}
Date: {date}
Classification: CONFIDENTIAL

TABLE OF CONTENTS
1. Executive Summary
2. Scope & Methodology
3. Risk Dashboard
4. Critical Findings (immediate action)
5. High-Priority Findings
6. Medium/Low Findings
7. Compliance Gap Analysis
8. Remediation Roadmap
9. Appendix: Tool Output & Evidence

───────────────────────────────────

1. EXECUTIVE SUMMARY

{2-3 paragraphs for non-technical executives}
- Overall security posture: {VIGIL score}/100 ({grade})
- Critical issues requiring immediate attention: {N}
- Estimated remediation effort: {X} engineering-days
- Compliance readiness: {SOC2|ISO27001|OWASP} at {X}%

Key finding: {one-sentence description of the most impactful finding}

2. SCOPE & METHODOLOGY

Scope:
- Repository: {repo_url} (commit {hash})
- Languages: {detected_languages}
- Frameworks: {detected_frameworks}
- Lines of code: {loc}
- Test coverage: {coverage}%

Methodology:
- Static analysis (Semgrep, Bandit, ESLint security rules)
- Dependency vulnerability audit (pip-audit, npm audit, Trivy)
- Secret detection (TruffleHog verified mode)
- Configuration review (Docker, CI/CD, cloud IAM)
- Manual code review (authentication flows, data handling, API security)
- Cross-domain correlation analysis (VIGIL proprietary)

Out of scope:
- Dynamic/runtime testing
- Social engineering
- Physical security
- {client-specified exclusions}

3. RISK DASHBOARD

┌─────────────────┬───────┬────────┐
│ Domain          │ Score │ Grade  │
├─────────────────┼───────┼────────┤
│ Security        │ {XX}  │ {A-F}  │
│ Authentication  │ {XX}  │ {A-F}  │
│ Data Protection │ {XX}  │ {A-F}  │
│ API Security    │ {XX}  │ {A-F}  │
│ Infrastructure  │ {XX}  │ {A-F}  │
│ Code Quality    │ {XX}  │ {A-F}  │
├─────────────────┼───────┼────────┤
│ OVERALL         │ {XX}  │ {A-F}  │
└─────────────────┴───────┴────────┘

Finding Summary:
  CRITICAL: {N} (fix within 24 hours)
  HIGH:     {N} (fix within 1 week)
  MEDIUM:   {N} (fix within 1 month)
  LOW:      {N} (fix within quarter)

4-6. FINDINGS

{For each finding, use this structure:}

──────────────────────────────────────
FINDING: {VIGIL-ID} — {Title}
Severity: {CRITICAL|HIGH|MEDIUM|LOW}
CWE: {CWE-XXX}
OWASP: {A01-A10}
Location: {file}:{line}
──────────────────────────────────────

Description:
{what the issue is, in clear technical language}

Evidence:
{code snippet with vulnerable lines highlighted}
{tool output proving the finding}

Impact:
{what an attacker could do, quantified}

Remediation:
{specific fix with code example}
{defense-in-depth recommendation}

Priority: {IMMEDIATE|HIGH|MEDIUM|LOW}
Effort: {X} hours estimated

7. COMPLIANCE GAP ANALYSIS

{Map findings to relevant standard}

| Control | Status | Finding | Gap |
|---------|--------|---------|-----|
| SOC2 CC6.1 | ❌ FAIL | VIGIL-SEC-201 | No access control on admin endpoints |
| ISO 27001 A.8.24 | ⚠️ PARTIAL | VIGIL-SEC-301 | Dependencies not monitored |
| OWASP A01 | ❌ FAIL | VIGIL-SEC-201 | Broken access control |

8. REMEDIATION ROADMAP

Week 1 (Critical):
  □ {finding} — {fix description} — {effort}h
  □ {finding} — {fix description} — {effort}h

Week 2-3 (High):
  □ {finding} — {fix description} — {effort}h

Month 1 (Medium):
  □ {finding} — {fix description} — {effort}h

9. APPENDIX

{Raw tool output, full scan logs, methodology details}
```

### SiegeReport (tier $$$, 1-2 week delivery)

Everything in ComplianceSprint PLUS:

- **Attack scenarios** from siege mode (Step 2 of siege.md)
- **Threat model** (STRIDE per component)
- **Architecture diagram** with trust boundaries
- **Penetration test narrative** (chronological attack story)
- **Risk register** (likelihood x impact matrix)
- **Board-ready executive brief** (2-page standalone summary for board deck)

Additional sections:

```
THREAT MODEL (STRIDE)

| Component | Spoofing | Tampering | Repudiation | Info Disclosure | DoS | Elevation |
|-----------|----------|-----------|-------------|-----------------|-----|-----------|
| Auth API  | HIGH     | MEDIUM    | LOW         | HIGH            | LOW | CRITICAL  |
| Database  | LOW      | HIGH      | MEDIUM      | CRITICAL        | LOW | HIGH      |

RISK REGISTER

| Risk | Likelihood | Impact | Rating | Mitigation |
|------|-----------|--------|--------|------------|
| Data breach via SQL injection | HIGH | CRITICAL | EXTREME | Parameterized queries |
| Account takeover via JWT confusion | MEDIUM | HIGH | HIGH | Algorithm whitelist |

ATTACK NARRATIVE

"Starting from the internet with no credentials, an attacker would first..."
{chronological story connecting findings into attack chains}
```

### ManagedVIGIL Delta Report (tier $, monthly retainer)

See: [../modes/watch.md](../modes/watch.md) for base watch functionality.

Monthly retainer report adds:

```
MANAGED VIGIL — MONTHLY SECURITY REPORT
========================================
Client: {name} | Period: {month year} | Report #{N}

TREND
  Score: {last_month} → {this_month} ({+/-change})
  Grade: {last_grade} → {this_grade}

CHANGES THIS PERIOD
  New findings: {N}
  Fixed findings: {N}
  Regressed: {N}
  Net change: {+/-N}

{delta details per finding}

DEPENDENCY UPDATES
  New CVEs published: {N}
  Affecting your deps: {N}
  Action required: {list}

RECOMMENDATIONS
  Priority actions for next month:
  1. {action}
  2. {action}
  3. {action}

NEXT SCAN: {date}
```

## Generation Flow

1. **Input:** VIGIL audit/siege/watch output + client context
2. **Select template** based on engagement type
3. **Map findings** to template sections
4. **Generate prose** for executive summary, finding descriptions, remediation
5. **Add compliance mapping** from compliance-maps/
6. **Calculate effort estimates** (rough: CRITICAL=4h, HIGH=2h, MEDIUM=1h, LOW=0.5h)
7. **Format output** as markdown (client converts to PDF/Docx)
8. **Quality check:**
   - No internal VIGIL IDs visible (use sequential numbering: Finding 1, Finding 2...)
   - No tool names in executive summary (say "static analysis" not "Bandit")
   - All code snippets have context (not just the vulnerable line)
   - Remediation is specific (not "validate input" — show the code)
   - Executive summary is readable by non-technical board members

## Pricing Guide Reference

| Engagement | Delivery | Effort tier | VIGIL Mode |
|------------|----------|-------------|------------|
| ComplianceSprint | 3 days | $ | audit + compliance |
| SiegeReport | 1-2 weeks | $$$ | siege (full) |
| ManagedVIGIL | Monthly | $ recurring | watch + monthly audit |
| AIRedTeam | 1-2 weeks | $$ | siege --only ai-and-ml |

**Tiers are relative effort, not a rate card.** Figures depend on scope, jurisdiction,
liability and who is buying, so a number published here would be wrong for almost every
reader and would price an engagement before anyone had scoped it. Set your own.
