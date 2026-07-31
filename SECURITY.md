# Security policy

## Reporting a vulnerability in VIGIL

Use GitHub's **private vulnerability reporting** (Security → Report a vulnerability) rather
than a public issue. If that is unavailable, open an issue asking for a private channel —
without details.

Expect an acknowledgement within a few days. This is a small project; there is no SLA, and
saying so is more useful than promising one.

## What counts as a vulnerability here

VIGIL is a prompt-and-scripts skill. It has no server, no network listener and no runtime
dependencies beyond the standard library. The interesting attack surface is unusual, so it is
worth being explicit:

**In scope**

- **A rule an auditor follows that causes harm** — for example, prose that leads a model to
  run a destructive command against the audited repo. VIGIL is read by an agent with tool
  access; the instructions are the executable surface.
- **A path where VIGIL leaks audited content.** It reads private codebases. Anything causing
  findings, source, or a `.vigil/context.md` to end up somewhere they should not is a real
  vulnerability, not a bug.
- **A gate that can be made to pass while findings are unresolved** — suppression handling,
  the severity floor, N/E evidence gating, `--ci` exit codes. A security tool that can be made
  to report green is worse than no tool.
- Code execution or path traversal in `evals/*.py` or `tests/*.py`.

**Out of scope**

- VIGIL missing a vulnerability in your code. That is a *lesson*, not a vulnerability — see
  [`lessons/README.md`](lessons/README.md). It is the most valuable contribution here, but it
  goes through the normal, public path.
- Vulnerabilities in the tools VIGIL orchestrates (`semgrep`, `bandit`, `trivy`, …). Report
  those upstream; none are bundled here.
- Findings produced by running VIGIL against a third party without authorisation.

## Reporting one *with* your own code in it

Do not send us your codebase. If a report needs context you cannot share, describe the shape
and say so — a redacted report we can act on beats a complete one you should not have sent.

The same rule as lessons applies, and for the same reason: `.vigil/context.md` is designed to
enumerate your existential controls and critical paths, so pasting it into a report makes an
attack map with your name on it. See [`lessons/0006`](lessons/0006-context-file-is-an-attack-map.md),
which records this repo shipping exactly that.

## What this project does not claim

A clean VIGIL report means the configured checks found nothing on that run. It is not
certification, and it is not a substitute for professional security review or penetration
testing. See [`NOTICE`](NOTICE).

Most clusters currently declare no required tool, so much of the weighted average is
unevidenced by construction — tracked as **D1** in [`docs/OPEN-DESIGN.md`](docs/OPEN-DESIGN.md).
Anyone relying on a VIGIL score should read that first.

## Supported versions

Pre-1.0. Only `main` receives fixes. There are no backports.
