---
id: 0009
date: 2026-07-31
found_by: author
missed_by: author, RULES.md Rule 1, RULES.md Rule 3
found_detail: caught only when the remediation step required opening the flagged files
missed_detail: Rule 1's evidence hierarchy treats tool output as sufficient on its own
class: a scanner hit is a pointer to a question, not an answer to it
status: open
check:
---

# Two findings were reported from scanner output; both files already answered the scanner

## What was believed

That two findings backed by named-tool output met the evidence bar. Both were reported at
MEDIUM/LOW with the tool, rule id and file path cited. One flagged a container as running with
excessive privilege; the other flagged a weak hash primitive.

## Why it was false

Both flagged files already contained the answer, in the file, at the flagged location.

The container image had a comment at the very lines the scanner pointed at, explaining that the
privileged process is a supervisor which drops privilege per task, naming the sibling
configuration file that performs the drop, stating that this specific scanner rule fires anyway
because it reads only the image definition, and giving a one-line command to verify the running
privileges. The sibling file confirmed it. The finding was a documented, verified, deliberate
exception, and the documentation was one `Read` away.

The hash finding was worse. The flagged call sites already declared the primitive
non-security-use through the language's own dedicated parameter for exactly that assertion —
and the digests were persisted as stable record identifiers. Acting on the recommendation would
have changed every existing identifier and orphaned the stored rows. The "fix" was more
dangerous than the finding.

Neither error required judgement to avoid. Both required opening the file.

## What changed

Nothing yet, mechanically. The proposed mechanism is recorded as **D8**: a finding whose
evidence is solely tool output must additionally quote the source at the flagged location and
state what that source says about the flag. A scanner-derived finding that cannot show it read
the target is downgraded to `NEEDS_REVIEW`.

## Why this class matters

`RULES.md` Rule 1 ranks evidence: tool output first, then file:line, then pattern, then
reasoning. It is read — reasonably — as a hierarchy where the *highest available* tier
suffices, and tool output is the highest tier. That reading is what produced both findings.
Rule 3 does say to check for existing mitigations, but it is prose beside a rule that has
already declared the evidence sufficient.

The deeper issue is that scanners are, correctly, context-free. They report what the artefact
says in isolation. The whole value an auditor adds over running the scanner directly is
supplying the context the scanner cannot see — and an auditor that forwards scanner output
verbatim has added nothing while borrowing the scanner's authority.

Where this shape recurs:

- IaC and container scanners that read one file and cannot see the orchestration around it
- dependency auditors reporting CVEs in code paths the project never reaches
- "weak primitive" rules where the weakness is irrelevant to the use
- lint rules already suppressed inline with a stated reason
- any rule whose documented exception mechanism lives outside the scanned artefact

`RULES.md` already warns that "false positives destroy trust faster than missed findings." Both
of these were false positives with the target's own rebuttal sitting in the file — the most
expensive kind, because the reader discovers the auditor did not read what it cited.
