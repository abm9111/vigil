---
id: 0012
date: 2026-08-01
found_by: author
missed_by: self-audit, ci, L34, review
found_detail: noticed only because someone was watching for the run and it never appeared
missed_detail: nothing can report the absence of a run; the badge kept showing the previous commit's green
class: a control removed produces silence, and silence is indistinguishable from nothing to report
status: mechanized
check: L35
---

# Narrowing the CI trigger to stop redundant tag runs stopped every branch run instead

## What was believed

That `on: push: tags-ignore: ['**']` means *"run on pushes, except tag pushes"*. It reads that
way, it is one line, and it was committed as tidy-up with the gate green.

## Why it was false

GitHub matches a `push` workflow to a branch only when a branch filter is **absent entirely**
or matches. Supply tag filters alone and there is nothing for a branch to match, so the
workflow runs for no push at all. The correct spelling of the same intent is
`branches: ['**']` — every branch, and by omission no tags.

The evidence is an absence, which is why it survived:

```console
$ git push origin main                       # succeeded
$ gh api "repos/OWNER/vigil/actions/runs?head_sha=$(git rev-parse HEAD)" --jq .total_count
0
```

Not a red run. **No run.** For eight minutes a watcher polled for a result that was never
going to exist. Meanwhile the README badge kept rendering green, because a badge reports the
last run that happened, and the last run that happened was on the commit before the trigger
was narrowed. Every one of the 34 checks was intact, tested, and never invoked.

The commit that did it was titled *"ci: do not run the gate on tag pushes"*, and its diff was
one line inside a comment block explaining why redundant tag runs are noise. Reviewing that
diff on its merits, it is correct. What it actually did is not visible in it.

## What changed

The trigger is `branches: ['**']`. **L35** fails the build when the `push` trigger carries a
tag filter and no branch filter, and when `push` is absent altogether — a merge gate that runs
only on `pull_request` leaves direct pushes to `main` unchecked, which for a single-maintainer
repo is every push.

L35 parses the YAML by hand and skips comment lines. CI installs `pytest`, `mypy` and `ruff`;
adding PyYAML so the gate can verify that the gate runs is a dependency in the wrong
direction. Skipping comments matters for a second reason: the block now *documents this trap*,
so a check reading comments as configuration would be satisfied by the warning about itself —
the same defect `L34` hit when a comment explaining `ruff check .` satisfied the check for the
recipe.

## Why this class matters

`lessons/0011`, hours earlier, was a gate that ran and disagreed with the local one. This is
worse in the way that matters: **a gate that does not run emits nothing, and nothing is what a
healthy system also emits.** Red is a signal. Absent is not.

The general shape — a control whose failure mode is silence, paired with an indicator that
reports the last success rather than the current state:

| Control | What its absence looks like |
|---|---|
| A CI trigger | no run, and a badge still green from last time |
| A cron job | no alert, which is what "nothing is wrong" also looks like |
| A log shipper | an empty dashboard, identical to a quiet week |
| A test that silently stopped collecting | a passing suite, one file lighter |
| A monitor whose query returns no rows | no page, because there is nothing to page about |

VIGIL has a rule for the subject side of this and did not apply it to itself. **N/E** exists
precisely because *"the scanner did not run"* must never render as *"the scanner found
nothing"* — and `SECURITY.md` names "a gate that can be made to pass while findings are
unresolved" as in-scope for a vulnerability report. A trigger narrowed to nothing is that
vulnerability, in this repo's own pipeline, introduced by a commit whose message said it was
reducing noise.

The auditing consequence is direct: a green CI badge on an audited repo is evidence that a
pipeline succeeded, **not** that it ran on the commit in front of you. Anything treating a
badge, a last-run status, or an empty findings list as evidence of a check having executed is
making this mistake. Ask what the control emits when it is switched off. If the answer is
"the same as when it passes", it is not a control.
