# VIGIL Engine: Context Loader

**Status:** Phase 2 implementation  
**Version:** 1.0 (May 2026)  
**Style:** Strict Claude-style skill instructions

---

## Purpose

This engine defines the **mandatory procedure** any VIGIL auditor must follow when a project provides a context file (`.vigil/context.md` or `vigil-context.json`).

The goal is to turn project-specific business context into enforceable signals that affect scoring, severity, correlation, and reporting.

Context is **not optional flavor text**. When present, it is evidence that must be loaded, validated, and applied.

---

## Discovery Rules

The auditor **must** check for context in this exact order:

1. `.vigil/context.md`
2. `.vigil/context.json`
3. `vigil-context.md` (root)
4. `vigil-context.json` (root)

**Rules:**
- If **both** a `.md` and `.json` file exist in the same location, prefer the `.md` version unless the JSON has a newer `last_updated` timestamp.
- If no context file is found after checking the above locations, record `context_loaded: false` and continue in generic mode.
- The auditor must explicitly state in the report whether context was loaded or not.

**Never** skip discovery because "the project looks simple" or "we already know the codebase."

---

## Supported Formats & Parsing Requirements

### Markdown Format (`.md`)

- The file must use clear section headings (`##`).
- The auditor must extract the following sections if present (case-insensitive matching on headings is allowed):
  - `Business Risk Model`
  - `Domain Profiles`
  - `Architecture Reality`
  - `Critical Paths`
  - `Accepted Risks`
  - `Custom Escalation Rules`

**Parsing rules for Markdown:**
- Lines containing `**EXISTENTIAL**`, `**HIGH_BUSINESS_IMPACT**`, or `**REGULATORY_MUST**` must be captured with the associated control name.
- Numbered lists under `Critical Paths` must be captured in order.
- Domain profiles must be extracted as a list (bullet points or comma-separated).

### JSON Format (`.json`)

The auditor must validate that the file contains at least one of these top-level keys:
- `business_risk_model`
- `domain_profiles`
- `critical_paths`
- `architecture_reality`

If the JSON is invalid or does not contain any recognized keys, treat it as a parsing failure (see Error Handling).

---

## Mandatory Execution Steps

The auditor **must** execute these steps in order when a context file is discovered. Do not skip or reorder.

### Step 1: Load and Validate
- Read the file.
- Confirm it is not empty.
- For JSON: Attempt to parse. If parsing fails → Error Handling path.
- Record the file path and last modified time (if available) in internal state.

### Step 2: Extract Structured Data
The auditor must populate the following internal structure (even if some fields are empty):

```json
{
  "source_file": "string",
  "format": "markdown | json",
  "controls": [
    {
      "name": "string",
      "criticality": "EXISTENTIAL | HIGH_BUSINESS_IMPACT | REGULATORY_MUST",
      "reason": "string"
    }
  ],
  "domain_profiles": ["string"],
  "critical_paths": ["string"],
  "architecture_notes": ["string"],
  "accepted_risks": ["string"],
  "custom_rules": ["string"]
}
```

### Step 3: Apply to Scoring
- Pass the extracted `controls` to the scoring engine.
- Any finding that touches a control marked `EXISTENTIAL` **must** be escalated one severity
  level, and the report must say why ("escalated: touches the declared EXISTENTIAL control
  <name>"). This is an ordinary severity change and flows through the normal penalty table in
  [engines/scoring.md](scoring.md) — there is no separate bonus arithmetic. Do not invent a
  numeric adjustment; if you find yourself computing one, the rule is the escalation above.
- Apply domain profile weight shifts if any recognized profiles are listed.

### Step 4: Apply to Correlation
- Pass the following structure to the correlation engine. There is no separate context-aware
  correlation mode: declared critical paths act as an additional grouping key for the existing
  patterns in [engines/correlation.md](correlation.md), and a correlation spanning a declared
  critical path escalates one level under that file's normal escalation rules.
  - `critical_paths`
  - `existential_controls` (controls marked EXISTENTIAL)
  - `high_impact_controls`
  - `architecture_notes`
- Findings clustering on one declared critical path are strong candidates for pattern 1
  (`ENDPOINT_STACK`), with the path in place of the route. **There is no
  `BUSINESS_CONTROL_CONCENTRATION` pattern** — an earlier draft named one that was never
  written. Ten patterns exist; use them.
- Any finding that intersects with a declared Critical Path or EXISTENTIAL control must be considered for escalation.

### Step 5: Record Influence
The auditor must maintain a log of every decision influenced by context (for the final report).

---

## Error Handling & Edge Cases

| Situation                              | Required Behavior                                      | Severity Impact |
|----------------------------------------|--------------------------------------------------------|-----------------|
| Context file exists but is empty       | Log warning. Proceed in generic mode.                  | None |
| JSON is malformed                      | Log error + continue in generic mode. Do **not** guess. | Record in report |
| Conflicting criticality declarations   | Prefer the highest criticality. Document the conflict. | Escalate the conflict as LOW in Compliance cluster |
| Context claims something is EXISTENTIAL but no code touches it | Still record the claim. Do not invent findings.       | None |
| Context file is present but appears outdated | Load it anyway. Note the staleness in the report.     | None |
| Context contradicts strong mechanical findings | Report both. Never suppress mechanical findings to "respect" context. | Document tension |

**Golden Rule:** Context can escalate risk. It cannot be used to hide or downgrade clear
mechanical problems.

This is consistent with the cap-lifting behaviour in
[engines/scoring.md](scoring.md): an accepted risk is still **reported in full at its
mechanical severity** — acceptance changes only whether it holds the severity floor down, and
only when it carries an owner and an expiry. Nothing here permits deleting or downgrading a
finding. If `accepted_risks` is present without owner and expiry, ignore it.

---

## Reporting Obligations

When context was loaded, the final report **must** contain a section titled:

**Context Influence**

This section must include at minimum:

- File loaded and format
- Domain profiles activated
- Controls declared as EXISTENTIAL or HIGH_BUSINESS_IMPACT
- Number of findings whose severity or score was adjusted because of context
- Any Critical Paths that caused escalation during correlation
- A short summary of how context changed the overall risk picture (1-3 sentences)

If no context file was found, the report must explicitly state:

> No VIGIL context file was present. Audit ran in generic mode.

---

## Integration Points

This engine is called early and feeds two other engines:

- `engines/scoring.md` — receives control criticality and domain profiles
- `engines/correlation.md` — receives critical paths and high-criticality controls (Phase 2+)

The context loader must finish before any cluster begins execution.

---

## Auditor Checklist (Mandatory)

Before finishing any audit where a context file existed, the auditor must be able to answer "Yes" to all of the following:

- [ ] Did I discover the context file using the exact priority order?
- [ ] Did I successfully parse it without guessing?
- [ ] Did I extract controls, profiles, and critical paths into the required structure?
- [ ] Did I pass the relevant data to scoring and correlation?
- [ ] Did I record every escalation or weight change caused by context?
- [ ] Is the "Context Influence" section present and accurate in the final report?
- [ ] Did I follow the golden rule (context can escalate, never hide mechanical findings)?

If the answer to any item is "No", the audit is incomplete.

---

## Future Extensions (Not Yet Implemented)

- Organization-level default context files
- Context versioning and diffing between audits
- Automatic suggestions for missing context sections
- Machine-readable context validation tool (outside current scope)

---

**This engine is now active.** Any run of `/vigil audit`, `/vigil siege`, or `/vigil score` that encounters a context file must follow the procedure defined here.