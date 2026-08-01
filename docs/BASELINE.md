# Running the baseline

The with/without-VIGIL comparison. It answers the question every other number here depends on —
*does the skill beat a competent prompt?* — and it is allowed to come back negative.

**Read this before spending anything.** The procedure looks over-engineered until you see what
each guard is for; every one of them exists because the obvious version produced a confident,
wrong number.

## The short version

```bash
scripts/run-baseline.sh /tmp/bl 5      # <outdir> <runs-per-arm>
```

Three steps, deliberately separate:

| Step | Precondition it verifies | Cost |
|---|---|---|
| `--arm control` | the skill is **absent** | one run per fixture |
| `--arm vigil` | the skill is **present** | one run per fixture |
| `--compare` | — | free, no CLI calls |

## `--runs 5` is a floor, not a suggestion

The same arm, on the same fixture, with identical code, has returned **0% and 83% recall** on
two consecutive draws. One run measures the draw, not the tool
([`../evals/results/2026-08-01-baseline-variance.md`](../evals/results/2026-08-01-baseline-variance.md)).

Anything below 5 is not a measurement, and reporting it as one is how this harness produced a
false headline the first time it ran.

## Why the arms are separate processes

The first version ran both arms in one process, so isolating the control meant isolating
everything — the wrapper removed the skill and the *treatment* arm ran without it too. It
scored 0%, and the harness reported *"VIGIL beat the control on 0/2 fixtures."*

Separate processes let each arm assert its own precondition, and the **symmetric guard** is the
actual fix: nothing had checked that the treatment arm *had* the skill.

## Isolation is physical, and everything else was tried

| Approach | Why it fails |
|---|---|
| `CLAUDE_CONFIG_DIR` → fresh dir | severs credentials; auth lives in the Keychain, the arm cannot run |
| `--disable-slash-commands` | documented as *"Disable all skills"* — **it does not hide them**, the model still lists every one |
| stash inside `~/.claude/skills/` | still discoverable under the new directory name |

So: the skill is moved **out of the skills tree entirely**, for the control pass only, by
`scripts/run-baseline.sh`, which restores it via a trap on `EXIT INT TERM HUP`. Verified to
restore after a kill.

The guards scan for a `SKILL.md` declaring `name: vigil` **following symlinks** — `Path.rglob`
does not, and a skill under development is a symlink into its working copy, so the check was
blind in the commonest install shape.

## Reading the output honestly

- **A null result is a result.** The control prompt in
  [`../evals/baseline-prompt.md`](../evals/baseline-prompt.md) is deliberately strong: it is
  handed the severity vocabulary, tools-before-opinion, and six named coverage areas.
  Strengthening it is always allowed; weakening it to improve the delta is gaming the benchmark.
- **Recall alone is not improvement.** The verdict requires recall up *and* false positives not
  up. A skill that finds more by inventing more has improved nothing.
- **`implausible()` excludes what it cannot trust.** 0% recall across every run on a fixture
  that seeds defects is flagged and left out of the count — a warning, never a refusal, because
  auto-discarding a low score would be the thumb on the scale this project refuses elsewhere.
- **Transcripts are saved** beside the scores. A 0% is otherwise ambiguous between "found
  nothing" and "the scorer did not match what it found", and telling them apart used to mean
  paying for the run again.

## What no run count fixes

Both fixtures are small synthetic repos written by this project. This anchors *fixture*
numbers, not field performance. A real answer needs both arms against a real codebase with
independently established ground truth — see **D5** in
[`OPEN-DESIGN.md`](OPEN-DESIGN.md).
