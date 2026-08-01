# Fourth review round — 2026-08-01

The **first scheduled run** of `scripts/adversarial-review.sh`, executed by the job built that
afternoon rather than by a person typing commands. Engine: Kimi (selected by the monthly
rotation), Docker sandbox, read-only mount, clean clone of `origin/main @ 8d8446d`.

**Six findings, three reproduced mechanically.** At the time the repository ran 36 structural
checks and 176 tests. They found none of the six.

Two of the three HIGHs were in code written **that same day**.

## Findings

### 1 · `L25` walked the record schema and not the envelope — HIGH · fixed

The closed-schema guarantee — "a path or a description has **no field to occupy**" — was
enforced on `run-record.schema.json` only. `bundle.schema.json` describes the artifact that is
actually committed to the public `corpus/`, and nothing walked it. `"notes": {"type":
"string"}` there passes the gate with zero errors, zero leak hits, and survives `L27`'s
re-validation of every merged bundle.

Considered and deferred as scope earlier the same day, while extending `L25` for arrays.

**Fixed:** `L25` walks both, honouring the `x-validated-by` declaration the privacy gate
honours. Breaker added.

### 2 · `L34` guarded one direction — HIGH · fixed

Asserted that every command CI runs is in the Makefile; never the reverse. Deleting the `mypy`
step from the workflow produced a **CLEAN** self-audit. A pull request could switch off part of
the merge gate with every check green.

`lessons/0011`, written that morning and the reason `L34` exists, states the fix in its own
words: *"the symmetric guard is the actual fix."* Applied there to the eval harness; not
applied to the check written beneath it.

**Fixed:** both directions, scoped to the `check` chain. Fixing it produced one more instance
of the incidental-text class — `mypy` appears in `pip install --quiet pytest mypy ruff`, so a
text comparison stayed green; it now compares commands. `lessons/0015`.

### 3 · Rule 1a Q1 and Q2 contradict inside one rule — HIGH · fixed

`# nosec … # reason` satisfied Q1 ("a comment claiming a mitigation" → enters at **Present**,
never resolves) *and* Q2 ("a suppression carrying a reason" → may fully withdraw). The same
artifact, two opposite dispositions, reopening "withdrawal cheaper than reduction" through a
second channel in the rule written to close it.

The reviewer also caught that Q2 credited a declaration's *existence* as settling the question.
`usedforsecurity=False` on a password hash is a true statement about the call and a false one
about the program — the declaration is then the finding.

**Fixed:** Q2 is now limited to what the compiler or runtime enforces; suppression comments are
explicitly Q1. Q2 requires asking whether the declaration is *correct* before it resolves
anything.

### 4 · `ci-adapter.md` exit 0 vs `scoring.md` — MEDIUM · fixed

`scoring.md:173`: a cluster below full coverage yields "INCOMPLETE — evidence partial",
**never a pass**. `ci-adapter.md`: exit 0 is "Pass", and partial evidence explicitly "does not
gate the exit code". A run with every cluster at ceiling 85 produced an INCOMPLETE verdict and
a green pipeline.

**Fixed:** partial evidence exits 1; zero evidence stays 2.

### 5 · `clause_holds` still defeatable — MEDIUM · documented, not fixed

A countermanding sentence placed **after** a clause, or a negation beyond the 260-character
lookback, reverses a rule with its check green. Both confirmed.

**Not fixed, deliberately.** Widening the window moves the next variant one sentence further
away; the check is a string matcher and the property is meaning. Recorded as **D10** in
`docs/OPEN-DESIGN.md` with what would actually close it. The reviewer flagged it as bordering a
known-open item, correctly, and reported it anyway because the mechanism was new — which is the
right call.

### 6 · `RULES.md` step 4 vs Rule 3a's fence — LOW · fixed

Rule 3 step 4 said "mark as `NEEDS_REVIEW` **not CRITICAL**", implying a downgrade. Rule 3a's
fence says a finding keeps its undiminished severity. **Fixed:** `NEEDS_REVIEW` is now
explicitly a mark at the existing severity.

## Sound surfaces

`install.sh` on a third independent look — truncation safety, clobber guard and remote
allowlist all hold. The privacy-gate validator core. The run-record schema. Makefile/CI parity
for commands that exist. Rule 7's floor fences. The `L36` suppression contract. The
implausibility guards in `adversarial-review.sh`.

One candidate — NaN bypassing numeric bounds — was tested and dropped as a false positive.
Reporting that is a result, not a failure to find something.

## The tally

| Round | Reviewer | Found |
|---|---|---:|
| 1 | Grok | 4 |
| 2 | Kimi | 4 |
| 3 | GPT-5.5 | 3 |
| 3 | direct attack on the checks | 2 |
| 4 | Kimi, scheduled | 6 |

**Automated suite: 0 of 19.** Four rounds, no decline in yield, no meaningful overlap.

The finding that matters most is not on the list. Two of these were in code written hours
earlier, one of them by someone who had that morning written the lesson stating the exact
principle the new check violated. A lesson protects the code it was written about. It does not
protect the code you write next while remembering it — which is the case for keeping an outside
reader in the loop permanently rather than until the checks feel sufficient.
