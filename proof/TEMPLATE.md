---
id: NNNN
date: YYYY-MM-DD
cluster: VIGIL-SEC
severity: HIGH
tool: gitleaks
ecosystem: python
disposition: accepted
missed_by_existing_tooling: true
class: one line naming the CLASS of finding, with no system in it
---

# A one-line title describing the class, not the incident

## What the class is

What kind of mistake this is, stated so that a reader who has never seen the codebase can
recognise it in their own. No repository, path, host, company or finding text.

## Why it survived

Why the existing setup did not catch it. This is the part that carries the value — a finding
that everything already catches proves nothing.

## What generalises

What another team should check as a result. If this section is hard to write, the entry is
probably an incident report rather than proof, and it belongs in your own tracker.

<!-- Before committing:
     - no repository name, path, hostname, company, product or person
     - no code excerpt, no finding text, no architecture description
     - `python3 evals/check_repo.py` (L19 scans this directory)
-->
