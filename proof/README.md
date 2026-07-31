# Proof

Times VIGIL found something real, on a codebase that was not its own.

This is the counterpart to [`lessons/`](../lessons/README.md), and the distinction matters:

|  | Records | Answers |
|---|---|---|
| [`lessons/`](../lessons/README.md) | VIGIL was **wrong** | *Should I trust it?* |
| `proof/` | VIGIL was **right**, on someone's real code | *Is it worth running?* |

A project that only publishes its failures looks unreliable; one that only publishes its wins
looks like marketing. Both surfaces exist so neither can be the whole story, and both are
generated into [`LEDGER.md`](../LEDGER.md) side by side.

## The rule is the same as for lessons, and it is not negotiable

**An entry is about a class of finding, not about a codebase.**

No repository name. No path. No hostname, company, product or person. No finding text, no code
excerpt, no architecture description. Not in the frontmatter, not in the prose, not "lightly
anonymised".

The temptation here is worse than in `lessons/`, because a proof entry *wants* to be
impressive, and specificity is what makes a war story impressive. Resist it. The generalisable
part is almost never the proprietary part, so redaction usually costs nothing — and where it
does cost something, the entry does not get written.

`L19` scans this directory for the mechanical shapes (paths, hosts, emails, key shapes). It
cannot read prose. Every entry is read by a maintainer before merge, and that read is the
actual control.

## What a good entry proves

The claim is not "VIGIL is clever". It is one of:

- a finding the project's **existing tooling did not surface** — the delta is the point
- a finding that required **correlating two clusters**, which single-purpose scanners cannot do
- a **severity judgement** that turned out to match reality

If the finding is one a bare `semgrep` run would have printed, it is not proof of VIGIL; it is
proof of semgrep, and VIGIL's own [`RULES.md`](../RULES.md) says to credit the tool.

## Format

Copy [`TEMPLATE.md`](TEMPLATE.md). Frontmatter is a controlled vocabulary — the fields are
enums so that the ledger can count them and so that free text has nowhere to hide. Prose is
limited to the three headed sections, and every one of them is about the class.

Where the finding came from a run that produced a machine record, cite the aggregate rather
than attaching the record: run records live in the user's own `.vigil/runs/` and are cleared by
[`evals/privacy_gate.py`](../evals/privacy_gate.py) before they are ever shared.
