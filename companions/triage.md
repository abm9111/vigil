# /vigil-triage — Finding Triage and Prioritization

**Trigger:** `/vigil-triage [--target program_name] [--budget N_hours]`
**Time:** 3-5 minutes
**Purpose:** Prioritize VIGIL findings by exploitability, payout potential, and duplicate probability for bounty submission

## Prerequisites

A completed `/vigil audit` or `/vigil siege` plus optionally `/vigil-recon` results.

## Execution

### Step 1: Collect All Findings (30s)

Gather findings from the most recent VIGIL audit/siege output.

Group by:
- Source: VIGIL pattern match, Nuclei template, Semgrep rule, manual correlation
- Severity: CRITICAL > HIGH > MEDIUM > LOW
- Type: injection, auth, config, crypto, logic, dependency

### Step 2: Score Each Finding (2min)

For each finding, compute a **Triage Score (0-100)**:

```
triage_score = (exploitability * 0.30) + (impact * 0.25) + (novelty * 0.25) + (evidence * 0.20)
```

| Factor | 0-25 | 26-50 | 51-75 | 76-100 |
|--------|------|-------|-------|--------|
| **Exploitability** | Theoretical only | Requires preconditions | Straightforward chain | Single request PoC |
| **Impact** | Info disclosure, no PII | Limited data/DoS | User data/account takeover | RCE/full DB dump/funds |
| **Novelty** | Common scanner finding | Known class, new instance | Uncommon pattern | Novel technique/chain |
| **Evidence** | Pattern match only | Code confirmed | HTTP request confirmed | Full PoC working |

### Step 3: Duplicate Risk Assessment (1min)

For each finding, estimate duplicate probability:

| Indicator | Duplicate Risk |
|-----------|---------------|
| Generic scanner finding (missing headers, info disclosure) | **90%+** — skip |
| Common vuln in popular endpoint (login XSS, basic IDOR) | **70-80%** — submit only if novel angle |
| Vuln in lesser-known feature/API | **30-50%** — good target |
| Chained exploit across multiple components | **10-20%** — high value |
| Business logic flaw requiring domain knowledge | **5-10%** — very high value |
| Novel attack technique or 0-day | **<5%** — submit immediately |

Heuristics for duplicate estimation:
1. **Program age:** Newer programs (<6 months) = lower duplicate risk
2. **Researcher count:** Programs with <50 researchers = lower duplicate risk
3. **Bounty amount:** Higher bounties attract more researchers = higher duplicate risk
4. **Component depth:** Deeper in the application = lower duplicate risk
5. **Automation detectability:** If nuclei/burp finds it easily = high duplicate risk

### Step 4: Payout Estimation (30s)

Based on program and finding type:

| Finding Type | HackerOne Range | Bugcrowd Range | Immunefi Range |
|-------------|-----------------|----------------|----------------|
| RCE | $10K-$100K+ | $5K-$50K | $50K-$15M |
| Auth bypass (full) | $5K-$50K | $3K-$25K | $10K-$500K |
| SQL injection | $3K-$25K | $2K-$15K | N/A |
| SSRF + escalation | $2K-$15K | $1.5K-$10K | $5K-$100K |
| IDOR (significant data) | $1K-$10K | $500-$5K | N/A |
| XSS (stored) | $500-$5K | $300-$3K | N/A |
| CORS + credentials | $500-$3K | $300-$2K | N/A |
| Info disclosure | $100-$500 | $50-$300 | N/A |
| Missing headers | $0-$100 | $0-$50 | N/A |

### Step 5: Prioritized Action Plan (1min)

Sort findings by: `triage_score * (1 - duplicate_probability) * payout_estimate`

## Output Template

```
╔══════════════════════════════════════════════════════════╗
║  VIGIL Triage — {target} ({N} findings)                 ║
╚══════════════════════════════════════════════════════════╝

TIME BUDGET: {budget}h available

━━━ SUBMIT NOW (high value, low duplicate risk) ━━━━━━━━━

  #1  VIGIL-SEC-103  CRITICAL  SQL injection in /api/export
      Triage: 87/100 | Dup risk: 15% | Est: $5K-$15K
      Time to PoC: ~2h | ROI: ★★★★★
      → Write PoC, submit to HackerOne within 24h

  #2  VIGIL-CORR-001  CRITICAL  Auth bypass + data exposure chain
      Triage: 82/100 | Dup risk: 10% | Est: $8K-$25K
      Time to PoC: ~4h | ROI: ★★★★★
      → Document full chain, submit as single high-impact report

━━━ VERIFY FIRST (promising but needs confirmation) ━━━━━

  #3  VIGIL-SEC-201  HIGH  Missing auth on /admin/export
      Triage: 71/100 | Dup risk: 35% | Est: $2K-$8K
      Time to verify: ~1h | ROI: ★★★★
      → Confirm endpoint is accessible, check if internal-only

━━━ BATCH SUBMIT (quick wins, moderate value) ━━━━━━━━━━━

  #4  VIGIL-SEC-401  MEDIUM  CORS allows evil.com with creds
      Triage: 55/100 | Dup risk: 50% | Est: $500-$2K
      Time: 30min | ROI: ★★★

━━━ SKIP (low value or high duplicate risk) ━━━━━━━━━━━━━

  #5  VIGIL-SEC-405  LOW  Missing X-Frame-Options header
      Triage: 12/100 | Dup risk: 95% | Est: $0-$50
      → Not worth submission time

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Summary:
  Submit now: {N} findings (~{X}h work, est. ${low}-${high})
  Verify first: {N} findings (~{X}h work)
  Batch: {N} findings (~{X}h work)
  Skip: {N} findings

Recommended order: #{ids} → total ~{X}h for est. ${total_low}-${total_high}
```

## Rules

1. **Never submit INFO-only findings** — wastes reputation score
2. **Never submit without PoC** — "I think this might be vulnerable" = instant close
3. **Chain findings when possible** — one CRITICAL chain > five MEDIUMs
4. **Check program scope BEFORE writing report** — out-of-scope = reputation damage
5. **Time-box verification** — if PoC takes >4h, move to next finding
6. **Track submissions** — use `/vigil-track` to avoid duplicate submissions across programs
