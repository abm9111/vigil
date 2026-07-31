---
id: 0006
date: 2026-07-30
found_by: author
missed_by: self-audit, author
found_detail: pre-publication privacy sweep, four passes
missed_detail: three earlier reviews read these files without flagging them
class: contributed material carries the contributor's real system
status: mechanized
check: L19
---

# The skill's own docs shipped a live business's domains, compliance posture and architecture

## What was believed

That `CONTEXT.md` and `templates/vigil-context.md` contained generic examples. They read like
documentation, they had been through three independent reviews, and none flagged them.

## Why it was false

Both carried a real business: live domain names, a specific payment-descriptor sanitisation
approach, card-network brand-risk framing, named internal controls, and an architecture
description accurate enough to be useful to someone attacking it. One worked example was
headed with the company's name.

A plain `grep` for the domain found the first instance. It took **four passes** to clear,
because each later instance described the same business in different words — an internal
control named one way in one file, a domain-specific entitlement rule in another, a named
compliance regime in a third. Machine sweeps found what they were told to look for; the rest
needed reading, and the words to search for were only obvious after finding them.

## What changed

All of it genericised. `L19` now scans `lessons/` and `evals/results/` — the two surfaces
where an outside contributor describes something VIGIL got wrong *on their own codebase* — for
absolute home paths, non-example hostnames, emails, API-key shapes and private-key blocks.
Probed with five realistic leak classes; all five caught.

## Why this class matters

The generalisable point is not "sanitise your examples." It is that **the most dangerous
contribution to an auditing tool is an honest one.**

A useful lesson says "VIGIL rated X as LOW on my codebase and it should have been HIGH." To
make that concrete a contributor reaches for their real finding, their real path, their real
architecture. What arrives is a public, indexed, permanent description of a specific
organisation's security gap, attributed to them.

`.vigil/context.md` is the sharpest version: it is designed to enumerate existential controls,
critical paths and architectural weak points, and it lives inside the audited repo. Pasted into
a lesson, it is an attack map with a byline.

L19 catches the mechanical shapes. It cannot catch "we rely on a legacy service for
authorisation and it is not covered by tests" — prose with no path, no host, no key, and every
detail an attacker wants. That part is a policy, and policies are read by people in a hurry.

The mitigation that actually works is structural: **a lesson is about a class of error, not
about your codebase.** The generalisable part is almost never the proprietary part, so
redaction usually costs nothing. If a lesson cannot be written without your system in it, it
is not yet a lesson — it is an incident report, and it belongs in your own tracker.
