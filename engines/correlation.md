# VIGIL Engine: Cross-Domain Correlation

Findings are correlated across security, API, data and infrastructure domains to surface
chains that per-domain tools report only as unrelated singletons. This is where most of the
value is: the constituents are often individually unremarkable.

## How It Works

1. Collect ALL findings from ALL clusters
2. For each correlation pattern, scan findings for trigger conditions
3. When triggered: create a correlated finding (VIGIL-CORR-xxx)
4. Correlated finding replaces its constituents in the report
5. Severity is escalated per pattern rules
6. Attack narrative is generated from the template

## The 10 Correlation Patterns

Patterns 1–7 are adversarial: an attacker chains weaknesses. Patterns 8–10 are non-adversarial:
no attacker is required, and the damage is done by someone acting in good faith on an artifact
that quietly lied. Both kinds ship real incidents. Scan for both.

### 1. ENDPOINT_STACK

**Trigger:** 3+ findings referencing the same endpoint/route
**Escalation:** Max severity of constituents + 1 level (MEDIUM→HIGH, HIGH→CRITICAL)
**Logic:**
```
Group all findings by endpoint (extract from file:line → route mapping)
For each endpoint with 3+ findings:
  Create VIGIL-CORR-xxx
  Severity = max(constituent severities) + 1 (cap at CRITICAL)
```
**Narrative template:**
> Endpoint `{route}` has {N} independent findings spanning {clusters}. Combined attack surface exceeds individual risk: {constituent_summary}.

**Compliance:** SOC2:CC7.2 (monitoring), OWASP:A04 (insecure design)

### 2. DATA_EXPOSURE_CHAIN

**Trigger:** ALL of: (auth gap on endpoint) + (raw SQL or ORM bypass) + (PII in response/table)
**Escalation:** Always CRITICAL regardless of constituent severities
**Logic:**
```
Find: SEC finding with "auth" or "authentication" or "authorization"
AND:  DATA finding with "SQL" or "injection" or "raw query"
AND:  (API finding with "PII" or "email" or "phone" or "SSN")
      OR (DATA finding referencing user/customer/patient table)
If all three present on overlapping code paths → CRITICAL
```
**Narrative template:**
> Complete data exposure chain: missing authentication on `{endpoint}` allows unauthenticated access to raw SQL query in `{file}:{line}` which returns PII ({pii_types}) from `{table}`. An attacker can exfiltrate {scope} with zero credentials.

**Compliance:** SOC2:CC6.1 (access control), ISO27001:A.8.11 (data masking), OWASP:A01 (broken access control)

### 3. INJECTION_WITH_PRIVILEGE

**Trigger:** Injection finding (SQL/command/template) + elevated context (admin route, root process, service account)
**Escalation:** Always CRITICAL
**Logic:**
```
Find: SEC finding with "injection" (SQL, command, template, LDAP)
AND:  Context is privileged:
      - Route contains "admin" or "manage" or "internal"
      - Process runs as root (Dockerfile USER check)
      - Uses service account or elevated DB role
If injection + privilege → CRITICAL
```
**Narrative template:**
> {injection_type} injection in privileged context: `{file}:{line}` executes in `{privilege_context}`. Successful exploitation grants {impact}: {specific_capability}.

**Compliance:** SOC2:CC6.3 (least privilege), OWASP:A03 (injection)

### 4. OBSERVABILITY_BLINDSPOT

**Trigger:** Security-relevant event + no logging/monitoring for that event type
**Escalation:** Constituent severity + 1 level
**Logic:**
```
Find: Any SEC or DATA finding involving auth, access control, or data modification
Check: Is there logging for this event type?
  - Search for logger/logging calls near the finding location
  - Check for audit trail middleware
  - Check for monitoring/alerting config
If security event + no logging → escalate
```
**Narrative template:**
> Security event at `{file}:{line}` ({event_type}) has no logging or monitoring. An attacker exploiting {finding_id} would leave no trace. Detection time: potentially infinite.

**Compliance:** SOC2:CC7.2 (system monitoring), ISO27001:A.8.15 (logging)

### 5. DEPENDENCY_AND_REACHABILITY

**Trigger:** Known CVE in dependency + vulnerable function is actually called in codebase
**Escalation:** CVE severity; +1 when directly reachable from external input; and — uniquely
among these patterns — *below* CVE severity when non-reachability is positively established.
The two downgrade rows below are fenced by the rule that follows the logic block.
**Logic:**
```
Find: SEC finding from pip-audit/npm-audit with CVE
For each CVE:
  1. Identify vulnerable function/module from CVE advisory
  2. Grep codebase for import/require of that module
  3. If imported: check if vulnerable function is called
  4. If called: check if reachable from external input (HTTP handler, CLI arg, file read)
  Reachable from external input → CRITICAL
  Called but not externally reachable → HIGH
  Imported but function not called → MEDIUM     ← downgrade: evidence required
  Not imported → LOW (transitive only)          ← downgrade: evidence required
```

**Those last two rows are the only place this engine lowers a severity, and they are fenced.**
Severity floors read the correlated severity ([engines/scoring.md](scoring.md)), so an
ungoverned downgrade means a HIGH CVE absorbed into a LOW correlation lifts the 79 cap and
turns a 10-point penalty into 1 — an auditor would score better by correlating more.

- **Positive evidence, or no downgrade.** Name the module grepped for, the call sites
  enumerated, and what came back empty. An empty grep is a tooling result, not a finding: it is
  evidence of absence only once you have shown the search could have found the thing. Dynamic
  import, `getattr`, plugin registries and framework autoloading all defeat it — where any of
  those are in play the reachability claim is unproven and the finding stays at CVE severity as
  NEEDS_REVIEW.
- **A downgrade moves the penalty and the fix order, never the floor.** The cap is still
  computed from the constituent CVE's severity — see [RULES.md](../RULES.md), Rule 7. To lift
  the cap on a CVE you have decided to live with, suppress it explicitly; that prints beside
  the grade, where a reviewer sees it.

**Narrative template:**
> CVE-{id} in `{package}@{version}`: vulnerable function `{function}` is {reachability} in `{file}:{line}`. {cve_description}. Upgrade to `{fixed_version}`.

**Compliance:** SOC2:CC7.1 (vulnerability management), OWASP:A06 (vulnerable components)

### 6. CONFIG_SECRET_EXPOSURE

**Trigger:** Secret/credential in file + that file is deployed/committed/exposed
**Escalation:** Always CRITICAL
**Logic:**
```
Find: SEC finding with "secret" or "credential" or "key" or "token" or "password"
Check deployment exposure:
  - Is file in git history? (git log --all -- {file})
  - Is file in Docker image? (not in .dockerignore)
  - Is file served by web server? (in static/ or public/ dir)
  - Is file in CI logs? (echo/print of secret variable)
If secret + any exposure vector → CRITICAL
```
**Narrative template:**
> Secret `{secret_type}` in `{file}:{line}` is exposed via {exposure_vector}. {specific_risk}. Rotate immediately and {remediation}.

**Compliance:** SOC2:CC6.1, ISO27001:A.8.9 (configuration management), OWASP:A02 (cryptographic failures)

### 7. AUTH_BYPASS_WITH_SCOPE

**Trigger:** Missing/broken auth + endpoint accesses admin data or performs admin action
**Escalation:** Always CRITICAL
**Logic:**
```
Find: SEC finding with missing auth (no @login_required, no JWT check, no middleware)
AND: Endpoint accesses:
  - Admin/management functionality (user CRUD, config, system settings)
  - Sensitive data (financial, health, PII)
  - Destructive operations (DELETE, bulk update, data export)
If missing auth + sensitive scope → CRITICAL
```
**Narrative template:**
> Endpoint `{route}` performs `{action}` on `{data_scope}` with no authentication. Any network-reachable client can {impact}. This is a complete authorization bypass.

**Compliance:** SOC2:CC6.1, ISO27001:A.8.3 (access restriction), OWASP:A01

### 8. TRUST_LAUNDERING

**Trigger:** Unverified/machine-generated content + authoritative presentation + crosses a trust boundary
**Escalation:** Constituent max + 1 level; always ≥ HIGH when the boundary is organisational
**Logic:**
```
Find: EGRESS or AIML finding — content generated by a model, scraped, inferred, or synthetic
AND:  Presentation is authoritative:
      - Natural-language prose (summary/description/advice/recommendation fields)
      - Sits in the same schema as source-of-truth columns, unlabelled
      - Rendered in the consumer's language or the source org's voice
AND:  It crosses a boundary:
      - Shipped to another org, published, or exported to a separate system
      - Consumed by a downstream pipeline that cannot re-check it
If all three → TRUST_LAUNDERING
```
**Narrative template:**
> `{field}` ({row_count} rows) is {generation_method} output, not {authority} data, and is
> presented identically to the {authority}-sourced columns beside it. It leaves via
> {boundary}. A reader has no way to tell the generated content from the sourced content,
> and {consequence}.

**Why it escalates:** each part is benign alone. Model output is fine when labelled; an export
is fine when its contents are known; prose is fine when its author is clear. Combined, the
artifact launders unverified content into apparent authority — and the boundary crossing means
nobody downstream can undo it.

**Compliance:** SOC2:CC7.1 (accuracy of information), ISO27001:A.5.34 (privacy & PII), EU AI Act Art.50 (transparency of AI-generated content)

### 9. DESTRUCTIVE_BEFORE_VALIDATE

**Trigger:** Irreversible operation ordered before the validation that would abort it
**Escalation:** Always ≥ HIGH; CRITICAL when the target is the only copy
**Logic:**
```
Find: any irreversible call — rmtree, unlink, DROP, TRUNCATE, overwrite, force-push, migrate
For each, read the enclosing function and compare statement order against:
  - input reads that can raise (file open, network fetch, parse)
  - validation/gate calls
  - schema or precondition checks
If the destructive statement precedes any of them → fires.
Confirm empirically where possible: remove an input, run, check whether the prior
artifact survived. A demonstrated failure outranks a read of the source.
```
**Narrative template:**
> `{file}:{destructive_line}` destroys `{target}` before `{file}:{validate_line}` can fail.
> A run that aborts for any reason — missing input, schema drift, disk error — leaves
> {end_state}. Demonstrated: {evidence}.

**Fix shape:** build into a staging path, validate, then swap. Never mutate the live target
before every failure mode has had its chance to fire.

**Compliance:** SOC2:A1.2 (availability/backup), ISO27001:A.8.13 (information backup)

### 10. INTEGRITY_THEATER

**Trigger:** An integrity control exists but cannot establish what it claims
**Escalation:** Constituent max + 1 level — a false assurance is worse than none, because it
stops anyone from looking
**Logic:**
```
Find: any integrity mechanism — checksum, manifest, signature, audit log, backup verification
Then test whether it can actually fail:
  - Self-certifying? (manifest ships inside the archive it certifies; log written to the
    host it audits; backup verified by the system being backed up)
  - Is the input reproducible? A checksum over a non-deterministic build cannot
    distinguish tampering from a rebuild
  - Is the reference value transmitted on the same channel as the artifact?
  - Has anyone verified it end-to-end, or only generated it?
If the control cannot distinguish a good artifact from a bad one → fires.
```
**Narrative template:**
> {control} at `{location}` cannot detect {threat}: {reason}. It produces the appearance of
> verification without the property. {who} will treat {artifact} as verified when it is not.

**Compliance:** SOC2:CC7.2 (monitoring), ISO27001:A.8.16 (monitoring activities), NIST SSDF PS.2 (verify software integrity)

## Correlated Finding Format

```
VIGIL-CORR-{NNN}  {SEVERITY}  [{pattern_name}]
  Narrative: {attack_narrative}
  Contributing:
    ├─ VIGIL-{cluster}-{nnn}  {description}  {file:line}
    ├─ VIGIL-{cluster}-{nnn}  {description}  {file:line}
    └─ VIGIL-{cluster}-{nnn}  {description}  {file:line}
  Compliance: {mapped_controls}
  Fix Priority: {IMMEDIATE | HIGH | MEDIUM}
  Remediation:
    1. {most impactful fix first}
    2. {defense in depth}
```

## Implementation Notes

- Run correlation AFTER all clusters complete (needs full finding set)
- Correlated findings get their own ID namespace (VIGIL-CORR-*)
- Constituent findings are REMOVED from per-cluster sections to avoid double-counting
- Scoring uses correlated severity, not sum of constituents
- `--ignore` means three different things depending on what is named, and only two of them
  change anything. State which one applied:
  - **A plain finding** — hidden from the report and excluded from scoring per
    [FLAGS.md](../FLAGS.md), and listed in the suppression ledger.
  - **A constituent of a correlation** — the correlation still fires (ignore applies to
    output, not to correlation input) and still charges its escalated penalty. The constituent
    was already replaced by the CORR, so the flag changes no output and no score: it is a
    no-op. Print it as one — `no effect: absorbed into VIGIL-CORR-xxx; ignore the CORR to act
    on the chain` — because otherwise the user sees a flag accepted, a grade that does not
    move, and nothing anywhere telling them whether the tool dropped the flag or the flag did
    nothing.
  - **The CORR itself** — restores its constituents, per the last note below.
- Every correlated finding is assigned a **primary cluster** and its penalty is charged there —
  see [engines/scoring.md](scoring.md). Without that, correlating findings raises the average
  by deleting them from their clusters.
- **Ignoring a CORR restores its constituents** to the report and to scoring at their original
  severities. Otherwise one `--ignore` erases several findings at once and lifts the severity
  floor. Ignoring a correlation is a statement about the link, never about the findings.
