# VIGIL Mode: Siege

**Time budget:** 20-30 minutes
**Depth:** Exhaustive adversarial — attack scenarios with blast radius
**Loads:** ALL clusters + ALL engines + ALL compliance maps + ALL domain details

## Execution

### Step 1: Full Audit (10-15min)

Run the complete audit mode pipeline (see [audit.md](audit.md)):
- All cluster audits with deterministic tools
- Cross-domain correlation
- Compliance mapping (all standards)
- Scoring

### Step 2: Attack Scenario Generation (5-10min)

For each CRITICAL and HIGH finding, plus each correlated finding:

Generate an **attack scenario** with this structure:

```
ATTACK SCENARIO: {name}
━━━━━━━━━━━━━━━━━━━━━
Triggered by: VIGIL-{ID} + VIGIL-{ID} (if correlated)

Preconditions:
  - {what attacker needs: network access, valid account, etc.}

Attack Steps:
  1. {concrete step with tool/technique}
  2. {next step}
  3. {exploitation/impact}

Blast Radius:
  - Data: {what data is exposed/corrupted}
  - Users: {who is affected, how many}
  - Systems: {what else is reachable from here}
  - Business: {regulatory, reputational, financial impact}

Exploitation Difficulty: {TRIVIAL | LOW | MODERATE | HIGH | EXPERT}
  Reasoning: {why this difficulty level}

CVSS 3.1 Vector: {if applicable}
CVSS Score: {if applicable}

Mitigation Priority: {IMMEDIATE | HIGH | MEDIUM}
Remediation:
  1. {specific fix with code}
  2. {defense-in-depth measure}
  3. {monitoring/detection to add}
```

### Step 3: Supply Chain Analysis (2-3min)

**Python:**
```bash
pip-audit --format=json 2>&1
# Parse for known CVEs, check if vulnerable function is actually called
```

**JavaScript:**
```bash
npm audit --json 2>&1
# Parse for known CVEs, check if vulnerable package is in dependency path
```

**For each CVE found:**
1. Check if the vulnerable function/module is actually imported
2. Check if the code path is reachable from external input
3. If reachable: CRITICAL. If imported but not reachable: HIGH. If not imported: LOW.

**The downgrade steps are fenced by [RULES.md](../RULES.md) Rule 7.** Siege is the adversarial
mode, so it is the likeliest place a reachability downgrade gets used — and the same ladder
without the fence is how the severity floor gets lifted quietly:

- A rating **below** the CVE's own severity requires **positive evidence of non-reachability**:
  the module and the call sites searched, named, and found absent. "No call was found" is not
  evidence of absence. An unsearched path is `NEEDS_REVIEW` at the CVE's own severity.
- The downgrade moves the **penalty and the fix order, never the severity floor**. The cap is
  computed from the constituent CVE's severity — reachability may reorder the work, it may not
  turn an unresolved HIGH into a pass.
- To lift the cap on a CVE you have decided to live with, suppress it explicitly, with owner
  and expiry, so it prints beside the grade. A quiet downgrade does not.

### Step 4: Configuration Hardening Review (2-3min)

Check all configuration files for security misconfigurations:

```bash
# CORS
grep -rn 'allow_origins.*\*\|Access-Control-Allow-Origin.*\*' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Debug mode
grep -rn 'DEBUG.*=.*[Tt]rue\|debug.*=.*[Tt]rue\|NODE_ENV.*development' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Default credentials
grep -rn 'admin.*admin\|password.*password\|changeme\|123456' . --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Exposed ports
grep -rn '0\.0\.0\.0\|EXPOSE\|ports:' Dockerfile* docker-compose* compose* 2>/dev/null
```

### Step 5: Adversarial AI Reasoning

After all deterministic tools have run, apply adversarial thinking:

1. **Assume breach:** If an attacker had access to {weakest point}, what's the worst case?
2. **Chain analysis:** Which findings, when combined, create escalation paths?
3. **Insider threat:** What could a malicious developer do with current permissions?
4. **Dependency risk:** What if the most critical dependency gets compromised?
5. **Data flow:** Trace sensitive data from input to storage — where are the gaps?

## Output Template

Includes full audit output PLUS:

```
━━━ ATTACK SCENARIOS ━━━

{numbered attack scenarios, highest severity first}

━━━ SUPPLY CHAIN ━━━

Dependencies: {total}
Known CVEs: {count} ({critical} critical, {high} high)
Reachable CVEs: {count} (exploitable in current code paths)

{table of reachable CVEs with package, version, CVE ID, fix version}

━━━ HARDENING CHECKLIST ━━━

☐ {specific hardening action}
☐ {specific hardening action}
☑ {already hardened — detected}
{...}

━━━ EXECUTIVE SUMMARY ━━━

Attack surface: {LOW | MODERATE | HIGH | CRITICAL}
Most critical path: {one-sentence description of worst attack chain}
Estimated fix effort: {hours/days for critical items}
```

## Rules for Siege Mode

- This is the MAXIMUM thoroughness mode — leave nothing unexamined
- Load ALL domain detail files for deep sub-domain checks
- Every attack scenario must be grounded in actual findings (not hypothetical)
- Exploitation difficulty must be realistic (not everything is "trivial")
- Include defensive measures already in place (credit what's done right)
- Time budget is 20-30 min but accuracy trumps speed
