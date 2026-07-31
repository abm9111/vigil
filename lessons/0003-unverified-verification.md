---
id: 0003
date: 2026-07-30
found_by: grok
missed_by: author, self-audit
found_detail: cross-model review
missed_detail: the author who wrote the claim; not a structural property
class: an unchecked claim wearing the words of a checked one
status: unmechanizable
check:
---

# A write-up said "each was manually verified" — one of them had not been

## What was believed

`evals/results/2026-07-30-run2.md` listed seven unseeded findings VIGIL had produced and
stated that "each was manually verified against the code before being accepted." One of the
seven, `DATA-002`, was then used to widen `acceptable_extra` in the fixture manifest.

## Why it was false

`DATA-002` claimed a left-join miss reaches the CSV as the literal string `"nan"`. It does not:

```python
df.merge(e, on='segment_code', how='left').to_csv()   # NaN -> empty field, not "nan"
```

`str()` at `build_export.py:33` runs only inside the list branch. The claim was also
unreachable in that fixture — both segment codes match in both files, so no left-join miss
exists at all. Three of the seven had genuinely been checked; that experience was generalised
into a sentence covering all seven.

## What changed

The `"nan"` allowance was removed from `acceptable_extra`. The run-2 write-up carries a
**Correction** section rather than a silent edit, and `acceptable_extra_provenance` records
that this happened once, here, so a future reader can distinguish a corrected manifest from a
moved goalpost.

## Why this class matters

This is the failure the surrounding document was written to prevent, occurring inside the
guard itself. It is deliberately marked **unmechanizable**: no check can determine whether a
human verified something they said they verified. That limit is worth stating plainly, because
the ledger's own entries are subject to it — including this one.

The only defence found so far is an independent reader. It is the strongest argument in this
repo for keeping cross-model review in the loop rather than assuming the harness replaced it.
