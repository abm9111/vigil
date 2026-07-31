# VIGIL Compliance Map: SOC2 Type II

**Standard:** AICPA SOC 2 Trust Services Criteria (2017)
**Purpose:** Map VIGIL findings to SOC2 controls for audit preparation

## Trust Services Criteria → VIGIL Mapping

### CC1 — Control Environment

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC1.1 | Integrity and ethical values | COMP | Code of conduct, CONTRIBUTING.md |
| CC1.2 | Board oversight | COMP | Governance documentation |
| CC1.3 | Management structure | COMP | CODEOWNERS, team access controls |
| CC1.4 | Competence commitment | CODE | Code review process, test coverage |
| CC1.5 | Accountability | INFRA | Audit logging, git blame |

### CC2 — Communication and Information

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC2.1 | Information quality | COMP, DATA | Data validation, schema enforcement |
| CC2.2 | Internal communication | COMP | README, ADRs, documentation |
| CC2.3 | External communication | API, COMP | API docs, status page, SECURITY.md |

### CC3 — Risk Assessment

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC3.1 | Risk objectives | SEC | Threat model documentation |
| CC3.2 | Risk identification | SEC, INFRA | Dependency scanning, SAST |
| CC3.3 | Fraud risk | SEC | Auth controls, audit trail |
| CC3.4 | Change risk | INFRA | CI/CD pipeline, change management |

### CC4 — Monitoring Activities

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC4.1 | Monitoring controls | INFRA | Health checks, alerting, dashboards |
| CC4.2 | Deficiency remediation | CODE | Issue tracking, SLA on fixes |

### CC5 — Control Activities

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC5.1 | Risk mitigation | SEC | Security controls implementation |
| CC5.2 | Technology controls | SEC, INFRA | Firewall, WAF, encryption |
| CC5.3 | Policy enforcement | INFRA | CI gates, branch protection |

### CC6 — Logical and Physical Access

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC6.1 | Access control | SEC | Auth on all endpoints, RBAC |
| CC6.2 | Access provisioning | SEC | User management, API key management |
| CC6.3 | Least privilege | SEC, DATA | Role-based access, DB permissions |
| CC6.4 | Access review | SEC | User audit, permission review |
| CC6.5 | Access revocation | SEC | Token expiry, session management |
| CC6.6 | Authentication | SEC | MFA, password policy, JWT |
| CC6.7 | Encryption | SEC, DATA | TLS, encryption at rest, key management |
| CC6.8 | Transmission security | SEC, API | HTTPS enforcement, certificate validation |

### CC7 — System Operations

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC7.1 | Vulnerability management | SEC | Dependency scanning, CVE tracking |
| CC7.2 | System monitoring | INFRA | Logging, alerting, intrusion detection |
| CC7.3 | Change management | INFRA | CI/CD, code review, deployment process |
| CC7.4 | Incident response | COMP | SECURITY.md, incident playbook |
| CC7.5 | Recovery procedures | DATA, INFRA | Backup, DR plan, rollback |

### CC8 — Change Management

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC8.1 | Change authorization | INFRA | PR approval, branch protection |

### A1 — Availability

The Availability category is optional in a SOC2 engagement, but when it is in scope these are
the criteria VIGIL can evidence. A1.2 is what `DESTRUCTIVE_BEFORE_VALIDATE` maps to: a build
that destroys the previous good artifact before validating its inputs has no recovery path.

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| A1.1 | Capacity management | PERF, INFRA | Resource limits, autoscaling, load headroom |
| A1.2 | Environmental protections, backup, recovery | INFRA, EGRESS | Backups exist and restore; destructive operations do not precede validation; last-known-good artifact survives a failed build |
| A1.3 | Recovery testing | INFRA | Restore drills, DR runbook exercised |

### CC9 — Risk Mitigation

| Control | Description | VIGIL Clusters | Check |
|---------|-------------|----------------|-------|
| CC9.1 | Vendor risk | SEC | Third-party dependency assessment |
| CC9.2 | Business continuity | INFRA | HA, failover, backup |

## Gap Analysis Template

```
SOC2 Compliance Gap Analysis — {project}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Mapped: {N}/{total} controls have evidence
Gaps: {M} controls with no evidence

CRITICAL GAPS (audit will fail):
  CC6.1 — No authentication on 5/12 endpoints
  CC6.7 — No encryption at rest for user data
  CC7.1 — No dependency vulnerability scanning in CI

HIGH GAPS (auditor will question):
  CC4.1 — No monitoring/alerting configured
  CC7.4 — No incident response documentation

PARTIAL (evidence exists but incomplete):
  CC5.3 — CI pipeline exists but no security gates
  CC7.2 — Logging exists but no centralized aggregation
```
