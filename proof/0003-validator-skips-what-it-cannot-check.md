---
id: 0003
date: 2026-08-01
cluster: DATA
severity: HIGH
tool: none
ecosystem: python
disposition: accepted
missed_by_existing_tooling: true
class: a validator drops checks it cannot run, so degraded input produces a clean result
---

# The checks that catch bad data are the ones that disappear when the data is bad

## What the class is

A pipeline extracts structured records from unreliable input — OCR, a vision model, a scraped
page — and validates them before storage. The validator builds a list of checks and reports
whatever failed.

Some checks are appended conditionally, because they need more than one field to be meaningful:

```python
if lines and subtotal is not None:
    checks.append(Check("lines_sum_to_subtotal", ...))
```

That reads as defensive. It is the defect. A missing field does not **fail** the check — it
**removes** it. The arithmetic that reconciles the parts against the whole is skipped exactly
when extraction was unreliable enough to lose a field, which is exactly when it was needed.

Measured on one real record, by executing the validator rather than reading it:

| Input | Checks emitted | Failed |
|---|---:|---:|
| healthy record | 7 | 0 |
| one line amount wrong | 7 | **1** — caught |
| same wrong amount, one input field missing | **4** | **0** — passes clean |

The corrupted record is accepted, and the report says the same thing it says for a good one.

## Why it survived

Every scanner passed. Secret scanning, dependency audit, the linter, the type checker, the
static-analysis pass — none has an opinion about the *shape* of a validation result, because
this is not a vulnerability, a type error, or a style issue. It is an epistemics bug: the code
is correct at every line and wrong as a whole.

Nor is it visible in review. The conditional guard is the thing a careful reviewer *wants* to
see — it prevents a crash on incomplete data, and removing it looks like the mistake.

The author was already alert to the underlying risk, having written elsewhere in the same file
that a value must never be silently defaulted "because the gates only check what they can see."
The insight was there. It had not been applied to the guard clauses themselves.

## What generalises

**A validator needs three outcomes, not two.** Passed, failed, and **could not check**. With
only the first two, absence of evidence is recorded as evidence of absence, and the result is
strongest where the input is weakest.

Concretely, on any pipeline that validates extracted data:

- Do any checks depend on a field that extraction can plausibly miss? Feed it a record with
  that field absent and count the checks emitted, not the failures.
- Does the count of checks *vary with input quality*? If it does, the report is not comparable
  between records, and a clean result on a degraded record means less than a clean result on a
  complete one.
- Does anything downstream distinguish "validated, 7 checks" from "validated, 4 checks"? If the
  stored record carries only a boolean, the distinction is lost at the point it matters.
- Where a reconciliation input is missing, emit a **failing or needs-review** check rather than
  none, so degraded extraction is louder than clean extraction rather than quieter.

The general form is the one this project applies to its own scoring: a cluster that could not be
examined is not a cluster that passed. Anything that produces a verdict from evidence needs to
say when the evidence was not there — see the N/A versus no-evidence distinction in
[`../engines/scoring.md`](../engines/scoring.md).

Related: [`0001`](0001-secret-removed-from-tree-still-live-in-history.md) and
[`0002`](0002-readme-claim-contradicted-by-own-benchmark.md) — in all three, every automated
check passes because the check surface and the risk surface are different objects.
