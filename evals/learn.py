#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""Turn local run records into the things VIGIL should learn.

Until now VIGIL's learning loop had an output half and no input half: `build_ledger.py`
renders lessons, but a lesson only existed if a human sat down and wrote one. Every number in
the repo therefore came from VIGIL auditing itself.

This reads the run records a real user accumulates in `.vigil/runs/` and reports the four
signals that are visible in aggregate and invisible in any single run:

  1. NO-EVIDENCE RATE per cluster. A cluster that is applicable but never produces evidence is
     carrying weight it cannot justify. Across many real repos this is the empirical answer to
     D1 in docs/OPEN-DESIGN.md, which no amount of reasoning from the armchair settles.
  2. FALSE-POSITIVE RATE per prefix. The only signal that says VIGIL was wrong. Above the
     threshold it is a lesson waiting to be written.
  3. MISSING TOOLS. What preflight assumed and reality did not have.
  4. N/A TRIGGERS. scoring.md treats an unexplained N/A as the cheap escape; this shows whether
     the triggers are actually being cited.

Records are gated by `privacy_gate.py` before anything is read from them. An ungated record is
never aggregated — a learning pipeline that quietly accepts unvalidated input is how the
private data got in last time (`lessons/0006`).

    python3 evals/learn.py --dir .vigil/runs
    python3 evals/learn.py --dir .vigil/runs --draft-lesson
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from privacy_gate import GateError, check_bundle, check_file

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "run-record.schema.json"
BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "bundle.schema.json"

# A signal needs both a rate and a floor. Two false positives out of two runs is noise; the
# floor is what stops a single unlucky repo from rewriting a rule.
MIN_RUNS = 5
FP_RATE = 0.30
NE_RATE = 0.50

# Corpus mode. These exist because pooled counting breaks the moment there is more than one
# contributor, and it breaks silently.
#
# One person who runs VIGIL fifty times against the same unusual monorepo produces more rows
# than nine people running it twice each. Pool the rows and that one repo's quirks read as a
# property of VIGIL, with an impressive-looking n behind them. Nothing in the numbers says the
# evidence came from a single codebase — and by design nothing can, because records carry no
# repo identity to group by.
#
# So the corpus statistic is deliberately not "how many findings" but "how many CONTRIBUTORS
# independently see this". A rate is computed per contributor and then contributors are
# counted; one person's volume cannot move it. That is strictly less sensitive than pooling,
# which is the correct direction for a signal that argues for changing a rule.
MIN_CONTRIBUTORS = 3
MIN_AGREEMENT = 0.60      # of contributors who have relevant data, this share must agree


def load(dirpath: Path) -> list[dict[str, Any]]:
    """Load every record, refusing any that the privacy gate blocks."""
    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot load schema: {exc}") from exc

    records: list[dict[str, Any]] = []
    for path in sorted(dirpath.glob("*.json")):
        try:
            errs = check_file(path, schema)
        except GateError as exc:
            errs = [str(exc)]
        if errs:
            print(f"skipping {path.name}: blocked by privacy gate ({errs[0]})", file=sys.stderr)
            continue
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def report(records: list[dict[str, Any]]) -> list[str]:
    """Render the aggregate. Returns the lines so tests can assert on them."""
    out: list[str] = []
    a = out.append
    n = len(records)
    a(f"# What {n} run(s) say VIGIL should learn")
    a("")
    if n < MIN_RUNS:
        a(f"⚠️  {n} runs is below the {MIN_RUNS}-run floor. Rates below are shown for "
          "orientation only — do not change a rule on this evidence.")
        a("")

    # 1. no-evidence rate ------------------------------------------------------------
    seen: Counter[str] = Counter()
    ne: Counter[str] = Counter()
    na_by: dict[str, Counter[str]] = defaultdict(Counter)
    for rec in records:
        for cluster in rec.get("clusters", []):
            prefix = cluster["prefix"]
            verdict = cluster["verdict"]
            if verdict == "na":
                na_by[prefix][cluster.get("na_trigger", "UNEXPLAINED")] += 1
                continue
            seen[prefix] += 1          # applicable runs only — N/A is not a failure to evidence
            if verdict == "ne":
                ne[prefix] += 1

    a("## 1. Clusters that are applicable but produce no evidence")
    a("")
    a("The D1 question, answered by use rather than by argument.")
    a("")
    a("| Cluster | Applicable runs | No evidence | Rate |")
    a("|---|---|---|---|")
    for prefix in sorted(seen, key=lambda p: (-(ne[p] / seen[p]), p)):
        rate = ne[prefix] / seen[prefix]
        flag = " ⚠️" if rate >= NE_RATE and seen[prefix] >= MIN_RUNS else ""
        a(f"| {prefix} | {seen[prefix]} | {ne[prefix]} | {rate:.0%}{flag} |")
    a("")

    # 2. false positives ------------------------------------------------------------
    disp: dict[str, Counter[str]] = defaultdict(Counter)
    for rec in records:
        for outcome in rec.get("outcomes", []):
            disp[outcome["prefix"]][outcome["disposition"]] += 1

    a("## 2. Where VIGIL was told it was wrong")
    a("")
    a("`false_positive` and `wrong_severity` are the only fields in the whole record that "
      "carry a judgement about VIGIL. Everything else describes the run.")
    a("")
    a("| Prefix | Findings | False positive | Wrong severity | FP rate |")
    a("|---|---|---|---|---|")
    for prefix in sorted(disp):
        counts = disp[prefix]
        total = sum(counts.values())
        fp = counts["false_positive"]
        rate = fp / total if total else 0.0
        flag = " ⚠️" if rate >= FP_RATE and total >= MIN_RUNS else ""
        a(f"| {prefix} | {total} | {fp} | {counts['wrong_severity']} | {rate:.0%}{flag} |")
    a("")

    # 3. missing tools --------------------------------------------------------------
    missing: Counter[str] = Counter()
    for rec in records:
        missing.update(rec.get("tools", {}).get("missing", []))
    a("## 3. Tools preflight wanted and reality did not have")
    a("")
    if missing:
        for tool, count in missing.most_common():
            a(f"- `{tool}` missing in {count} run(s)")
    else:
        a("_none recorded_")
    a("")

    # 3b. evidence ceilings ----------------------------------------------------------
    # The most direct D1 evidence in the record. A cluster that scores but is capped below
    # 100 is telling you, per run, that no probe specific to it exists — so its contribution
    # to the weighted average is bounded by what could not be checked.
    capped: dict[str, list[int]] = defaultdict(list)
    for rec in records:
        for cluster in rec.get("clusters", []):
            ceiling = cluster.get("ceiling")
            if isinstance(ceiling, int):
                capped[cluster["prefix"]].append(ceiling)
    a("## 3b. Evidence ceilings — D1, straight from the record")
    a("")
    if capped:
        a("| Cluster | Runs | Median ceiling | Ever reached 100? |")
        a("|---|---|---|---|")
        for prefix in sorted(capped, key=lambda p: sum(capped[p]) / len(capped[p])):
            vals = sorted(capped[prefix])
            med = vals[len(vals) // 2]
            flag = " ⚠️" if med < 100 else ""
            a(f"| {prefix} | {len(vals)} | {med}{flag} | "
              f"{'yes' if max(vals) >= 100 else '**no**'} |")
        a("")
        a("A cluster that never reaches 100 has no probe of its own. That is not a scoring "
          "quirk — it is the weighted average resting on something unmeasured.")
    else:
        a("_no ceilings recorded_")
    a("")

    # 4. n/a discipline --------------------------------------------------------------
    a("## 4. Is N/A being justified?")
    a("")
    unexplained = sum(c["UNEXPLAINED"] for c in na_by.values())
    if unexplained:
        a(f"⚠️  **{unexplained} N/A verdict(s) cite no trigger.** scoring.md treats an "
          "unexplained N/A as the cheapest way to raise a score without doing work.")
    else:
        a("Every N/A cites a trigger.")
    a("")
    return out


def load_corpus(dirpath: Path) -> dict[str, list[dict[str, Any]]]:
    """Load contributed bundles, keyed by contributor. Blocked bundles are dropped entirely.

    A bundle is rejected whole rather than record-by-record: if one record in a submission
    smuggled a path, the submitter's redaction process is what failed, and cherry-picking the
    clean ones would quietly launder that.
    """
    try:
        record_schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        bundle_schema = json.loads(BUNDLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot load schema: {exc}") from exc

    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in sorted(dirpath.rglob("*.json")):
        try:
            errs = check_bundle(path, bundle_schema, record_schema)
        except GateError as exc:
            errs = [str(exc)]
        if errs:
            print(f"skipping {path.name}: blocked by privacy gate ({errs[0]})", file=sys.stderr)
            continue
        bundle = json.loads(path.read_text(encoding="utf-8"))
        out[bundle["contributor"]].extend(bundle["records"])
    return dict(out)


def _ne_rates(records: list[dict[str, Any]]) -> dict[str, float]:
    seen: Counter[str] = Counter()
    ne: Counter[str] = Counter()
    for rec in records:
        for cluster in rec.get("clusters", []):
            if cluster["verdict"] == "na":
                continue
            seen[cluster["prefix"]] += 1
            if cluster["verdict"] == "ne":
                ne[cluster["prefix"]] += 1
    return {p: ne[p] / seen[p] for p in seen}


def _fp_rates(records: list[dict[str, Any]]) -> dict[str, float]:
    total: Counter[str] = Counter()
    fp: Counter[str] = Counter()
    for rec in records:
        for outcome in rec.get("outcomes", []):
            total[outcome["prefix"]] += 1
            if outcome["disposition"] == "false_positive":
                fp[outcome["prefix"]] += 1
    return {p: fp[p] / total[p] for p in total}


def corpus_report(by_contributor: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Cross-contributor aggregate. Counts people, not rows."""
    out: list[str] = []
    a = out.append
    people = len(by_contributor)
    runs = sum(len(v) for v in by_contributor.values())

    a(f"# Corpus: {runs} run(s) from {people} contributor(s)")
    a("")
    if people < MIN_CONTRIBUTORS:
        a(f"⚠️  {people} contributor(s) is below the {MIN_CONTRIBUTORS}-contributor floor. "
          "Nothing here is a signal yet — with one or two submitters you are measuring their "
          "codebases, not VIGIL.")
        a("")

    # Volume, stated up front. A reader should see skew before they see rates.
    a("## Who submitted what")
    a("")
    a("Shown because rates below are computed **per contributor and then counted**, so this "
      "table is context, not weight. One person with 50 runs gets exactly one vote.")
    a("")
    a("| Contributor | Runs | Share |")
    a("|---|---|---|")
    for who, recs in sorted(by_contributor.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        a(f"| {who} | {len(recs)} | {len(recs) / runs:.0%} |")
    a("")

    for title, fn, threshold, blurb in (
        ("No-evidence by cluster", _ne_rates, NE_RATE,
         "Contributors for whom this cluster was applicable but produced no evidence in at "
         "least half their runs. This is D1, measured."),
        ("False-positive rate by prefix", _fp_rates, FP_RATE,
         "Contributors who dismissed at least 30% of this prefix's findings as wrong."),
    ):
        per: dict[str, list[float]] = defaultdict(list)
        for recs in by_contributor.values():
            for key, rate in fn(recs).items():
                per[key].append(rate)

        a(f"## {title}")
        a("")
        a(blurb)
        a("")
        a("| Key | Contributors with data | Above threshold | Agreement | Signal |")
        a("|---|---|---|---|---|")
        for key in sorted(per, key=lambda k: (-len([x for x in per[k] if x >= threshold]), k)):
            rates = per[key]
            over = [x for x in rates if x >= threshold]
            agreement = len(over) / len(rates)
            signal = (len(rates) >= MIN_CONTRIBUTORS and agreement >= MIN_AGREEMENT)
            a(f"| {key} | {len(rates)} | {len(over)} | {agreement:.0%} | "
              f"{'⚠️ yes' if signal else 'no'} |")
        a("")

    # Stack skew — the mistake that would otherwise be invisible.
    stacks: Counter[str] = Counter()
    for recs in by_contributor.values():
        for rec in recs:
            stacks.update(rec.get("stack", []))
    a("## Stack coverage")
    a("")
    a("A no-evidence rate drawn from ten Python repos says nothing about Go. Read every "
      "signal above as scoped to this distribution.")
    a("")
    for stack, n in stacks.most_common():
        a(f"- `{stack}` in {n} run(s)")
    a("")

    versions = {rec.get("vigil_version", "?")
                for recs in by_contributor.values() for rec in recs}
    if len(versions) > 1:
        a(f"⚠️  Corpus mixes VIGIL versions {sorted(versions)}. A rule that changed between "
          "them makes the pooled rate meaningless for that cluster.")
        a("")
    return out


def corpus_candidates(by_contributor: dict[str, list[dict[str, Any]]]) -> list[tuple[str, str]]:
    """Signals that clear both the contributor floor and the agreement bar."""
    out: list[tuple[str, str]] = []
    if len(by_contributor) < MIN_CONTRIBUTORS:
        return out
    for label, fn, threshold, cls in (
        ("returned NO EVIDENCE", _ne_rates, NE_RATE,
         "cluster carries weight it cannot evidence"),
        ("was dismissed as a false positive", _fp_rates, FP_RATE,
         "rule fires on a shape it should not"),
    ):
        per: dict[str, list[float]] = defaultdict(list)
        for recs in by_contributor.values():
            for key, rate in fn(recs).items():
                per[key].append(rate)
        for key in sorted(per):
            rates = per[key]
            over = [x for x in rates if x >= threshold]
            if len(rates) >= MIN_CONTRIBUTORS and len(over) / len(rates) >= MIN_AGREEMENT:
                out.append((cls, f"{key} {label} above threshold for {len(over)} of "
                                 f"{len(rates)} contributors who had data for it"))
    return out


def candidates(records: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Signals strong enough to justify writing a lesson. (class, why) pairs."""
    out: list[tuple[str, str]] = []
    if len(records) < MIN_RUNS:
        return out

    disp: dict[str, Counter[str]] = defaultdict(Counter)
    for rec in records:
        for outcome in rec.get("outcomes", []):
            disp[outcome["prefix"]][outcome["disposition"]] += 1
    for prefix, counts in sorted(disp.items()):
        total = sum(counts.values())
        if total >= MIN_RUNS and counts["false_positive"] / total >= FP_RATE:
            out.append((
                "rule fires on a shape it should not",
                f"{prefix} was dismissed as a false positive in "
                f"{counts['false_positive']}/{total} findings across {len(records)} runs",
            ))

    seen: Counter[str] = Counter()
    ne: Counter[str] = Counter()
    for rec in records:
        for cluster in rec.get("clusters", []):
            if cluster["verdict"] == "na":
                continue
            seen[cluster["prefix"]] += 1
            if cluster["verdict"] == "ne":
                ne[cluster["prefix"]] += 1
    for prefix in sorted(seen):
        if seen[prefix] >= MIN_RUNS and ne[prefix] / seen[prefix] >= NE_RATE:
            out.append((
                "cluster carries weight it cannot evidence",
                f"{prefix} returned NO EVIDENCE in {ne[prefix]}/{seen[prefix]} applicable runs",
            ))
    return out


def draft(signals: list[tuple[str, str]]) -> str:
    """A lesson stub. Deliberately incomplete — the reasoning is the contribution."""
    lines = ["---", "id: NNNN", "date: YYYY-MM-DD", "found_by: field-telemetry",
             "missed_by: self-audit", "found_detail: aggregated from local run records",
             "missed_detail: FILL IN", f"class: {signals[0][0]}", "status: open", "check: ",
             "---", "", "# FILL IN — one sentence naming what VIGIL believed and was wrong about",
             "", "## What was believed", "", "FILL IN", "", "## Why it was false", ""]
    for _, why in signals:
        lines.append(f"- {why}")
    lines += [
        "", "## What changed", "", "FILL IN — and prefer a check over a patch.", "",
        "## Why this class matters", "",
        "FILL IN. Note: the aggregate above says a rule misfires; it does not say why. ",
        "The why is the part a maintainer cannot re-derive, and it is the actual contribution.",
        "",
        "<!-- Nothing above may name a repository, path, host, company or finding text. ",
        "     If the lesson cannot be written without them, it is an incident report. -->",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="aggregate local run records into learning signals")
    ap.add_argument("--dir", type=Path, default=Path(".vigil/runs"))
    ap.add_argument("--corpus", type=Path,
                    help="aggregate contributed bundles across contributors")
    ap.add_argument("--draft-lesson", action="store_true",
                    help="emit a lesson stub for the strongest signal")
    args = ap.parse_args()

    if args.corpus:
        if not args.corpus.is_dir():
            print(f"no corpus at {args.corpus}", file=sys.stderr)
            return 2
        by_contributor = load_corpus(args.corpus)
        if not by_contributor:
            print("no usable bundles", file=sys.stderr)
            return 2
        print("\n".join(corpus_report(by_contributor)))
        signals = corpus_candidates(by_contributor)
        if args.draft_lesson:
            if not signals:
                print("no signal clears the contributor floor — nothing to draft",
                      file=sys.stderr)
                return 1
            print(draft(signals))
        elif signals:
            print(f"{len(signals)} signal(s) clear the contributor floor — "
                  "re-run with --draft-lesson")
        return 0

    if not args.dir.is_dir():
        print(f"no run records at {args.dir} — run /vigil on a real codebase first",
              file=sys.stderr)
        return 2

    records = load(args.dir)
    if not records:
        print("no usable run records", file=sys.stderr)
        return 2

    print("\n".join(report(records)))

    signals = candidates(records)
    if args.draft_lesson:
        if not signals:
            print("no signal crosses the threshold — nothing to draft", file=sys.stderr)
            return 1
        print(draft(signals))
    elif signals:
        print(f"{len(signals)} signal(s) cross the threshold — "
              "re-run with --draft-lesson to start writing one up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
