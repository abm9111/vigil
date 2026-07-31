# Engine: Run Records (self-learning input)

**Purpose:** let VIGIL learn from real use without ever ingesting the user's work.

Every other engine in this directory describes how to *produce* an audit. This one describes
what to keep afterwards, and — more importantly — what must be impossible to keep.

## The problem this solves

VIGIL's ledger renders lessons; nothing produced them. Every measurement in the repo therefore
came from VIGIL auditing itself, which is the weakest possible evidence about how it behaves on
someone else's code.

The naive fix is telemetry, and the naive telemetry is a disaster: an auditing tool that phones
home with findings is shipping a map of its users' vulnerabilities. `lessons/0006` records this
project doing a milder version of it to itself.

## The design

**Local by default. Content-free by construction. Shared only by an explicit human act.**

1. At the end of a run, write one record to `.vigil/runs/<timestamp>.json` in the audited repo.
2. That path is **gitignored by the user's own repo**, not by ours. It is their data.
3. **Nothing is transmitted. Ever.** VIGIL has no network egress for telemetry, no endpoint,
   no key. The only way a record leaves the machine is a human running
   `evals/privacy_gate.py`, reading the output, and choosing to attach it to a contribution.
4. The record is validated against [`../schemas/run-record.schema.json`](../schemas/run-record.schema.json),
   where every string is an enum and `additionalProperties` is false at every level.

That last point is the whole guarantee, and it is worth stating precisely:

> A repository name, file path, hostname, company, finding description or code excerpt is not
> *redacted* from a run record. It is **unrepresentable** — there is no field of the right
> shape for it to occupy, and an unknown field fails the gate.

Redaction is a filter, and filters have holes; `L19` exists and openly cannot read prose. A
closed schema has no holes of that kind. This is why the schema is the mechanism and the regex
scan in `privacy_gate.py` is only defence in depth: if a regex ever fires, the schema leaked
and the schema is the bug.

## What to record

Per run: mode, VIGIL version, detected stack (as a bounded enum), size and duration **buckets**.

Per cluster: its prefix, one of three verdicts, and counts.

| Verdict | Meaning |
|---|---|
| `scored` | a probe ran and produced evidence |
| `na` | genuinely not applicable — **must** cite an `na_trigger` |
| `ne` | applicable, but nothing could evidence it either way |

The `ne` count is the point. A cluster that is applicable across many real repos and never
produces evidence is carrying weight it cannot justify — which is **D1** in
[`../docs/OPEN-DESIGN.md`](../docs/OPEN-DESIGN.md), unanswerable by argument and answered
immediately by use.

Per finding, if the user dispositions it: prefix, severity, and one of `accepted`,
`false_positive`, `duplicate`, `deferred`, `wrong_severity`, `not_reachable`. This is the only
field in the record that carries a judgement *about VIGIL*, and it is what
[`../evals/learn.py`](../evals/learn.py) turns into a lesson candidate.

## What to record never

Not as a field, not appended to an enum, not encoded, not hashed:

- repository name, remote URL, or any path
- hostnames, IPs, emails, company or product names
- finding titles, descriptions, code excerpts, or commit messages
- exact file counts, exact timings, or any stable per-repo identifier

**A hash is not anonymisation.** A hashed repo path is a stable identifier that links every run
from one machine, and the input space is small enough to brute force. There is deliberately no
run-id or install-id field for this reason: records aggregate, they do not correlate.

## Ending a run: the consent contract

**A run does not end until the user has been told a record exists and asked what to do with
it.** Writing the file silently and leaving them to discover `privacy_gate.py` on their own is
consent by omission — the exact pattern a security tool has no business shipping.

Four rules, none of them optional.

### 1. Disclose on first write, in that repo

The first time a record is written to a repo, say so before anything else:

> Wrote a run record to `.vigil/runs/` — counts and cluster verdicts only, no paths or
> findings. It stays on this machine; VIGIL has no network path for it.
> Add `.vigil/` to `.gitignore`, or turn this off with `.vigil/telemetry: off`.

Once per repo, not once per run. A disclosure repeated every time is noise, and noise is how
people learn to skip the thing you most want them to read.

### 2. Ask for dispositions — this helps them, not us

> 3 findings. Mark any as false positives? VIGIL uses this to stop repeating them. (enter to skip)

Ask once, at the end, and make declining free. Never ask *why* in free text: the answer would
be the most useful sentence in the record and the most likely to name their system, which is
precisely the trade `lessons/0006` says not to make. The why belongs in a lesson the user
writes deliberately, having read [`../lessons/README.md`](../lessons/README.md).

### 3. Ask about sharing — separately, and never by default

Dispositions are local. Sharing is an export, and it is a **different question** that must be
asked as one:

> Share this run with the VIGIL project? It becomes a public file in `corpus/` under your
> GitHub handle.
>   [n] no  (default — nothing leaves this machine)
>   [s] show me exactly what would be sent
>   [y] yes, prepare a bundle I can attach to a PR

**The default is no, and enter must select it.** If the user says nothing, nothing is shared.

**`[s]` prints the record in full**, not a summary and not a description of the categories. The
record is a few dozen lines precisely because it is content-free, so informed consent here is
achievable in a way it never is for real telemetry — the user can read every byte in under a
minute. A tool that says "anonymous usage data" and shows nothing is asking for trust it has
not earned; this one can just show the file.

**`[y]` does not transmit anything.** It writes a bundle and prints the two commands the user
runs themselves. VIGIL has no endpoint and no credential; the transport is a pull request the
user opens, reviews and can abandon.

### 4. Ask at most once per run, and honour a no

A decline is recorded in `.vigil/telemetry.json` as `"share": "never"` and **is not asked
again** in that repo. Re-prompting someone who already declined is nagging, and nagging is how
a consent dialog becomes a dark pattern with a clean conscience.

`.vigil/telemetry: off` disables record writing entirely, including the disclosure. That
setting is checked before step 1 of this engine, not after.

## What must never happen

Each of these is a normal, defensible product decision somewhere else, and none of them are
available here:

- writing a record **after** the user set `telemetry: off`, for any reason including "just this
  diagnostic one"
- treating silence, `--yes`, `--ci` or a non-interactive session as consent to share —
  **non-interactive means no**, because there was nobody there to ask
- asking again after a `never`
- sharing anything at a moment the user did not initiate
- summarising the record instead of showing it when they ask to see it
- making `[y]` easier to reach than `[n]`, including by ordering, wording or emphasis

## Reading the result back

    python3 evals/privacy_gate.py --dir .vigil/runs     # clears records; fails closed
    python3 evals/learn.py --dir .vigil/runs            # the four aggregate signals
    python3 evals/learn.py --dir .vigil/runs --draft-lesson

`learn.py` refuses to aggregate any record the gate blocks. A learning pipeline that accepts
unvalidated input is how the private data arrived last time.

## What this deliberately does not do

It does not auto-file lessons. A lesson's value is the reasoning about *why* a rule was wrong,
and an aggregate cannot produce it — it can say a rule misfires, never why. Auto-filing would
fill `lessons/` with the one part of a lesson that is worthless on its own, and
`build_ledger.py` already refuses to reward lesson count for exactly this reason.

The loop ends at a draft. A human finishes it, or it does not get written.
