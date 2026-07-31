# /vigil-bounty — Platform-Ready Bounty Report Generator

**Trigger:** `/vigil-bounty [--platform h1|bc|immunefi] [--finding VIGIL-ID] [target]`
**Time:** 2-5 minutes per report
**Purpose:** Transform VIGIL findings into platform-ready bounty submissions with correct severity, impact proof, and reproduction steps

## Prerequisites

A completed `/vigil audit` or `/vigil siege` with at least one HIGH/CRITICAL finding.

## Platform Templates

### HackerOne Format

```markdown
## Summary
{one-line description: vulnerability type + location + impact}

## Vulnerability Type
{CWE ID}: {CWE Name}

## Description
{2-3 paragraphs: what, where, why it's exploitable}

## Steps to Reproduce
1. {exact step with URL/endpoint}
2. {exact request with curl/screenshot}
3. {observed behavior vs expected}

## Impact
{concrete impact: data exposed, accounts affected, escalation path}

## Severity Assessment
- **CVSS 3.1 Vector:** {AV:N/AC:L/...}
- **CVSS Score:** {0.0-10.0}
- **Suggested Severity:** {Critical/High/Medium/Low}

## Supporting Material/References
- {screenshot/video URL}
- {relevant CVE/CWE references}
- {code snippet with line numbers}

## Fix Recommendation
{concrete remediation with code example}
```

### Bugcrowd Format

```markdown
## Title
{Vulnerability Type} in {Component} allows {Impact}

## URL/Location
{exact endpoint or code path}

## Severity
{P1-P5 per Bugcrowd VRT}

## Description
{what + where + why, 2-3 paragraphs}

## Steps to Reproduce
1. {step}
2. {step}
3. {step}

## Impact
{business impact statement}

## Attachments
{list files: screenshots, PoC scripts, HTTP logs}
```

### Immunefi Format (Smart Contracts)

```markdown
## Bug Description
{technical description of the vulnerability}

## Impact
{specific impact per Immunefi severity guidelines}
- Funds at risk: {$amount or TVL percentage}
- Attack vector: {on-chain/off-chain}
- Prerequisites: {flash loan, specific role, etc.}

## Risk Breakdown
- Difficulty of Exploit: {Easy/Medium/Hard}
- CVSS: {vector string}

## Proof of Concept
{Foundry/Hardhat test code that demonstrates the exploit}

## Recommendation
{specific fix with code diff}

## References
{related CVEs, audits, similar bugs in other protocols}
```

## Execution

### Step 1: Select Finding (30s)

If `--finding` specified, load that finding. Otherwise, list all HIGH/CRITICAL findings:

```
Available findings for submission:
  1. VIGIL-SEC-001  CRITICAL  Hardcoded API key in config.py:23
  2. VIGIL-SEC-103  HIGH      SQL injection in api/users.py:45
  3. VIGIL-CORR-001 CRITICAL  Data exposure chain (auth + SQL + PII)

Select finding number (or 'all' for batch):
```

### Step 2: Enrich Finding (1-2min)

For the selected finding, gather additional context:

```bash
# Get the vulnerable code in context
grep -n -B5 -A10 '{pattern}' {file}

# Check git blame for timing
git log --oneline --follow -5 {file}

# Check if there's a fix branch already
git branch -a | grep -i 'fix\|patch\|security'

# Get project version
cat setup.py setup.cfg pyproject.toml package.json 2>/dev/null | grep -i 'version'
```

**CWE mapping** (auto-detect from finding type):

| VIGIL Pattern | CWE |
|---------------|-----|
| Hardcoded secret | CWE-798 |
| SQL injection | CWE-89 |
| Command injection | CWE-78 |
| Path traversal | CWE-22 |
| XSS | CWE-79 |
| Missing auth | CWE-306 |
| CORS misconfiguration | CWE-942 |
| SSRF | CWE-918 |
| IDOR | CWE-639 |
| JWT algorithm confusion | CWE-327 |
| Fail-open default | CWE-636 |
| Deserialization | CWE-502 |
| Prototype pollution | CWE-1321 |
| Prompt injection | CWE-77 (command) / no CWE yet |
| Reentrancy | SWC-107 |
| Access control (Solidity) | SWC-115 |

**CVSS 3.1 auto-calculation:**

| Factor | Heuristic |
|--------|-----------|
| Attack Vector (AV) | Network if web endpoint, Local if file-based |
| Attack Complexity (AC) | Low if no preconditions, High if chained |
| Privileges Required (PR) | None if unauth, Low if user-level, High if admin |
| User Interaction (UI) | None if server-side, Required if XSS/CSRF |
| Scope (S) | Changed if crosses trust boundary |
| Confidentiality (C) | High if data exposed, Low if metadata only |
| Integrity (I) | High if write access, Low if read-only |
| Availability (A) | High if DoS/data destruction possible |

### Step 3: Generate Report (1min)

Fill the platform template with:
1. Finding details from VIGIL audit
2. Enriched code context
3. Auto-calculated CWE and CVSS
4. Concrete reproduction steps (translate VIGIL tool commands to attacker steps)
5. Fix recommendation from fix-engine or manual analysis

### Step 4: Quality Check (30s)

Before outputting, verify:

- [ ] Title is specific (not "XSS vulnerability" — instead "Stored XSS in comment field via markdown parser")
- [ ] Steps to reproduce are executable by someone with no project knowledge
- [ ] Impact statement quantifies damage (users, data, dollars)
- [ ] CVSS vector matches the described attack scenario
- [ ] CWE is accurate for the vulnerability class
- [ ] Fix recommendation is actionable (not "validate input" — instead "add parameterized query")
- [ ] No internal tool output or VIGIL IDs leak into the submission
- [ ] Screenshot/PoC placeholders are clearly marked `[ATTACH: ...]`

### Step 5: Output

```
╔══════════════════════════════════════════════════════════╗
║  VIGIL Bounty Report — {platform} format                ║
╚══════════════════════════════════════════════════════════╝

{formatted report}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Checklist:
  ✓ CWE-{id} mapped
  ✓ CVSS {score} ({severity})
  ✓ {N} reproduction steps
  ✗ Screenshots needed: [ATTACH: ...]

Next: Review, add screenshots/PoC, submit to {platform}
```

## Bugcrowd VRT Severity Mapping

| VIGIL Severity | Bugcrowd Priority | Typical Range |
|----------------|-------------------|---------------|
| CRITICAL | P1 | $5,000-$50,000+ |
| HIGH | P2 | $1,500-$10,000 |
| MEDIUM | P3 | $500-$3,000 |
| LOW | P4 | $100-$500 |
| INFO | P5 | $0 (out of scope) |

## Duplicate Avoidance Tips

Include in report preamble (do NOT submit — these are internal notes):
1. Search program's disclosed reports for similar findings
2. Check if the component/endpoint was recently patched (git log)
3. If finding is in a dependency, check if upstream CVE already exists
4. For CORS/subdomain: verify the specific origin/subdomain hasn't been reported
5. Time-sensitive: submit within 24h of discovery for priority
