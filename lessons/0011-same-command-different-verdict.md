---
id: 0011
date: 2026-08-01
found_by: ci
missed_by: author, self-audit, grok, kimi, Makefile
found_detail: three consecutive pushes went red on a hosted runner while make check stayed green on the maintainer's machine
missed_detail: the Makefile header already promised "exactly what CI runs — green here means green there", and two cross-model reviews read that file without testing the claim
class: a shared gate definition does not produce a shared verdict; the environment is part of the gate
status: mechanized
check: L34
---

# `make check` claimed to be exactly what CI runs, and was green while CI was red for three commits

## What was believed

That `lessons/0010`'s CI/local split was closed. The fix then was *one definition of the
gate*: a Makefile whose `check` target is the same list of commands the workflow runs, with
a header saying so. Sharing the definition was taken to mean sharing the verdict.

## Why it was false

Three separate divergences existed simultaneously in the file that promised none could.

**1. The commands were not actually the same.**

```make
lint:
	ruff check evals/*.py tests/*.py     # Makefile
```
```yaml
        run: ruff check .                # CI
```

`scripts/` and `examples/` were linted in one place and not the other. Nobody noticed because
both were green.

**2. A whole CI step had no Makefile equivalent.** The privacy gate — the mechanism protecting
contributors — ran in CI and not in `make check`. A contributor could get a green local gate
and have their bundle rejected on push. This one was found by the check written for (1), not
by reading.

**3. The commands matched exactly and the verdicts still differed.**

This is the part no command comparison catches. `evals/run_eval.py` had:

```python
def assert_skill_invisible(model):
    r = subprocess.run(["claude", "-p", "List the names of every skill..."])   # first
    ...
    found = _vigil_installed()                                                # second
```

The free filesystem check ran *after* the paid model probe. On a machine with the CLI that
exits 2 for the right reason and looks correct. On a hosted runner there is no `claude`, so
`subprocess.run` raises `FileNotFoundError` before the check is reached:

```
FAILED tests/test_baseline_guards.py::test_control_guard_refuses_when_the_skill_is_present
  FileNotFoundError: [Errno 2] No such file or directory: 'claude'
```

Reproducible locally in one line — the environment was never varied, so it was never seen:

```bash
env PATH="$(dirname "$(command -v python3)"):/usr/bin:/bin" pytest tests/ -q
```

The test asserting the ordering had a docstring stating it exactly — *"Must exit BEFORE the
model probe"* — and asserted only `SystemExit(2)`, which the wrong ordering also produces
wherever the CLI happens to exist. It was green for a reason unrelated to its claim.

Its sibling made that worse:

```python
def _passes(fn) -> bool:
    try: fn(None)
    except SystemExit: return False
    except Exception: return False   # a CRASH read as a refusal
    return True
```

## What changed

- The free check moved above the probe in `assert_skill_invisible`, matching
  `assert_skill_visible`, which had been correct all along. The asymmetry was the bug.
- `_passes` catches `SystemExit` only. A crash is no longer indistinguishable from a refusal.
- Two tests replace the CLI with a function that raises, so the ordering claim is enforced
  rather than asserted in a docstring.
- `make test` runs with `PATH` restricted to the interpreter's directory plus `/usr/bin:/bin`,
  so the local gate has CI's environment and not the maintainer's.
- `make lint` runs `ruff check .`; `make privacy` was added.
- **L34** compares the two files: every tool invocation CI runs must appear in a Makefile
  recipe, and the `test` recipe must restrict `PATH`.

L34 needed three corrections before it worked, each of which is the same failure in miniature:
it compared only multi-line `run: |` blocks and so skipped every single-line step including
the `ruff` one it existed to catch; `"PATH=" in body` also accepted `NOPATH=`; and comparing
against the whole Makefile let the *comment explaining why lint must run `ruff check .`*
satisfy the check for the recipe. A gate its own documentation can satisfy is `L21` again.

## Why this class matters

`0010` was about the auditor and the subject disagreeing on **which tree**. This is the same
shape one level up: the auditor and CI disagree on **which machine**, and the report cannot
say so.

A gate is a command *and* an environment. Only one of those is usually written down, and the
unwritten half is supplied by whoever is running it — which is exactly why the divergence
appears as "works on my machine" rather than as a diff. The general form:

| Written | Unwritten, and supplied locally |
|---|---|
| the test command | which binaries are on `PATH` |
| the build command | the toolchain version resolved |
| the container's `CMD` | the env vars the orchestrator injects |
| the migration script | the extensions the target database has installed |

For VIGIL specifically: a preflight that resolves a tool on the auditor's machine (`L30`) says
nothing about whether it resolves inside the subject's CI. A finding of "no SAST configured"
against a repo whose scanner runs only in a hosted pipeline is this same mistake, made about
somebody else's code.

The narrower lesson is about paying to learn something free: a guard that spends a CLI call
before consulting the filesystem is not merely slow, it is **unrunnable anywhere the CLI is
absent** — and the places it is absent are exactly the automated ones that would have caught
the fault.
