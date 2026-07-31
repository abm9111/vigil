# VIGIL Engine: Bounty & Engagement Tracking

**Purpose:** Track bounty submissions, consulting engagements, CVEs, and revenue across all platforms. Single source of truth for the security business pipeline.

## Storage

All tracking data lives in `~/.vigil/tracking/`:

```bash
mkdir -p ~/.vigil/tracking
```

### Bounty Tracker (`~/.vigil/tracking/bounties.json`)

```json
{
  "version": 1,
  "submissions": [
    {
      "id": "BNT-001",
      "platform": "hackerone",
      "program": "program-name",
      "submitted": "2026-03-27",
      "title": "SQL injection in /api/export endpoint",
      "severity": "CRITICAL",
      "cwe": "CWE-89",
      "status": "triaged",
      "payout": null,
      "vigil_finding": "VIGIL-SEC-103",
      "report_url": "https://hackerone.com/reports/XXXXXX",
      "notes": "Confirmed by triager within 24h",
      "timeline": [
        {"date": "2026-03-27", "event": "submitted"},
        {"date": "2026-03-28", "event": "triaged"},
        {"date": "2026-04-05", "event": "bounty_awarded", "amount": 5000}
      ]
    }
  ],
  "stats": {
    "total_submitted": 0,
    "accepted": 0,
    "duplicate": 0,
    "informative": 0,
    "not_applicable": 0,
    "total_earned": 0,
    "acceptance_rate": 0.0,
    "avg_payout": 0,
    "avg_time_to_triage_days": 0
  }
}
```

### CVE Tracker (`~/.vigil/tracking/cves.json`)

```json
{
  "version": 1,
  "cves": [
    {
      "id": "CVE-2026-XXXXX",
      "project": "FileCodeBox",
      "title": "Unauthenticated RCE via file upload",
      "severity": "CRITICAL",
      "cvss": 9.8,
      "status": "assigned",
      "disclosed": "2026-03-27",
      "published": null,
      "bounty_id": "BNT-001",
      "advisory_url": "https://github.com/project/advisories/GHSA-xxxx",
      "writeup_url": null,
      "timeline": [
        {"date": "2026-03-27", "event": "reported"},
        {"date": "2026-04-01", "event": "cve_assigned"},
        {"date": "2026-04-15", "event": "patch_released"},
        {"date": "2026-04-22", "event": "published"}
      ]
    }
  ]
}
```

### Engagement Tracker (`~/.vigil/tracking/engagements.json`)

```json
{
  "version": 1,
  "engagements": [
    {
      "id": "ENG-001",
      "client": "Company Name",
      "type": "ComplianceSprint",
      "status": "in_progress",
      "start_date": "2026-04-01",
      "delivery_date": "2026-04-04",
      "price": 5000,
      "currency": "USD",
      "paid": false,
      "scope": "Full codebase audit — Python FastAPI backend",
      "vigil_mode": "audit --compliance soc2",
      "report_path": "~/.vigil/reports/ENG-001/",
      "findings": {"critical": 2, "high": 5, "medium": 8, "low": 12},
      "score": 62,
      "notes": "Client referred by DIFC accelerator contact"
    }
  ],
  "pipeline": [
    {
      "company": "Prospect Name",
      "stage": "proposal_sent",
      "type": "SiegeReport",
      "est_value": 15000,
      "next_action": "Follow up 2026-04-10",
      "source": "cold_outreach"
    }
  ]
}
```

### Revenue Tracker (`~/.vigil/tracking/revenue.json`)

```json
{
  "version": 1,
  "monthly": [
    {
      "month": "2026-04",
      "bounties": 2500,
      "consulting": 5000,
      "training": 0,
      "products": 0,
      "total": 7500,
      "expenses": 500,
      "net": 7000
    }
  ],
  "cumulative": {
    "total_revenue": 0,
    "total_bounties": 0,
    "total_consulting": 0,
    "total_expenses": 0,
    "net_profit": 0
  },
  "targets": {
    "phase_1_target": 8000,
    "phase_2_target": 27000,
    "phase_3_monthly_target": 35000,
    "phase_4_monthly_target": 78000
  }
}
```

## Commands

### `/vigil-track add bounty`

```
/vigil-track add bounty --platform h1 --program "program-name" \
  --title "Finding title" --severity CRITICAL --cwe CWE-89 \
  --finding VIGIL-SEC-103
```

Creates entry in bounties.json, returns BNT-ID.

### `/vigil-track add cve`

```
/vigil-track add cve --project "FileCodeBox" --title "Unauth RCE" \
  --severity CRITICAL --bounty BNT-001
```

Creates entry in cves.json, returns CVE tracking ID.

### `/vigil-track add engagement`

```
/vigil-track add engagement --client "Company" --type ComplianceSprint \
  --price 5000 --delivery "2026-04-04"
```

Creates entry in engagements.json, returns ENG-ID.

### `/vigil-track update`

```
/vigil-track update BNT-001 --status bounty_awarded --payout 5000
/vigil-track update CVE-2026-XXXXX --status published
/vigil-track update ENG-001 --status delivered --paid true
```

### `/vigil-track status`

Show dashboard:

```
╔══════════════════════════════════════════════════════════╗
║  VIGIL Business Dashboard — March 2026                  ║
╚══════════════════════════════════════════════════════════╝

BOUNTIES
  Submitted: {N} | Accepted: {N} ({pct}%) | Pending: {N}
  Revenue: ${total} | Avg payout: ${avg}
  Platforms: H1 ({n}), Bugcrowd ({n}), Immunefi ({n})

CVEs
  Assigned: {N} | Published: {N} | Pending: {N}
  Trophy case: {list of CVE IDs}

CONSULTING
  Active: {N} engagements (${value})
  Pipeline: {N} prospects (${est_value})
  Delivered: {N} this month

REVENUE (March 2026)
  Bounties:    ${X}
  Consulting:  ${X}
  Products:    ${X}
  ─────────────────
  Total:       ${X}
  Cumulative:  ${X}

PHASE PROGRESS
  Current: Phase {N}
  Target: ${target}/month
  Actual: ${actual}/month
  Status: {ON_TRACK | BEHIND | AHEAD}

GATES
  ✓ Phase 0: FileCodeBox CVE filed
  ✓ Phase 1: First valid report accepted
  ○ Phase 1: $1K cumulative
  ○ Phase 2: First consulting engagement
  ○ Phase 2: BSCP certification
```

### `/vigil-track report`

Generate monthly summary for record-keeping:

```
/vigil-track report --month 2026-04
```

Outputs markdown summary of all activity, suitable for:
- Personal records
- Tax documentation (UAE freelance license)
- Investor/partner updates (if applicable)

## Data Integrity

- All JSON files use schema version field for future migration
- Backup on every write: `cp file.json file.json.bak`
- Timestamps in ISO 8601 format
- Currency always in USD (convert AED at write time if needed)
- IDs are sequential: BNT-001, CVE-2026-XXXXX, ENG-001
