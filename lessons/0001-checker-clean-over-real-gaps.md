---
id: 0001
date: 2026-07-30
found_by: author
missed_by: self-audit
found_detail: manual read while wiring a new cluster
missed_detail: check_repo L1-L6, all reporting CLEAN
class: a checker only checks what someone thought to check
status: mechanized
check: L7, L8
---

# The self-audit reported CLEAN while five real inconsistencies sat in the repo

## What was believed

That `check_repo.py` passing meant the repo was internally consistent. It had just caught two
latent bugs on its first run, which made it feel trustworthy.

## Why it was false

Five inconsistencies were live at the time it reported CLEAN:

- `modes/audit.md` enumerated 9 clusters; 11 existed. Two clusters — including one added that
  same session — would never have run in audit mode, because the mode file's ordered list is
  what actually executes, not the router's "ALL clusters".
- Four compliance citations in `correlation.md` pointed at controls no map defined.

None were checkable by the six checks that existed. Each check had been written for a class
that had already bitten; nothing covered a class that had not.

## What changed

L7 (audit mode enumerates every cluster) and L8 (every cited standard resolves to a map).
Both negative-tested: inject the fault, confirm it fires, confirm it clears.

## Why this class matters

This is the ledger's founding lesson and it has recurred twice since. A green self-audit is
evidence about the classes someone previously thought of, and nothing more. When a gap gets
past the checks, the fix is a new check — not just a patch — because the patch fixes one
instance and the check fixes the class.
