---
id: 0008
date: 2026-07-31
found_by: author
missed_by: author, RULES.md Rule 3
found_detail: caught while editing the control for an unrelated style issue, not while auditing it
missed_detail: the control was read closely, quoted in the report, and credited as a mitigation
class: a control's presence is not its efficacy — reading is not running
status: open
check:
---

# A rate limiter was credited as a compensating control; it had never blocked a single request

## What was believed

That an authentication bypass was partially mitigated by a per-IP sliding-window rate limiter
sitting in front of the same endpoints. The limiter was read, understood, and described in the
report as reducing — though not closing — the finding. Its configured bound was quoted.

## Why it was false

The limiter never rejected anything. Its prune branch deleted the caller's counter and returned
early whenever the window came out empty — which is the state *every* caller is in on its first
request. The entry was removed before anything was ever recorded, so the next request took the
same branch, and the line that accumulated the count was unreachable for every caller, forever.

Twenty lines of the control, lifted verbatim and exercised:

```
limit is 10 per 60s
500 back-to-back requests from one IP -> allowed: 500, blocked: 0
store after 500 requests: {}
```

The code is not obviously wrong on the page. It has a plausible prune, a plausible eviction
sweep, a plausible bound check. Reading it carefully is what produced the wrong conclusion —
more careful reading would not have helped, because the defect is in the *interaction* between
the early return and the accumulator, and that interaction only shows up in a second call.

The consequence for the audit was not a missed finding but an **understated** one. The report
said "reduced by rate limiting"; the truth was that an unauthenticated caller had unmetered
access to a paid inference endpoint.

## What changed

Nothing yet, mechanically. The proposed mechanism is recorded as **D7**: when a finding's
severity is reduced because a compensating control exists, the report must cite an *execution*
of that control — an observed input and its observed output — not a description of it. Absent
that, the finding stands at its unmitigated severity.

## Why this class matters

`RULES.md` Rule 3 instructs the auditor to "check if mitigations exist elsewhere (middleware,
framework defaults, WAF)" before reporting. **Exist** is the wrong test, and it is the word that
does the damage: a control that exists, is wired up, is syntactically reachable and is wrong
satisfies Rule 3 completely.

This is distinct from `0003-unverified-verification`, where a claim of verification was simply
never performed. Here the verification *was* performed, to the standard the rules ask for, and
the standard was insufficient. That makes it worse, not better — the rule was followed.

The class covers every control an auditor is tempted to credit by inspection:

- rate limiters and quotas
- retry, backoff and circuit-breaker logic
- input validators and sanitisers with an early-return path
- cache invalidation
- feature flags and kill switches
- anything whose behaviour depends on accumulated state across calls

For all of these, the control is cheap to run and expensive to reason about. The asymmetry is
the point: a control that takes twenty lines to exercise should never be credited on a reading.
