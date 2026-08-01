---
id: 0014
date: 2026-08-01
found_by: author, gpt-5.5
missed_by: self-audit, test_prose_clauses, grok, kimi, ci
found_detail: a third-model review found the suppression contradiction; the prose-check inversion was found by attacking the checks directly rather than reading them
missed_detail: five checks searched for a fragment of a sentence, so negating the sentence around the fragment left every one green
class: a check that a rule is *stated* was satisfied by the rule being *quoted*
status: mechanized
check: L28, L30, L31, L32, L33, L36
---

# Every rule in this repository could be reversed without deleting a word of it

## What was believed

That `L28` and `L30`–`L33` protected the rules they name. Each searches its document for a
pattern; each has a per-clause inversion probe in `tests/test_prose_clauses.py`; three prior
instances of "the pattern matched incidental text" had already been found, fixed, and written
up as a convention in `AGENTS.md`:

> Keep every alternative keyed to text that changes when the rule's meaning changes.

That convention is correct. It is also insufficient, and the reason is the whole lesson: a
fragment **of a negated sentence** is still text that changes when the meaning changes. It just
does not change when the meaning is changed *this* way.

## Why it was false

Two edits. Neither deletes anything. Both were reported clean by 35 checks and 167 tests.

**Insertion** — every word of the rule survives, spliced apart by its own reversal:

```diff
- **A mitigation may reduce a finding's severity only on demonstrated efficacy.**
+ **A mitigation may reduce a finding's severity — and this is deliberately not restricted
+   to only on demonstrated efficacy; a control that is present and wired up is enough.**
```

`L31`'s pattern was `only on demonstrated efficacy`. Present. Green.

**Historical quotation** — the rule is preserved verbatim and demoted to a description of what
used to be true:

```diff
- **The default is no, and enter must select it.** If the user says nothing, nothing is shared.
+ **The default is yes.** Earlier versions specified that the default is no, and enter must
+   select it; that is no longer the behaviour.
```

All eight `L28` clauses matched. `AUDIT EXIT=0`. That edit **flips telemetry consent to
opt-out** — records written and shared without the user being asked — and it is the single most
damaging change anyone could make to this repository. It is also not an adversarial
construction: keeping the old sentence as a note is how documentation drifts everywhere.

**27 of 31 clause patterns were unanchored fragments.** All 27 were defeatable this way.

Separately, and found by a third-model review rather than by any check: `FLAGS.md` said a
suppressed finding is "hidden from output and excluded from scoring" while `engines/scoring.md`
said it is "always reported, at its mechanically-derived severity" — and `FLAGS.md`
contradicted *itself* three lines later. `.vigil/ignore` was specified as bare patterns with no
owner and no expiry, in a file that lives **inside the audited repository**, against a rule in
`scoring.md` reading *"Never accept a suppression that is anonymous or open-ended — that is the
audited party grading itself."* A repo could suppress its own HIGH findings and keep a green
gate. `SECURITY.md` names that shape as an in-scope vulnerability.

## What changed

A clause is now a **whole sentence**, and `clause_holds()` requires it to appear:

1. **verbatim** — insertion anywhere inside it breaks the match;
2. **beginning a sentence** — line start, list bullet, table cell or after terminal
   punctuation, so no words can lead into it;
3. **without negating language in the preceding context** — `no longer`, `earlier version`,
   `is now`, `deliberately not`, and a dozen more.

Both attacks now fail, as regression tests. `L36` was added for the suppression contract, and
`FLAGS.md` was rewritten to match `scoring.md`: a suppressed finding is always reported, only
its scoring status changes, and every `.vigil/ignore` entry carries an owner and an expiry.

**This does not prove meaning, and the code says so.** A regex cannot. What it buys is that
ordinary drift — which produced every instance found so far, including this one — now fails
loudly, and reversing a rule requires deleting the sentence that states it. Deletion is a
visible act in review; quotation is not.

## Why this class matters

The general shape: **a check for the presence of a claim, standing in for a check on the claim
being in force.** Presence and force are different properties, and the gap between them is
exactly wide enough to fit the word "not".

| Verifies presence | Does not verify |
|---|---|
| a policy document exists and mentions encryption | that it mandates it, or is current |
| a licence header appears in every file | that it is the licence the project grants |
| a config key is set | that anything reads it |
| a compliance control is documented | that it is in force — `lessons/0008`, from the other side |
| a rule's text appears in a file | that the file asserts it rather than quoting it |

VIGIL audits other people's repositories for precisely this. Rule 3a exists because a control
that was *present* was credited without being *effective*. `lessons/0008` is that lesson about
somebody else's rate limiter. This is the same mistake, made by the checks that enforce it,
about their own rules — and it took attacking them to see, because reading them proves nothing:
every one of these checks reads correctly.

The operational rule: **a check is not verified by reading it, only by defeating it.** Five
checks here had per-clause inversion probes, three recorded prior instances, and a written
convention. All of it was green while the rules could be reversed. The probes were written by
the same person who wrote the patterns, testing the failure mode that person had already
imagined. Two of the four findings this round came from a model that had never seen the file.
