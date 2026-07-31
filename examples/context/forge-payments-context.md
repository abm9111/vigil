# VIGIL Context — Forge (B2B Payments Platform)

**Last updated:** 2026-05-26  
**Project type:** B2B SaaS — Embedded invoicing, payouts, and tax compliance infrastructure  
**Stage:** Series C (~180 engineers)  
**Primary compliance regimes:** SOC 2 Type II, PCI-DSS SAQ-D

---

## Business Risk Model

- Payout authorization engine is **EXISTENTIAL**. Incorrect or bypassed authorization logic can cause direct financial loss and regulatory exposure.
- Fraud rule configuration and enforcement is **EXISTENTIAL**. Weakening or bypassing these rules has led to material losses at peer companies.
- Tax reporting and remittance logic is **HIGH_BUSINESS_IMPACT**. Errors here trigger state-level penalties and customer trust damage.
- Customer data isolation (especially between connected accounts) is **REGULATORY_MUST** under SOC 2 CC6.1 and CC6.6.

## Domain Profiles

- regulated-payments
- hybrid-legacy-migration
- high-stakes-ecommerce

## Architecture Reality

- The legacy Ruby on Rails monolith ("Core") remains the system of record for payout authorization, fraud rules, and tax configuration as of May 2026.
- A "Strangler Fig" migration is in progress. Roughly 35% of financial transaction volume has been moved to the new Go + Temporal services.
- Several critical compliance checks still execute only inside the Rails monolith and are called via internal HTTP from the new stack.
- The new stack has better observability, but the authoritative policy decisions still live in the older codebase.

## Critical Paths

1. Payout Authorization (Rails Core) → Fraud Rules Engine → Bank Transfer Initiation
2. Customer onboarding → KYC/AML service → Account activation + payout capability
3. Tax configuration changes → Rule evaluation → Report generation for customers and tax authorities
4. Internal admin tools that can override fraud rules or payout holds

## Accepted Risks

- The Rails monolith contains multiple large, low-test-coverage modules related to legacy tax logic. This is accepted until the end of the migration (target Q4 2027).
- Direct database access from a small number of internal tools into the Core database is still used for emergency operations. Mitigated by strict access controls and audit logging.

## Custom Escalation Rules

- Any finding that touches payout authorization logic, fraud rule evaluation, or tax remittance must be treated as at least HIGH, regardless of technical severity.
- Findings in the legacy Rails monolith that affect financial transaction flows receive +1 severity escalation during correlation.
- Deprecated code paths that are still reachable from the new stack and touch money movement must not be treated as LOW.