# Corpus

Contributed bundles. One file per contributor: `corpus/<handle>.json`.

This directory is the only place field data from other people exists. It is checked into git,
public, and permanent — so everything in it has passed
[`evals/privacy_gate.py`](../evals/privacy_gate.py), and `L27` re-checks every file on every
push rather than trusting that it did.

## What a bundle is

A wrapper around run records, plus the one identity field the system needs:

```json
{
  "schema_version": 1,
  "contributor": "your-handle",
  "vigil_version": "0.4.0",
  "records": [ { "...": "run records from your .vigil/runs/" } ]
}
```

**Attribution lives here and nowhere else.** Run records carry no install-id, machine-id or
repo-hash, so they cannot be linked to each other or to a person. Submitting means opening a
pull request, which is already a non-anonymous act — naming yourself in the envelope costs no
privacy the PR did not already spend. Pushing identity down into the records to make grouping
easier is exactly the trade this design refuses.

## Submitting

```bash
python3 evals/privacy_gate.py --dir .vigil/runs        # your local records
# assemble the bundle, then:
python3 evals/privacy_gate.py corpus/<handle>.json --bundles
```

The gate validates the envelope, then **every record inside it**, then scans the raw text. A
bundle is accepted or rejected whole: if one record smuggled a path, the redaction process
failed, and cherry-picking the clean ones would launder that.

## How it is read

```bash
python3 evals/learn.py --corpus corpus/
```

Rates are computed **per contributor and then contributors are counted**. One person with 50
runs gets one vote, the same as someone with two.

This is not politeness, it is correctness. Pooling rows breaks silently the moment one
contributor is heavier than the others: fifty runs against one unusual monorepo outvote nine
people, and the resulting rate looks well-evidenced because `n` is large. Nothing in the
numbers reveals it came from a single codebase — and by design nothing can, because records
carry no repo identity to group by. Counting people is the only grouping that survives having
no identifiers.

A signal needs **≥3 contributors with relevant data** and **≥60% of them agreeing**. Both
numbers are in `learn.py` and deliberately conservative: the output argues for changing a rule
that runs on everyone else's code.

## The corpus is untrusted input

Records are trivially fabricated. Nothing here can change a rule on its own — it can only
raise a question, and the question is answered by a human writing a lesson that explains
*why*. That is why the loop ends at a draft and not at a patch, and it is the same reason
[`CONTRIBUTING.md`](../CONTRIBUTING.md) asks for evidence rather than rule edits: evidence is
safe to accept from a stranger, an assertion about evidence is not.
