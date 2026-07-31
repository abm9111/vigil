---
id: 0002
date: 2026-07-31
cluster: EGRESS
severity: HIGH
tool: none
ecosystem: python
disposition: accepted
missed_by_existing_tooling: true
class: a headline capability claim contradicted by the project's own measurement artifact
---

# The strongest evidence against a README is usually already in the repository

## What the class is

A project advertises a headline capability — an accuracy figure, a corpus size, a throughput
number — in the document everyone reads first, marked as delivered. Elsewhere in the same
repository sit the artifacts that measure it: a benchmark result file, a status document, a
migration log.

They disagree, and not marginally. In the case that produced this entry the advertised accuracy
was roughly **1.6×** the only benchmark artifact committed to the repo, and the advertised
corpus roughly **2×** the figure in the project's own status document. Both claims carried a
delivered-feature marker. The benchmark had `n=50`.

Nobody lied. The README was written when the numbers were targets, the benchmark arrived later,
and no process connected the two. That is the normal way this happens, which is why it is worth
having a name for.

## Why it survived

No scanner has an opinion about it. `gitleaks`, `bandit`, `semgrep`, `pip-audit`, `ruff` and
`mypy` all pass — every one of them examines code, and this is a contradiction between two
prose documents. A linter cannot hold two files in mind and notice they disagree.

Nor is it visible in review. The README and the benchmark are edited months apart by people
solving different problems; the diff that introduces the discrepancy is a diff to *one* file,
and it looks correct in isolation.

The detection needs three things at once, which is what makes it a correlation rather than a
finding: read the marketing surface, read the measurement artifacts, and be willing to treat
the project's own evidence as authoritative over its own claims. Each is trivial; together
they are the whole thing.

**The severity is not about accuracy.** A number being stale is `LOW`. This is `HIGH` because
the claim is load-bearing: it is what a user relies on when deciding whether to trust generated
output in a domain with real consequences, and the disclaimer that would qualify it was present
on one internal surface and absent from every surface a user actually reaches.

## What generalises

Treat a repository's own artifacts as the authority on its own claims, and go looking for the
disagreement deliberately:

- Does every capability number in the README have a measurement artifact behind it, and does
  that artifact agree — including on `n`?
- Does a scale claim (documents, users, requests) match the deployment record?
- Is a claim marked as **delivered** when the evidence describes a target?
- Where the product generates content that a reader might act on, does the qualifier reach the
  surface the reader sees, or only the internal one?

The generalisable point is that an audit which only reads code is auditing half the artifact.
The claims a project makes about itself are part of what it ships, they are checkable against
material already in the repository, and no scanner will do it for you.

Related: the same shape as
[`0001`](0001-secret-removed-from-tree-still-live-in-history.md) — in both, every automated
check passes because the check surface and the risk surface are different objects.
