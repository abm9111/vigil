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

**Status:** RESOLVED 2026-08-01 — genericised, both engines kept · **was:** owner decision · **Raised by:** all three reviews

`engines/tracking.md` and `engines/report-generator.md` are business infrastructure, not
auditing capability: consulting price points, a revenue tracker, bounty payouts, a tax-residency
reference. Publishing means publishing the price list to competitors and prospects at once.

Some consultancies do that deliberately. It should be a decision, not a side effect.

**Options:** strip both from the public tree and keep them private · genericise the pricing to
tiers without numbers · publish as-is deliberately.

**Done.** Option 2 of three: the deliverable templates stay, the figures go. Four price
disclosures became relative effort tiers; the personal phase-gate roadmap (a named CVE, a
certification goal, a revenue milestone) became braced placeholders; the jurisdiction-specific
tax line and the geographic targeting line became neutral.

The reasoning is in the file now, and it is not only commercial: **a published figure would be
wrong for almost every reader** — scope, jurisdiction, liability and buyer all move it — and it
would price an engagement before anyone had scoped it. Tiers carry the ordering, which is the
part that generalises.

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

## D5 — Does the skill beat its own absence?

**Status:** measurable since 2026-07-31, **not yet measured** · **Raised by:** a survey of
comparable repos

Every recall number this project has published was unanchored. The harness scored VIGIL
against fixtures and reported 80%, but nothing established what a bare model scores on the same
fixtures with a competent prompt. If the answer is also 80%, the eleven cluster files, the
correlation engine and the scoring model are decoration, and the honest move is to delete most
of it.

That is not a hypothetical objection. `levnikolaevich/claude-code-skills` argues explicitly
that modern Claude and Codex models work better with concise procedural guidance and ships 52
files where this repo has well over a hundred. That claim has never been tested here, and
dismissing it because this repo is more thorough would be assuming the conclusion.

**Now runnable:**

```bash
python3 evals/run_eval.py --baseline --runs 3
```

Two arms over the same fixtures with the same scorer: VIGIL, and a control with no skills
discoverable, given the deliberately strong prompt in
[`../evals/baseline-prompt.md`](../evals/baseline-prompt.md). The harness proves the control
cannot see the skill before trusting a single control number — otherwise both arms are the
treatment arm, the delta collapses to zero, and the plausible-looking conclusion is "VIGIL adds
nothing."

It is a measurement, not a gate: it always exits 0. Wiring it to an exit code would create
pressure to weaken the control on a red build, which is the threshold-lowering move `L12`
exists to prevent.

**Done when:** the numbers exist in `evals/results/`, including any fixture where VIGIL did not
win. A null result is the most valuable output this can produce and the easiest to quietly not
publish.

---

## D6 — Preflight probes a tool's existence, not its environment

**Status:** MECHANIZED 2026-07-31 as `L30` · **Raised by:** [`lessons/0007`](../lessons/0007-instrument-outside-the-subject.md)

Preflight asks "does a binary of this name run?" A tool resolved from outside the subject's
environment answers yes, then reports on a project whose dependency graph it cannot see. With
the usual "ignore unresolvable imports" flag set, every dependency-typed value degrades to a
permissive type and the real errors vanish. The run exits 0 and reports less than the truth.

This fails toward **clean**, which is the direction preflight exists to prevent. A missing tool
is already loud; a misresolved one is silent.

**Shape of the fix:** record the resolved absolute path per tool, and whether it lies inside the
subject's environment (venv, node_modules, lockfile-managed toolchain). Treat "resolved outside
the subject environment" as a coverage reduction — the same ceiling machinery as a missing tool
— rather than a pass.

**Done:** `engines/preflight.md` now requires the resolved path to be recorded, prefers the
project-local invocation, and makes Rule 6 binding — a tool resolved outside the subject's
environment cannot contribute to a ceiling of 100. The sharp sub-case is fenced explicitly:
an analyzer that cannot import the subject's dependencies produces a clean result that is
**not evidence**, so that portion is N/E rather than scored.

`L30` asserts each clause survives, with the same honest limit as `L28` — it proves the
requirement is stated, not that a run obeyed it. Verified by softening the ceiling clause to
"should ideally be noted" and watching it fire.

**Still open:** nothing enforces this at *run* time. A behavioural test needs a fixture with a
deliberately misresolved toolchain, which is the same live-CLI harness D5 needs.

---

## D7 — A compensating control is credited on inspection, never on execution

**Status:** MECHANIZED 2026-07-31 as `L31` (Rule 3a) · **Raised by:** [`lessons/0008`](../lessons/0008-control-present-not-effective.md)

`RULES.md` Rule 3 says to check whether mitigations **exist** before reporting. A control that
exists, is wired up, is reachable, and is wrong satisfies that test completely — and the
resulting finding is understated rather than missed, which is harder to notice.

**Shape of the fix:** when a finding's severity is reduced because a compensating control
exists, require the report to cite an execution of that control — an observed input and its
observed output. Absent that, the finding stands at its unmitigated severity. This is the same
fence `RULES.md` Rule 7 already applies to reachability downgrades, generalised from CVEs to
controls.

**Done when:** Rule 3 says "execute" rather than "check if it exists", and a severity reduction
citing a control with no execution evidence is rejected by the report format.

---

## D8 — Tool output alone is treated as sufficient evidence

**Status:** MECHANIZED 2026-07-31 as `L32` (Rule 1a) · **Raised by:** [`lessons/0009`](../lessons/0009-scanner-hit-is-a-pointer.md)

Rule 1 ranks evidence with tool output at the top, which reads as "the highest available tier
suffices." Scanners are correctly context-free: they report what one artefact says in isolation.
The auditor's entire value over running the scanner directly is supplying the context the
scanner cannot see, so a finding forwarded from tool output alone has added nothing while
borrowing the scanner's authority.

**Shape of the fix:** a finding whose evidence is solely tool output must also quote the source
at the flagged location and state what that source says about the flag — including the case
where it documents a deliberate exception. A scanner-derived finding that cannot show it read
its target is downgraded to `NEEDS_REVIEW`.

**Done when:** Rule 1 distinguishes "a tool flagged this location" from "this location is a
finding", and the report format requires the second.

---

## D9 — The audited tree is never named

**Status:** MECHANIZED 2026-07-31 as `L33` (Rule 10a) + `tree_state` in the record · **Raised by:** [`lessons/0010`](../lessons/0010-which-tree-was-audited.md)

`modes/*.md` head every report `{project} @ {commit_short}`, and `RULES.md` Rule 5 governs which
directories to skip — but nothing establishes *which tree* is the subject. Working tree,
tracked-at-HEAD and CI checkout are three different objects that answer the same question
differently; one secret scan returned 32, 1 and 0 findings across them.

A commit SHA in the header of an audit run against a dirty working tree is a reproducibility
claim the report cannot honour. It also silently breaks Rule 10: a baseline delta that compares
across tree kinds attributes uncommitted work to a code change.

**Shape of the fix:** add a `Subject` line to the preflight block naming the tree and its state
— e.g. `working tree (N tracked modified, M untracked-unignored)` or `tracked @ <sha> (clean)`.
Permit a bare commit SHA in the header only when the working tree is clean; otherwise the header
must say so. Count untracked-and-unignored files explicitly rather than letting them blend into
source, since that population is outside review, outside CI, and one command from publication.

**Also worth mechanising here:** ignore-aware search tools skip ignored paths by default, so
adding a path to the ignore file removes it from subsequent sweeps. Secret and PII scans must
run with ignore rules disabled, or a remediation will silently shrink detection coverage.

**Done when:** no report can present a commit SHA as its subject while the tree it examined
differs from that commit, and the egress cluster's scans are ignore-agnostic by construction.

---

## Checks that would catch the classes above

`evals/check_repo.py` runs 33 structural checks. Every one was added after a real gap got past
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
