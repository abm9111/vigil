# VIGIL Context — [Project / Company Name]

> **Instructions:** Fill this out honestly. The more precise you are, the more dangerous (and useful) the VIGIL audit becomes. Delete sections you don't need. Commit this file.

---

## Business Risk Model

List the controls or areas that are unusually important for *this* business. Use one of these tags:

- **EXISTENTIAL** — Failure here can kill or severely damage the company (regulatory termination, major lawsuits, loss of payment processing, etc.)
- **HIGH_BUSINESS_IMPACT** — Significant revenue, legal, operational, or reputational damage
- **REGULATORY_MUST** — Direct compliance obligation with real consequences

Examples:

- Account-suspension enforcement is **EXISTENTIAL** because re-entry creates processor risk and legal exposure.
- Real-time card-network brand-risk programs compliance on all customer-facing and payment surfaces is **EXISTENTIAL**.
- Payment name sanitization on every order path (WP + Next.js) is **CRITICAL**.

---

## Domain Profiles

Activate any that apply (you can combine them):

- `regulated-payments`
- `brand-risk-sensitive`
- `hybrid-legacy-migration`
- `ai-heavy` (heavy LLM/chat/tool usage with output controls)
- `high-stakes-ecommerce`
- `dual-backend`
- Custom: `your-custom-profile`

---

## Architecture Reality

Document the uncomfortable truths that generic scanners will miss:

- The authoritative source of truth for [entitlements / compliance / X] still lives in the legacy [system].
- After the [migration / cutover], several cross-system calls and webhooks still point at the old [host].
- A single [N]-line file holds most of the [payment / auth / compliance] enforcement logic.
- [Other real architectural constraints]

---

## Critical Paths

List the actual flows that protect revenue, compliance, or customer trust. Number them.

1. Ban Check (live endpoint + daily sync cron) → Order Creation → Payment processing
2. LLM streaming response → ComplianceStreamFilter → Client browser
3. Order line items → All gateway sanitizers (WP hooks + Next.js flows)
4. [Add more as needed]

---

## Accepted Risks (Optional but Recommended)

List known issues you have consciously accepted, with timeboxes if possible.

- VIGIL-SEC-042 (or description) is accepted until [date/quarter] because [reason].
- We are aware that [specific legacy pattern] exists and have compensating controls in [place].

This prevents VIGIL from wasting time re-reporting things you already know about.

---

## Custom Escalation Rules (Optional)

Add any project-specific rules you want VIGIL to enforce:

- Any finding that touches the suspension enforcement path must be treated as at least HIGH.
- Deprecations or TODOs in the [critical file] related to payment or compliance logic are MEDIUM+.
- [Your rule here]

---

## Notes for the Auditor

Free text. Anything else the auditor should know before it starts scanning.

Example:
> We are mid-migration from `old.example.com` → `new.example.com`. The old host returns 410 on most paths. Any finding involving cross-domain calls should be read in that light.

---

**Last updated:** [Date] by [Name/Team]

This file is deliberately not secret. It describes priorities and reality, not credentials.
