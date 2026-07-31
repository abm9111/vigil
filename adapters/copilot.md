# VIGIL Adapter: GitHub Copilot

**Purpose:** Instructions for using VIGIL methodology in GitHub Copilot Chat.

## Setup

Add to `.github/copilot-instructions.md`:

```markdown
## Code Review Standards — VIGIL

When reviewing code or PRs, apply VIGIL methodology:

### Finding Format
Every issue must include:
- ID: VIGIL-{CLUSTER}-{NNN}
- Severity: CRITICAL / HIGH / MEDIUM / LOW / INFO
- What: one-line description
- Where: file:line
- Fix: concrete remediation

### Severity Scale
- CRITICAL (25pts): Exploitable now — RCE, auth bypass, data exposure
- HIGH (10pts): Exploitable with effort — injection, missing auth
- MEDIUM (4pts): Defense gap — no rate limit, verbose errors
- LOW (1pt): Best practice — style, naming

### Clusters
Security (22%), Data (12%), API (10%), Infrastructure (10%), Code Health (8%), Performance (8%)

### Cross-Domain Check
After individual findings, check correlation patterns:
- 3+ findings on same endpoint → escalate severity
- Auth gap + raw SQL + PII table → always CRITICAL
- Injection in admin context → always CRITICAL
```

## Usage in Copilot Chat

- `/vigil` → "Review this code following VIGIL methodology"
- In PR review: "Apply VIGIL security audit to the changed files"
- In editor: "What VIGIL findings would you flag in this file?"

## Limitations

- No bash tool access (AI-only analysis)
- No scoring engine (manual calculation)
- No baseline tracking
- Best for PR review comments and inline suggestions
