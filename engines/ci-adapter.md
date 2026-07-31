# VIGIL Engine: CI Adapter

**Purpose:** Machine-readable output for CI/CD pipelines with deterministic exit codes.

## Exit Codes

| Code | Meaning | When |
|------|---------|------|
| 0 | Pass | Nothing at or above the blocking severity **and** no cluster is N/E |
| 1 | Fail | CRITICAL or HIGH findings present (or MEDIUM+ with --strict) |
| 2 | Error | Tool execution failed, configuration error, **or an applicable cluster had no evidence (N/E)** |

The **blocking severity** is HIGH, or MEDIUM under `--strict`. It is not the `--threshold` flag,
which only filters what gets printed: hiding a HIGH from the report does not turn exit 1 into
exit 0. Two unrelated meanings of one word, kept apart deliberately.

### Evidence gating — exit 0 requires having looked

Per [engines/scoring.md](scoring.md), a cluster whose required tools were all unavailable is
**N/E**, not 100. A green pipeline must never mean "the scanner was missing."

```
if any(cluster.state == "N/E" for cluster in applicable):
    emit_capability_report()      # which tools, which cluster, install commands
    exit(2)                       # NOT 0 — this is an error, not a pass
```

This is stricter than it looks, and deliberately so: a CI job whose security scanner silently
vanished after a base-image change will otherwise go green forever. Exit 2 forces someone to
look. To run anyway, the operator must explicitly narrow scope with `--only` — but a command
line is not an artifact. The reduced coverage is a recorded decision only once it reaches the
machine output, which is why `scope` is a required field below.

**Partial evidence** (some required tools missing, cluster ceiling 85) does not gate the exit
code — it caps the score and appears in the capability report. Only *zero* evidence is fatal.

**Relationship to rule 5 below:** rule 5 covers a tool that ran and crashed. This covers a tool
that was never there. Both exit 2; both must name the tool.

## Output Formats

### SARIF 2.1.0 (Default for --ci)

GitHub Code Scanning, Azure DevOps, and many CI tools consume SARIF natively.

```json
{
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/main/sarif-2.1/schema/sarif-schema-2.1.0.json",
  "version": "2.1.0",
  "runs": [{
    "tool": {
      "driver": {
        "name": "VIGIL",
        "version": "0.4.0",
        "informationUri": "https://vigil.example/",
        "rules": [
          {
            "id": "VIGIL-SEC-001",
            "name": "HardcodedCredential",
            "shortDescription": { "text": "Hardcoded API key in source" },
            "defaultConfiguration": { "level": "error" },
            "properties": { "tags": ["security", "CWE-798"] }
          }
        ]
      }
    },
    "results": [
      {
        "ruleId": "VIGIL-SEC-001",
        "level": "error",
        "message": { "text": "Hardcoded API key found" },
        "locations": [{
          "physicalLocation": {
            "artifactLocation": { "uri": "config.py" },
            "region": { "startLine": 23, "startColumn": 1 }
          }
        }],
        "properties": {
          "vigil_cluster": "security",
          "vigil_severity": "HIGH",
          "compliance": ["SOC2:CC6.1", "OWASP:A02"]
        }
      }
    ],
    "invocations": [{
      "executionSuccessful": true,
      "properties": {
        "overall_score": 74,
        "overall_grade": "C",
        "scope": {
          "audited": ["security", "code-health"],
          "not_applicable": { "blockchain": "no *.sol, no foundry.toml, no Anchor.toml" },
          "no_evidence": {},
          "out_of_scope": ["api", "data", "infra", "frontend", "performance",
                           "compliance", "ai-ml", "egress"]
        },
        "suppressions": [
          {
            "id": "VIGIL-SEC-004",
            "severity": "HIGH",
            "authority": "--ignore on the command line",
            "owner": null,
            "expires": null
          },
          {
            "id": "VIGIL-DATA-009",
            "severity": "MEDIUM",
            "authority": ".vigil/context.md risk acceptance",
            "owner": "platform",
            "expires": "2026-09-30"
          }
        ]
      }
    }]
  }]
}
```

### JSON (--format json)

Simpler format for custom integrations:

```json
{
  "vigil_version": "0.4.0",
  "timestamp": "2026-03-27T10:30:00Z",
  "commit": "abc1234",
  "mode": "watch",
  "overall": { "score": 74, "grade": "C", "production_ready": false },
  "clusters": {
    "security": { "score": 65, "grade": "D", "finding_count": 8 }
  },
  "scope": {
    "audited": ["security", "code-health"],
    "not_applicable": { "blockchain": "no *.sol, no foundry.toml, no Anchor.toml" },
    "no_evidence": {},
    "out_of_scope": ["api", "data", "infra", "frontend", "performance",
                     "compliance", "ai-ml", "egress"]
  },
  "suppressions": [
    {
      "id": "VIGIL-SEC-004",
      "severity": "HIGH",
      "authority": "--ignore on the command line",
      "owner": null,
      "expires": null
    }
  ],
  "findings": [
    {
      "id": "VIGIL-SEC-001",
      "cluster": "security",
      "severity": "HIGH",
      "title": "Hardcoded API key",
      "description": "API key found in config.py:23",
      "file": "config.py",
      "line": 23,
      "fix_type": "manual",
      "compliance": ["SOC2:CC6.1", "OWASP:A02"],
      "correlated_by": null
    }
  ],
  "correlated_findings": [],
  "verdict": "FAIL",
  "exit_code": 1
}
```

## Scope and suppressions belong in the artifact

`--ci` output is what the pipeline keeps; the terminal transcript is discarded. Anything the
human report must print beside the grade therefore has to survive into the machine artifact, or
`--ci` becomes the one mode in which the safeguards quietly do not apply.

Two fields are **REQUIRED whenever non-empty** — in SARIF under `invocations[].properties`, and
at the top level in `--format json`:

**`suppressions`** — every finding hidden by `--ignore`, `.vigil/ignore`, or a context-file
acceptance, each with its authority, owner, and expiry. Without it, a committed `.vigil/ignore`
plus `watch --ci` gives exit 0 and a green badge while the hidden HIGH is recorded nowhere.

**`scope`** — which clusters were audited, which are N/A, which are N/E, and which were never
loaded. Without it, `--only security` and a full audit render as the same green badge.

The suppression rules in [engines/scoring.md](scoring.md) carry over unchanged, because this is
that ledger serialised: a suppressed CRITICAL or HIGH lifts the cap but never disappears, and a
suppression that cannot be listed must not be applied.

**Exiting 0 with suppressions active also warns on stderr**, naming the count and the IDs:

```
vigil: exit 0 with 2 finding(s) suppressed — VIGIL-SEC-004 (HIGH), VIGIL-DATA-009 (MEDIUM)
```

stderr, not stdout, so the warning cannot corrupt SARIF or JSON being redirected to a file. It
exists because an artifact is usually opened only once something already looks wrong; the
operator who never opens it still sees this line in the job log.

## CI Pipeline Integration

### GitHub Actions

```yaml
- name: VIGIL Audit
  run: |
    # Claude Code runs /vigil watch --ci --fix
    # Parse exit code
    claude --print "/vigil watch --ci --fix --format sarif > vigil-results.sarif"
  continue-on-error: true

- name: Upload SARIF
  uses: github/codeql-action/upload-sarif@v3
  with:
    sarif_file: vigil-results.sarif
```

### GitLab CI

```yaml
vigil:
  script:
    - claude --print "/vigil watch --ci --strict"
  allow_failure: false
  artifacts:
    reports:
      sast: vigil-results.json
```

### Pre-Commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit
claude --print "/vigil watch --ci" > /dev/null 2>&1
exit $?
```

## Severity to SARIF Level Mapping

| VIGIL Severity | SARIF Level | GitHub Display |
|---------------|-------------|----------------|
| CRITICAL | error | Error |
| HIGH | error | Error |
| MEDIUM | warning | Warning |
| LOW | note | Note |
| INFO | none | (hidden) |

## CI-Specific Behavior

When `--ci` is active:
1. **No color codes** in output (TTY detection)
2. **No progress indicators** (spinners, bars)
3. **No AI commentary** — no narrative around the findings. This is not licence to drop the
   `scope` block, the `suppressions` array, or the capability report: those record what the run
   did and did not look at, and without them a green badge cannot be checked against anything
4. **Deterministic output** — same input always produces same output (no timestamps in findings)
5. **Strict tool failure handling** — if ANY tool fails to execute, exit 2
6. **No interactive prompts** — `--fix` applies only auto-fixable, skips confirm category
