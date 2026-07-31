# Open design work

Items that need a decision or a design pass, not an edit. Each states the defect, why the
obvious fix is wrong, and what "done" looks like — so the next session starts from the argument
rather than rediscovering it.

Closed items are not listed here; they live in the git history and in `evals/results/`.

---

## D1 — Most clusters have no probe that can fail

**Status:** open · **Raised by:** Grok (C5), sharpened by Kimi · **Blocks:** honest scoring

Only **security**, **code-health** and **blockchain** declare required tools. Data, API,
infrastructure, frontend, performance, compliance and AI/ML declare none — so they sit at
ceiling 100 having probed nothing. `engines/preflight.md` admits this in its own text, which is
honest but is not a fix: most of the weighted average is unevidenced by construction.

The rule that decides this is already written, in `engines/preflight.md`:

> **A probe must be able to fail.** "grep is installed" cannot fail, so it converts "probed
> nothing meaningful" into ceiling 100 — the N/E vocabulary wrapped around the old lie.

**Why the obvious fix is wrong.** Declaring the grep suite as the probe, and stopping there,
relabels the problem. A suite that is merely *described* is not a probe.

**Two honest options per cluster** (choose per cluster, not globally):

1. **Name a discriminating tool as required** and accept N/E when absent —
   `go vet`, `cargo clippy`, `sqlfluff`, an OpenAPI validator, `axe`/`pa11y` for frontend.
2. **Formalise the check suite as the probe** — versioned, enumerated, with a per-check
   execution ledger ("these N named checks each executed"), recorded in the baseline alongside
   tool versions.

**Constraint that makes this safe:** required-tool lists must stay small and honest. Per
`engines/scoring.md`, *if a tool is missing on most normal machines, it was misclassified as
required — that is a manifest bug, not a reason to weaken the gate.* Getting this wrong turns
every audit into INCOMPLETE and the gate becomes noise.

**Done when:** every applicable cluster has a probe that can fail; a `check_repo.py` check
asserts each cluster in the weights table appears in a preflight tool table or declares an
enumerated suite.

---

## D2 — Commercial engines in a public tree

**Status:** owner decision · **Raised by:** all three reviews

`engines/tracking.md` and `engines/report-generator.md` are business infrastructure, not
auditing capability: consulting price points, a revenue tracker, bounty payouts, a tax-residency
reference. Publishing means publishing the price list to competitors and prospects at once.

Some consultancies do that deliberately. It should be a decision, not a side effect.

**Options:** strip both from the public tree and keep them private · genericise the pricing to
tiers without numbers · publish as-is deliberately.

**Done when:** decided and acted on. Nothing else in the repo depends on the outcome.

---

## D3 — The eval measures a proxy

**Status:** known and documented · **Raised by:** Kimi (C2/I6), partly mitigated

Matching is keyword + line-proximity. Line anchoring closed the naive sprinkling probe, but
someone who has read the fixture can still satisfy every mechanical criterion without
understanding anything. `evals/README.md` states this plainly and the roadmap names the real
fix: **structured finding fields** (`file` and `line` as data, not free text).

Recorded as `lessons/0005-metric-that-flatters.md`, which documents six harness bugs that
each produced a confidently wrong number — in both directions.

**Also open, same area:**
- No `web-app-chain` fixture — correlation pattern 2 (`DATA_EXPOSURE_CHAIN`) is exercised by
  nothing.
- No golden SARIF snapshot — `--ci` output is unexercised markdown.
- Single-model measurement. Recall varies by model; `evals/results/` now carries the caveat,
  but per-model scorecards do not exist.

**Done when:** findings carry structured location data and matching stops being string-based.
Until then, treat a passing run as "no regression detected," never as evidence of audit quality.

---

## D4 — `self-certifying-manifest` calibration

**Status:** open, deliberately · **Raised by:** the eval itself, twice

The fixture expects LOW. VIGIL reported HIGH (run 1) and MEDIUM (run 2). It has out-rated the
manifest both times, and the run-2 write-up concedes the fixture is probably wrong: a manifest
shipped inside the archive it certifies, excluding itself from its own checksum list, unsigned,
and named in the README as the verification step is arguably more than LOW.

**Left unchanged on purpose.** Editing an expectation to match a result is the exact move this
harness exists to prevent — and doing it *because the result is right* is how the habit starts.
It needs an argument, recorded, not a quiet edit.

**Done when:** someone decides, and writes down why, in `evals/results/`.

---

## Checks that would catch the classes above

`evals/check_repo.py` runs 26 structural checks. Every one was added after a real gap got past
the previous set. Known remaining blind spots, from Kimi's M11:

| Class | Caught? | Note |
|---|---|---|
| Dead `[text](link)` | L1 | |
| Dead prose `file.md -> Section` | L14 | added after four such pointers shipped |
| Weight-table drift | L6/L10/L13 | header, mode template, and authority all compared |
| Compliance citations resolving | L8 | |
| Fenced downgrade rules | L15 | added after `siege.md` bypassed the Rule 7 fence |
| Formula integrity | L16 | ceiling term cannot silently vanish |
| **Cross-file semantic contradiction** | **no** | needs semantic comparison, not regex |
| **Used-but-undefined vocabulary** | **no** | e.g. a severity token outside the defined set |
| **Template field drift** | **partial** | L10 covers weights only, not required fields |

The first is the class that produced three Critical findings across two reviews. It may not be
mechanically checkable at all — which is an argument for keeping cross-model review in the loop
rather than assuming the harness has replaced it.
