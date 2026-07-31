# VIGIL Cluster: Data Egress & Provenance

**Covers:** What leaves the repo, whether it is labelled honestly, and whether its integrity can be proven
**Weight:** 10%
**ID prefix:** VIGIL-EGRESS
**Applies when:** the project produces data artifacts — exports, bundles, dumps, reports, datasets, model outputs, generated documents. Not just web apps.

## Why this cluster exists

The other clusters guard a running system against an attacker. This one guards a **consumer
downstream** against trusting an artifact more than the evidence warrants. There is no
adversary in most of these findings; the damage is done by an honest person acting on data
that was quietly wrong.

Three failure shapes, none of which the web-app clusters detect:

1. **Egress** — sensitive source data is one `git add -A` from disclosure, while the curated
   export that *was* reviewed goes out clean. The review protected the wrong file.
2. **Provenance** — machine-generated content ships without a label and is read as
   authoritative. Fluent prose is the most dangerous payload here, not code.
3. **Integrity theatre** — a checksum, manifest or signature exists but proves nothing,
   because it is self-certifying or the build is not reproducible.

## Deterministic Tools

### A. What actually leaves

```bash
# Generated/exported artifacts — the things that travel
find . -type d \( -name 'export*' -o -name 'dist' -o -name 'build' -o -name '_deploy' \
  -o -name 'out' -o -name 'artifacts' \) -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null

find . -maxdepth 3 \( -name '*.zip' -o -name '*.tar.gz' -o -name '*.7z' -o -name '*.dump' \
  -o -name '*.sqlite' -o -name '*.parquet' -o -name '*.xlsx' \) -not -path '*/node_modules/*' 2>/dev/null

# Is each one ignored, or one `git add -A` from being committed?
for f in $(find . -maxdepth 4 \( -name '*.zip' -o -name '*.sqlite' -o -name '*.dump' \) \
  -not -path '*/node_modules/*' 2>/dev/null); do
  git check-ignore -q "$f" && echo "IGNORED   $f" || echo "EXPOSED   $f"
done

# Upload / transmission calls — where does data go?
grep -rn -E 'boto3|s3\.upload|put_object|requests\.(post|put)\(|httpx\.(post|put)\(|\bscp\b|rsync|\bcurl -[A-Za-z]*[TF]|drive\.files\.create|WeTransfer|dropbox' \
  . --include='*.py' --include='*.ts' --include='*.js' --include='*.sh' \
  --exclude-dir={node_modules,.venv,.git,dist} 2>/dev/null | head -20
```

### B. PII in files, not tables

`domains/pii-deep.md` greps ORM models. That will never fire on a 17 MB JSON of named
entities sitting beside the code. Scan the **data**, not only the schema:

```bash
# Candidate raw datasets
find . \( -name '*.json' -o -name '*.csv' -o -name '*.ndjson' -o -name '*.parquet' \) \
  -size +100k -not -path '*/node_modules/*' -not -path '*/.venv/*' 2>/dev/null | head -20

# Identifier-shaped keys inside them (sample the head — do not load 17MB into context)
for f in $(find . -name '*.json' -size +100k -not -path '*/node_modules/*' 2>/dev/null | head -5); do
  echo "── $f"
  head -c 4000 "$f" | grep -oE '"(name|nameEn|nameAr|email|phone|mobile|licen[cs]eNo|registrationNo|trn|iban|passport|nationalId|address|dob)"' \
    | sort -u | tr '\n' ' '; echo
done
```

**Then prove the direction of travel.** Do not assume the curated export excluded the raw
records — verify it, because this is exactly the claim that feels true and is cheap to check:

```bash
# Take real identifier values from the raw file, search for them in the shipped artifact.
# A zero-hit result is only meaningful if you confirm the needles were real.
python3 - <<'PY'
import json, pathlib
raw  = json.load(open('RAW.json'))
ship = pathlib.Path('export/csv/activities.csv').read_text(encoding='utf-8-sig')
names = {b['nameEn'] for b in raw.values() if b.get('nameEn')}
needles = [n for n in list(names)[:2000] if len(n) > 12]
print("needles tested:", len(needles), "-> leaked:", sum(n in ship for n in needles))
PY
```

⚠️ **Numeric collision is not leakage.** Identifier-shaped numbers (6–8 digits) collide by
coincidence with counts, classification codes and totals. Before reporting numeric overlap,
locate the *column* the colliding values sit in. A classification code that happens to share
a range with a licence number is a false positive, and Rule 3 says a false positive costs more
than a miss.

### C. Provenance & labelling

```bash
# Machine-generated content shipped as data
grep -rn -E 'llm|gpt|claude|qwen|llama|mistral|generated_by|_enriched_by|synthetic|ai_summary' \
  --include='*.json' --include='*.py' --include='*.ts' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null | head -20

# Provenance constants — duplicated ones drift
grep -rn -E '^[A-Z_]*(SNAPSHOT|VERSION|AS_OF|VINTAGE|GENERATED|BUILD_DATE)[A-Z_]* *=' \
  --include='*.py' --include='*.ts' . --exclude-dir={node_modules,.venv} 2>/dev/null

# Does the artifact ship its own caveats?
ls export/ dist/ 2>/dev/null | grep -iE 'readme|dictionary|caveat|limitation|schema|license'
```

Then answer three questions in the report:

1. **Which shipped columns are model-generated?** Count them and count their rows.
2. **Is that stated in the document the recipient will actually read?** A caveat in a data
   dictionary that the README does not reference is not disclosure. People read the README.
3. **Does the generated content look authoritative?** Fluent natural-language prose in the
   consumer's own language is the highest-risk form — it reads like guidance from the source
   organisation. Flag `summary`, `description`, `recommendation`, `advice` fields hardest.

### D. Integrity contracts

```bash
# Reproducibility: build twice, compare. Non-determinism breaks every checksum workflow.
BUILD_CMD='python3 build_export.py'
$BUILD_CMD >/dev/null 2>&1 && find export -type f | sort | xargs shasum -a 256 > /tmp/vigil.r1
$BUILD_CMD >/dev/null 2>&1 && find export -type f | sort | xargs shasum -a 256 > /tmp/vigil.r2
diff -q /tmp/vigil.r1 /tmp/vigil.r2 && echo "REPRODUCIBLE" || { echo "NON-DETERMINISTIC:"; diff /tmp/vigil.r1 /tmp/vigil.r2 | head; }

# Self-certifying manifest — a checksum inside the archive it certifies proves nothing
find . -name 'MANIFEST*' -o -name '*.sha256' -o -name 'checksums*' 2>/dev/null

# Destructive operations ordered before the validation that would abort them
grep -rn -E 'rmtree|shutil\.rmtree|os\.remove|unlink\(|DROP TABLE|TRUNCATE|--force|-rf ' \
  --include='*.py' --include='*.sh' --include='*.sql' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null | head -20
```

For each destructive call found, read the enclosing function and check **ordering**: does the
irreversible step run before the read/validate that could fail? If so it is a finding — a
failed run destroys the last good artifact and leaves nothing.

### E. Encoding & format contracts

The class of defect that corrupts data silently on the receiving side. Every item here is a
documented promise; each one is testable:

```bash
# BOM present? (Excel on Windows reads BOM-less UTF-8 as ANSI → Arabic/CJK becomes mojibake)
head -c 3 export/csv/*.csv | xxd | head -2      # expect efbbbf

# Line endings
file export/csv/*.csv

# Leading-zero identifiers preserved as text?
python3 -c "import csv,io;r=list(csv.reader(io.open('export/csv/x.csv',encoding='utf-8-sig')));i=r[0].index('code');print('zero-prefixed:',sum(1 for x in r[1:] if x[i].startswith('0')))"

# Multi-value delimiter collision — if the documented separator occurs inside a value,
# the documented split silently corrupts data downstream
grep -c ' | ' export/csv/*.csv
```

## What to report, and at what severity

| Finding | Typical severity | Escalate when |
|---------|------------------|---------------|
| Raw PII/records dataset not gitignored | MEDIUM | HIGH if a remote is configured or the file is already committed |
| Model-generated fields shipped unlabelled | MEDIUM | HIGH if crossing an org boundary, or if the field is prose in the reader's language |
| Destructive op before validation | HIGH | CRITICAL if it targets the only copy |
| Non-reproducible build with a checksum workflow | MEDIUM | HIGH if the checksum is the stated integrity control |
| Self-certifying manifest | LOW | MEDIUM if it is presented to a recipient as verification |
| Duplicated provenance constant | MEDIUM | HIGH if the artifact asserts that date to a third party |
| Encoding/delimiter contract undefended | MEDIUM | HIGH if the contract is documented for a recipient but unenforced |
| Artifact ships without its caveats | MEDIUM | HIGH if the data has known validity limits (sampling, staleness) |

## Judgement notes

- **Absence of a field is not absence of the thing.** An empty `requirements` column may mean
  "none required" or "the scrape failed." Which one changes every conclusion drawn from it.
  If the pipeline cannot distinguish them, that is the finding.
- **Aggregates are not records — but verify the aggregation.** "Only counts travel" is a
  claim, and claims of this shape are the ones worth testing, not asserting.
- **A stale dataset is a correctness risk, not a hygiene one.** If the artifact carries no
  as-of date, a recipient will assume it is current. Silence defaults to "now."
- **Do not flag every generated file.** Build outputs are meant to be generated. The finding
  is a generated artifact that is *indistinguishable from source*, or one whose provenance is
  asserted rather than derived.
