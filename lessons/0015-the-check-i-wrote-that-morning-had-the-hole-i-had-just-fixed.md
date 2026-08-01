---
id: 0015
date: 2026-08-01
found_by: kimi
missed_by: author, self-audit, ci, grok, gpt-5.5
found_detail: the first scheduled run of the automated review job, hours after the checks it broke were written
missed_detail: L34 asserted only that CI's commands are in the Makefile, never that the Makefile's are in CI; L25 walked the record schema and not the envelope schema
class: a guard written for one direction, by someone who had just written down that guards must be symmetric
status: mechanized
check: L25, L34
---

# The check written that morning contained the hole whose lesson was written that morning

## What was believed

That `L34` protected the gate. It was added hours earlier, with a lesson (`lessons/0011`), two
negative tests, and a docstring explaining that a shared gate definition does not produce a
shared verdict.

And that `L25` enforced the closed-schema guarantee. It had existed for weeks, and had been
extended that same day after a third-model review found an array without `items`.

## Why it was false

**`L34` checked one direction.** For every command CI runs, it asserted the Makefile runs it
too. Nothing asserted the reverse. Delete the `mypy` step from the workflow:

```console
$ python3 evals/check_repo.py
VIGIL self-audit: CLEAN — no dead links, orphans, or prefix gaps.
```

A pull request could switch off part of the merge gate with every check green. The local gate
stays stronger, so `make check` keeps passing and nothing reveals that the gate which actually
blocks a merge is now smaller.

The uncomfortable part is that `lessons/0011` — the lesson `L34` was written *for*, that same
morning — states the fix in its own words:

> Separate processes let each arm assert its own precondition, and the **symmetric guard** is
> the actual fix: nothing had checked that the treatment arm *had* the skill.

The conclusion was written down, applied to the eval harness, and not applied to the check
being written directly beneath it.

**`L25` walked `run-record.schema.json` and not `bundle.schema.json`.** The closed-schema
promise is that a path or a description has no field to occupy. It was enforced on the inner
object and not on the envelope — and the envelope is the artifact that lands in the public
`corpus/`. Adding `"notes": {"type": "string"}` there put arbitrary prose through the gate with
zero errors, zero leak hits, and it survived `L27`'s continuous re-validation of every merged
bundle.

That gap had been *considered* the same day, while extending `L25` for arrays, and deferred as
scope. The reviewer found it four hours later.

Fixing `L34` then produced a third instance of a class fixed twice already the same day: the
first version compared the Makefile against the workflow's *text*, and `mypy` appears in
`pip install --quiet pytest mypy ruff`. Deleting the step left the check green because an
incidental mention propped it up. It now compares against the workflow's *commands*.

## What changed

`L34` asserts both directions, scoped to the `check` chain so that deliberately-not-in-CI
targets (`baseline`, `learn`) do not make it wrong instead of strict. `L25` walks both schemas,
honouring the same `x-validated-by` declaration the privacy gate honours. Both have breakers.

## Why this class matters

The general shape is **asymmetric verification**: checking that A implies B, and calling it a
guarantee that A and B agree. It is comfortable because the direction you check is the
direction you were worried about, and the other one usually holds by accident until it does
not.

| Checked | Unchecked, same pair |
|---|---|
| every CI command is in the shared gate | every shared-gate command is in CI |
| every schema field is constrained | every schema that admits fields is walked |
| the control arm lacks the skill | the treatment arm has it (`lessons/0011`) |
| every documented check has a test | every test asserts something a check does |
| every finding carries a fix | every fix was checked against what it breaks |

There is also a lesson about *when* this was found. It came from the first scheduled run of
`scripts/adversarial-review.sh` — a job built that afternoon to hand the repository to an
outside model on a rotation. Its first real execution found six things, three reproduced
mechanically, two of them in code written hours earlier by the person who had just written the
lesson that would have prevented one of them.

Which is the argument for the job, and against the belief that having *recorded* a class means
having internalised it. A lesson protects the code it was written about. It does not protect
the code you write next, ten minutes later, while remembering it.
