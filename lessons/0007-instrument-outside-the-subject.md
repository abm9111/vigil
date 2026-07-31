---
id: 0007
date: 2026-07-31
found_by: ci
missed_by: author, preflight
found_detail: the project's own CI ran the same tool inside the project environment and disagreed
missed_detail: preflight probed the tool and passed it; every local run agreed with itself
class: an instrument resolved outside the subject's environment fails silently clean
status: open
check:
---

# A type checker reported a codebase clean because it could not import the codebase's dependencies

## What was believed

That a static analyser which preflight had probed successfully — present on PATH, answering
`--version`, exit code 0 — was measuring the audited project. Its output was used to size a
remediation backlog, to decide which modules were already correct, and to write a
configuration file quarantining the rest.

## Why it was false

The binary on PATH belonged to a different environment than the project's. It could not import
the project's third-party dependencies at all. The analyser was invoked with a flag that
suppresses errors for unresolvable imports — a flag that is entirely reasonable when a few
stubs are missing, and catastrophic when *every* dependency is missing, because every
dependency-typed value silently degrades to `Any` and every real error against it disappears.

The evidence, once someone thought to look:

```
$ command -v mypy                     # what preflight probed
/somewhere/outside/the/project/bin/mypy
$ mypy src/           …  0 errors     # the instrument outside the environment
$ .venv/bin/mypy src/ …  6 errors     # the same command, the project's instrument
```

Both runs "passed" preflight. Both printed a plausible number. One of them was measuring a
project in which half the type information had been erased.

The failure direction is what makes this severe. A missing tool is loud — preflight already
reports it and caps the cluster. A *wrong* tool is quiet, and it fails toward **clean**. Every
downstream artefact inherited the error: the backlog count, the list of "already correct"
modules, and a committed config file asserting which modules were fine.

## What changed

Nothing yet, mechanically. The immediate correction was to re-run every measurement with the
environment-local binary and rebuild the artefacts derived from it.

The proposed mechanism is recorded as **D6**: preflight records, per tool, the *resolved
absolute path* and whether that path lies inside the project's environment, and treats
"resolved outside the subject environment" as a coverage reduction rather than a pass.

## Why this class matters

Preflight exists to stop VIGIL claiming coverage it does not have. It currently answers "does a
tool by this name run?" — which is a weaker question than "is this the tool that sees what the
subject sees?", and the gap between them is invisible in the output.

The shape generalises well beyond type checkers. Any analyser whose results depend on resolving
the subject's dependency graph has it:

- a linter with plugins installed in one environment and the code in another
- a dependency auditor reading a lockfile from a different resolution context
- a test runner collecting against a different interpreter than the one that ships
- any tool whose "cannot resolve X" mode is configured to be non-fatal

In every case the tool runs, exits 0, and reports less than the truth. `engines/preflight.md`
already argues that "an empty tool result is a tooling outcome, not a finding." This is the
sharper version: **an empty result from an instrument pointed at the wrong environment is not
even a tooling outcome — it is a measurement of something else.**
