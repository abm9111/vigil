---
id: 0001
date: 2026-07-31
cluster: VIGIL-SEC
severity: HIGH
tool: gitleaks
ecosystem: python
disposition: accepted
missed_by_existing_tooling: true
class: secret deleted from the working tree and gitignored, still live in pushed history
---

# A credential can be "removed" in every sense a reviewer checks and still be published

## What the class is

A config file carrying a real API key is committed. Later — often during exactly the cleanup
that is supposed to fix it — the file is deleted from the working tree and added to
`.gitignore`. Every subsequent check agrees the repository is clean:

- the file is not in `HEAD`
- `.gitignore` names it, so it will not come back
- a secret scan of the **working tree** reports nothing
- the code review that removed it was, in good faith, a security improvement

None of that touches the commit where the key was introduced. The credential is still in
history, still reachable from every branch that descends from it, and still valid — because
deleting a file does not rotate anything.

Three properties have to hold simultaneously for this to be dangerous, and each one is checked
by a different tool or by none:

1. **the value is still live** — belongs to the secret store, not the repo
2. **the commit is an ancestor of a pushed ref** — belongs to `git merge-base`, not the scanner
3. **the endpoint it authenticates is remotely reachable** — belongs to config, not either

## Why it survived

The scanner did its job: it reported a rule hit, a file, a line and a commit. What it did not
report — and is not built to — is whether that commit was ever pushed, whether the value is
still valid, or whether the file had since been "handled".

So the finding reads as historical housekeeping. A reviewer who checks the working tree, finds
it clean, and sees the file gitignored has every reason to close it. The finding survives
precisely because the remediation that was performed is genuinely good practice; it is just
aimed at the wrong artifact.

The delta is not the detection. The scanner line was available all along. The delta is the
three-step correlation that converts it into *rotate this credential now*, and the ordering
that falls out of it: **rotate first, rewrite history second.** Rotation is one action that
makes every historical copy worthless; history rewriting is a force-push against every branch
containing the commit, and it races anyone who already cloned.

A private repository lowers the blast radius. It does not change the ordering, because
visibility is a setting and a clone is forever.

## What generalises

Treat "secret removed from the working tree" as an **unverified** claim, not a fix. Three
questions settle it, and none of them are answered by re-running the scanner:

- Is the flagged commit an ancestor of any pushed ref?
- Is the value still present in the live secret store?
- Is the endpoint it authenticates reachable from outside?

If all three are yes, the finding is not historical and its severity is whatever the credential
protects — not `LOW` because the file is gone.

More generally: a secret scan that reads only the working tree answers a question nobody asked.
Git is the storage layer, so history is the state, and any scan that stops at the checkout is
measuring the wrong surface — the same shape as [`lessons/0005`](../lessons/0005-metric-that-flatters.md),
where the measurement pointed slightly away from the thing that mattered.
