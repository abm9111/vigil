---
id: 0010
date: 2026-07-31
found_by: ci, author
missed_by: author, RULES.md Rule 5, modes/audit.md output template
found_detail: a CI job failed on a path that exists locally but is not tracked; a pre-push gate refused a commit that had swept in untracked files
missed_detail: the report header named a commit; the audit had been run against a working tree far ahead of it, and nothing in the format made that expressible
class: a finding is relative to a tree, and the tree is never named
status: mechanized
check: L33
---

# An audit report was headed with a commit SHA; it had audited neither that commit nor anything equal to it

## What was believed

That "the codebase" is a single unambiguous object, so a report could be headed
`{project} @ {commit_short}` and every finding inside it understood as a fact about that
commit.

## Why it was false

At least three different trees can be called "the codebase", and they disagree materially:

| Tree | What it is |
|---|---|
| working tree | tracked files at current content, **plus** everything untracked-and-unignored |
| tracked-at-HEAD | what the named commit actually contains |
| CI checkout | what `checkout` produces — tracked files only, no local strays |

In one audit these three produced different answers to the same question. A secret scan
returned **32** findings over the working tree, **1** over history, and **0** over the tracked
tree. All three were correct; they were answers to different questions, and only one of them
was the question the report claimed to be answering.

The header said `@ <commit>`. The audited tree was tens of files and roughly two thousand lines
ahead of that commit, none of it committed. Every finding in that report was a fact about an
unnamed intermediate state that existed only on one machine.

Four failures followed from the same confusion, in one session:

1. A lint target was added for a directory that exists locally and has **zero** tracked files.
   The tool emits "no such file or directory" on a clean checkout and fails the job. It passed
   every local run.
2. A staging command swept in hundreds of untracked-but-unignored files — including embedded
   repositories and a file holding a verified-live credential. A pre-push gate caught it.
3. An analyser's backlog was measured against the working tree, so it counted defects in files
   that no pipeline will ever see, and a remediation was written for some of them.
4. Most instructive: adding a directory to the ignore file — a *remediation* — made a live
   credential inside it invisible to ignore-aware search. A recursive grep for the key came back
   empty and was very nearly reported as "clean". The direct read found three occurrences.

(4) is the trap worth remembering. Modern search tools respect the ignore file by default, so
**hardening the repository reduced the scanner's field of view.** Remediation and detection
moved in opposite directions, silently.

## What changed

Nothing yet, mechanically. Working practice during the session became: rebuild the subject from
`git ls-files` into a scratch directory and run the gate there, which is what caught (1) before
it shipped.

The proposed mechanism is **D9**: the report names its tree, and a bare commit SHA may only
head an audit whose working tree is clean.

## Why this class matters

`RULES.md` Rule 5 is titled "Scope Discipline" and is entirely about which *directories* to
exclude — `node_modules`, `.venv`, honouring the ignore file. It never establishes which
**tree** is the subject, so the auditor inherits whatever happens to be on disk and the report
has no field in which to say so.

The consequences are not cosmetic:

- A report headed with a commit is **not reproducible**. Someone checking out that commit sees
  a different codebase from the one audited, and cannot reconcile the difference.
- Baselines and trend deltas (Rule 10) silently compare across tree kinds. A score that moved
  because uncommitted work appeared is not a code regression.
- Untracked-and-unignored files are the highest-risk population in the repository — they are
  outside review, outside CI, and one command from publication — and an audit scoped to the
  tracked tree never sees them, while one scoped to the working tree cannot tell them apart
  from real source.
- `--ci` artefacts are produced from the checkout, so a finding that only exists in someone's
  working tree cannot be actioned by the pipeline that receives it.

The shape is not specific to git. Any subject with more than one materialisation has it: a
container image versus its build context, a deployed artefact versus its source branch, a
lockfile-resolved dependency set versus a declared one. In each case the auditor picks one by
accident and the report implies the other.
