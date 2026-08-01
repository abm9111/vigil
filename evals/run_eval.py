#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""VIGIL eval harness — measures recall, false positives, and severity calibration.

Without this, "VIGIL catches X" is an assertion. With it, it is a number that can regress.

Each fixture is a small repo with deliberately seeded defects and an `expected.json` that
declares what a competent audit must find. The harness runs VIGIL against the fixture and
scores three things:

  Recall        of the must-detect defects, how many were found
  False pos.    findings that match no seeded defect and no acceptable-extra allowance
  Calibration   was the seeded HIGH reported as HIGH, or inflated/deflated

The clean-control fixture has zero seeded defects. Any finding it produces is a pure false
positive. Rule 3 says false positives destroy trust faster than misses, so that fixture is
the sharpest signal in the suite — watch it before you watch recall.

Usage
  python3 evals/run_eval.py                          # all fixtures (invokes claude -p)
  python3 evals/run_eval.py --fixture clean-control
  python3 evals/run_eval.py --from-file out.txt --fixture data-export-pipeline
                                                     # score a saved transcript, no tokens

Exit: 0 all fixtures pass · 1 a threshold was missed · 2 harness error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "fixtures"
# Answer keys live OUTSIDE the audited directory. When expected.json sat inside the fixture,
# the auditor read it while enumerating the directory and said so — a run where the auditor
# can see the key measures nothing. Keep the fixture dir containing only the target code.
EXPECTED = ROOT / "expected"

# VIGIL finding lines look like: VIGIL-SEC-001  HIGH  description...
FINDING_RE = re.compile(
    r"VIGIL-(?P<cluster>[A-Z]+)-(?P<num>\d+)\s+(?P<sev>CRITICAL|HIGH|MEDIUM|LOW|INFO)?",
    re.I,
)
SEV_ORDER = ["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"]

# expected.json shapes. Values are heterogeneous JSON, so these stay loose by design.
Defect = dict[str, Any]
Spec = dict[str, Any]


def parse_findings(text: str) -> list[dict[str, str]]:
    """Extract findings from VIGIL output.

    Prefers a fenced JSON block (what --format json emits). Falls back to scraping the
    terminal format, because a harness that only works on the happy path measures nothing.
    """
    # Take the parse yielding the MOST findings. A non-greedy regex over nested JSON
    # matches an inner object and silently truncates the list — that produced a 50%
    # recall reading on a run that had actually reported the findings.
    best: list[dict[str, str]] = []
    for segment in text.split("```"):
        blob = segment.strip()
        blob = blob[4:].lstrip() if blob.lower().startswith("json") else blob
        if not blob or blob[0] not in "[{":
            continue
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        # A report carries BOTH `correlated_findings` and `findings`. Rule 7 says a
        # correlated finding REPLACES its constituents, so reading only `findings`
        # loses every defect that got correlated — which is the most important ones.
        items: list[object] = []
        if isinstance(data, dict):
            for key in ("correlated_findings", "findings"):
                v = data.get(key)
                if isinstance(v, list):
                    items.extend(v)
        elif isinstance(data, list):
            items = list(data)

        # Only accept blocks whose items actually look like findings. "Largest block wins"
        # alone lets an unrelated array — a preflight tool list, a scores table — outvote
        # the real report and drive recall to zero.
        dicts = [
            i
            for i in items
            if isinstance(i, dict)
            and (
                re.fullmatch(r"VIGIL-[A-Z]+-\d+", str(i.get("id", "")).strip(), re.I)
                or str(i.get("severity", "")).upper() in SEV_ORDER
            )
        ]
        if dicts:
            parsed = [
                {
                    # Index-qualified so findings with a missing or duplicate id stay
                    # distinct. Keying on a possibly-empty string let one id-less finding
                    # enter `claimed` and exempt every other id-less finding from the
                    # false-positive count — the metric clean-control depends on.
                    "id": str(i.get("id", "")).strip() or f"<unlabelled #{n}>",
                    "key": f"{n}:{str(i.get('id', '')).strip()}",
                    "severity": str(i.get("severity", "")).upper(),
                    "text": json.dumps(i, ensure_ascii=False).lower(),
                }
                for n, i in enumerate(dicts)
            ]
            if len(parsed) > len(best):
                best = parsed
    if best:
        return best

    # VIGIL findings are multi-line: the ID and severity sit on the first line, the
    # description and narrative wrap onto the following indented lines. Scoring only the
    # first line loses the evidence and reports a competent audit as a miss.
    out: list[dict[str, str]] = []
    matches = list(FINDING_RE.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[m.start():end]
        # Stop at the next section rule so a finding does not absorb the following header.
        block = re.split(r"\n\s*(?:━|─{3,}|##)", block)[0]
        fid = f"VIGIL-{m.group('cluster').upper()}-{m.group('num')}"
        out.append(
            {
                "id": fid,
                "key": f"{i}:{fid}",
                "severity": (m.group("sev") or "").upper(),
                "text": " ".join(block.split()).lower(),
            }
        )
    return out


@dataclass
class Result:
    """Typed scorecard for one fixture. A plain dict here forced every consumer to
    re-assert types that the scorer already knows."""

    recall: float = 0.0
    detected: list[str] = field(default_factory=list)
    missed: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    max_false_positives: int = 0
    calibration: list[str] = field(default_factory=list)
    severe_deflation: list[str] = field(default_factory=list)
    passed: bool = False


# A finding that cites nothing is an impression, not a catch. Rule 1 demands evidence before
# opinion; without this, a run of hedged "worth a note" LOWs scored 100% recall.
#
# The bare alternations `:\d+` and `line \d+` were removed: they matched "a ratio of 1:2" and
# "section 2.3:1", so "evidence" degraded to "contains a colon followed by a digit". Only a
# real `path.ext:line` or an explicit line/lines field counts now.
EVIDENCE_RE = re.compile(
    r"[\w./-]+\.[a-z]{1,5}:\d+"          # build_export.py:77
    r'|"lines?"\s*:\s*\d+'                # structured {"line": 77}
    r"|\bline\s+\d+\s+of\b"               # "line 77 of build_export.py"
)


# Line numbers taken ONLY from a real citation: `path.ext:77`, `"line": 77`, `lines 77-80`.
CITED_LINE_RE = re.compile(
    r"[\w./-]+\.[a-z]{1,5}:(\d+)"      # build_export.py:77
    r'|"lines?"\s*:\s*(\d+)'            # {"line": 77}
    r"|\blines?\s+(\d+)"                # "line 77", "lines 77-80"
)


def _cited_lines(text: str) -> list[int]:
    return [int(g) for m in CITED_LINE_RE.finditer(text) for g in m.groups() if g]


def has_evidence(text: str) -> bool:
    """True if the finding cites a concrete location, not just a topic.

    Deliberately does NOT accept the words "demonstrated"/"reproduced" on their own — an
    auditor can type either without having done it, and this harness cannot tell.
    """
    return bool(EVIDENCE_RE.search(text))


# Rule 7 makes a correlated finding REPLACE its constituents, so a report that obeys the rule
# ships one VIGIL-CORR-* where the manifest seeded several defects. Capping every finding at
# one claim then marked the rest MISSED: folding two seeded defects into one honest CORR
# scored 83%, three scored 67% and failed outright, while a flat report listing them
# separately scored 100%. That penalised the auditor for using the flagship feature.
CORR_ID_RE = re.compile(r"vigil-corr-\d+", re.I)
VIGIL_ID_RE = re.compile(r"vigil-[a-z]+-\d+", re.I)
CONSTITUENTS_RE = re.compile(
    r'"?(?:contributing(?:_factors)?|constituent(?:s|_findings)?)"?\s*:\s*(.{0,400})',
    re.I | re.S,
)


def claim_capacity(finding: dict[str, str]) -> int:
    """How many seeded defects one finding may satisfy.

    One — except a correlated finding, which stands in for the constituents it names, and so
    may satisfy one defect per constituent. Deliberately gated on BOTH the VIGIL-CORR-* id and
    a declared constituent list: a flat finding that must not claim two defects still cannot,
    and a bare CORR with a keyword-rich narrative but no declared constituents cannot sweep the
    manifest. This is only a ceiling — each claim still has to clear signals, evidence and the
    line anchor on its own.
    """
    if not CORR_ID_RE.fullmatch(finding["id"].strip()):
        return 1
    m = CONSTITUENTS_RE.search(finding["text"])
    if not m:
        return 1
    window = m.group(1)
    # A JSON list ends at its bracket; the terminal format has no bracket, so fall back to the
    # bounded window rather than reading into the next section.
    if window.startswith("["):
        window = window.partition("]")[0]
    named = {i.lower() for i in VIGIL_ID_RE.findall(window)}
    named.discard(finding["id"].strip().lower())
    return max(1, len(named))


def score(expected: Spec, findings: list[dict[str, str]]) -> Result:
    must: list[Defect] = expected.get("must_detect", [])
    # Word-boundary, not substring: "merge" as a bare substring also exempted "merged",
    # "submerge" and any finding whose JSON happened to contain the letters. Short tokens
    # were quietly exempting large classes of real findings from the FP count.
    allowed = [
        re.compile(rf"(?<![a-z0-9]){re.escape(a.lower())}(?![a-z0-9])", re.I)
        for a in expected.get("acceptable_extra", [])
    ]

    tolerance = int(expected.get("line_tolerance", 6))

    detected: list[str] = []
    missed: list[str] = []
    calibration: list[str] = []
    severe_deflation: list[str] = []
    claimed: set[str] = set()

    # Assign best-first, not first-come. Iterating defects in declaration order and taking
    # the first finding that clears the bar let an early defect claim a finding that was a
    # far stronger match for a later one — producing a recall number that looked right for
    # the wrong reasons. Score every (defect, finding) pair, then assign highest-confidence
    # matches first so each defect gets the finding that actually describes it.
    pairs: list[tuple[int, int, str]] = []
    for d_i, defect in enumerate(must):
        sigs = [s.lower() for s in defect.get("signals", [])]
        fn = str(defect.get("file", "")).lower()
        want_lines = [int(x) for x in defect.get("lines", [])]
        for f in findings:
            if not has_evidence(f["text"]):
                continue
            hits = sum(s in f["text"] for s in sigs)
            if not (hits >= 2 or (hits >= 1 and fn and fn in f["text"])):
                continue
            # The cited line must land near the real defect. Signal keywords can be
            # sprinkled straight out of the manifest's own vocabulary; correct line numbers
            # cannot be guessed without reading the code. This is what separates measuring
            # comprehension from measuring token co-occurrence — a synthetic "finding" of
            # bare keywords plus a plausible-looking path now fails unless it also lands
            # on the right lines.
            if want_lines:
                # Extract ONLY cited locations, never every number in the text. Scanning all
                # 1-4 digit tokens meant one incidental number ("affects 31 rows") satisfied
                # the anchor while the finding cited entirely wrong lines — a probe with
                # wrong citations plus decoy numbers scored 100%. The anchor has to read the
                # citation, not the prose around it.
                cited = _cited_lines(f["text"])
                if not any(abs(c - w) <= tolerance for c in cited for w in want_lines):
                    continue
            # File agreement breaks ties between equally keyword-matched findings.
            pairs.append((hits * 2 + (1 if fn and fn in f["text"] else 0), d_i, f["key"]))
    pairs.sort(reverse=True)

    assignment: dict[int, str] = {}
    # Budget, not a one-shot flag: a correlated finding may satisfy one defect per constituent
    # it declares (see claim_capacity). `claimed` still records "this finding matched
    # something" for the false-positive count, which is a yes/no question.
    budget = {f["key"]: claim_capacity(f) for f in findings}
    for _score, d_i, cand_key in pairs:
        if d_i not in assignment and budget[cand_key] > 0:
            assignment[d_i] = cand_key
            budget[cand_key] -= 1
            claimed.add(cand_key)
    by_key = {f["key"]: f for f in findings}

    for d_i, defect in enumerate(must):
        f_key: str | None = assignment.get(d_i)
        if f_key is not None:
            hit = by_key[f_key]
            detected.append(defect["id"])
            want, got = str(defect.get("severity", "")).upper(), hit["severity"]
            if want and not got:
                severe_deflation.append(
                    f"{defect['id']}: finding reported no severity — cannot be calibrated"
                )
            elif want and got and want != got:
                if want in SEV_ORDER and got in SEV_ORDER:
                    delta = SEV_ORDER.index(got) - SEV_ORDER.index(want)
                    calibration.append(
                        f"{defect['id']} ({hit['id']}): expected {want}, reported {got} "
                        f"({'inflated' if delta > 0 else 'deflated'} {abs(delta)})"
                    )
                    # A defect reported two or more levels below expectation is not a catch
                    # in any useful sense — it is the defect noticed and then waved through.
                    # Ungated calibration let a run of hedged LOWs score 100% recall.
                    # Any deflation of a HIGH/CRITICAL matters: HIGH->MEDIUM moves the
                    # severity floor from 79 (not production-ready) to 89 (B, ready). An
                    # eval that passes what the product would ship on is not a gate.
                    # Below HIGH, only a >=2-level drop counts as waving it through.
                    if delta < 0 and (want in ("HIGH", "CRITICAL") or delta <= -2):
                        severe_deflation.append(
                            f"{defect['id']}: {want} reported as {got} "
                            f"({abs(delta)} level{'s' if abs(delta) > 1 else ''} low)"
                        )
                else:
                    # An unscoreable severity is not a free pass: omitting severity, or
                    # using a token outside the five, previously credited full recall with
                    # an empty calibration list and passed.
                    calibration.append(
                        f"{defect['id']} ({hit['id']}): unrecognised severity {got!r} "
                        f"(expected {want})"
                    )
                    severe_deflation.append(
                        f"{defect['id']}: severity {got or '<missing>'!r} is not one of "
                        f"{'/'.join(SEV_ORDER)} — cannot be calibrated"
                    )
        else:
            missed.append(defect["id"])

    false_pos = [
        f["id"]
        for f in findings
        if f["key"] not in claimed and not any(a.search(f["text"]) for a in allowed)
    ]

    recall = len(detected) / len(must) if must else 1.0
    cap = int(expected.get("max_false_positives", 0))
    return Result(
        recall=recall,
        detected=detected,
        missed=missed,
        false_positives=false_pos,
        max_false_positives=cap,
        calibration=calibration,
        severe_deflation=severe_deflation,
        passed=(
            recall >= float(expected.get("min_recall", 1.0))
            and len(false_pos) <= cap
            and not severe_deflation
        ),
    )


def run_vigil(fixture: Path, model: str | None) -> str:
    cmd = ["claude", "-p", "/vigil audit --format json .",
           "--allowedTools", "Bash,Read,Glob,Grep"]
    if model:
        cmd += ["--model", model]
    if not fixture.is_dir():
        print(f"harness error: no fixture directory at {fixture}", file=sys.stderr)
        sys.exit(2)
    try:
        r = subprocess.run(
            cmd, cwd=fixture, capture_output=True, text=True, timeout=900, check=False
        )
    except FileNotFoundError:
        print(
            "harness error: `claude` CLI not on PATH.\n"
            "  Score a saved transcript instead:\n"
            "    claude -p '/vigil audit --format json .' > out.txt\n"
            "    python3 evals/run_eval.py --from-file out.txt --fixture <name>",
            file=sys.stderr,
        )
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print(f"harness error: timed out on {fixture.name}", file=sys.stderr)
        sys.exit(2)
    if r.returncode != 0:
        # A CLI that died mid-run would otherwise be scored as a 0-recall audit, which reads
        # as a VIGIL regression rather than a harness failure.
        print(f"harness error: `claude` exited {r.returncode} on {fixture.name}\n"
              f"{r.stderr[-600:]}", file=sys.stderr)
        sys.exit(2)
    return r.stdout + r.stderr


BASELINE_PROMPT_FILE = ROOT / "baseline-prompt.md"


def control_prompt() -> str:
    """The without-VIGIL prompt, read from its own file so it can be reviewed and argued with.

    Kept out of this module deliberately: a benchmark's result is decided by its control, and a
    control buried in code is one nobody audits. See baseline-prompt.md for why it is
    deliberately strong.
    """
    text = BASELINE_PROMPT_FILE.read_text(encoding="utf-8")
    m = re.search(r"## The prompt\s*\n+```\n(.*?)\n```", text, re.S)
    if not m:
        print(f"harness error: no fenced prompt under '## The prompt' in "
              f"{BASELINE_PROMPT_FILE.name}", file=sys.stderr)
        sys.exit(2)
    return m.group(1).strip()


def _vigil_installed() -> Path | None:
    """Where VIGIL is installed, or None. Follows symlinks, which rglob does not.

    `Path.rglob` will not descend into a symlinked directory, and a skill under development is
    almost always a symlink into a working copy — this one is. So the filesystem guard was
    blind in the single most common install shape, and only the model probe was doing any
    work. Scan entries directly instead.
    """
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "skills"
    if not root.is_dir():
        return None
    for entry in list(root.iterdir()) + [d for e in root.iterdir() if e.is_dir()
                                         for d in e.iterdir() if d.is_dir()]:
        skill = entry / "SKILL.md"
        if not skill.is_file():
            continue
        head = skill.read_text(encoding="utf-8", errors="replace")[:400]
        if re.search(r"^name:\s*[\"']?vigil[\"']?\s*$", head, re.M):
            return entry
    return None


def assert_skill_invisible(model: str | None) -> None:
    """Prove the control cannot see VIGIL before trusting a single control number.

    Without this the harness has a silent, catastrophic failure mode: if the control inherits a
    config where the skill is discoverable, both arms are really the treatment arm, the delta
    collapses to roughly zero, and the honest-looking conclusion is "VIGIL adds nothing."

    A benchmark that can quietly measure the wrong thing and still print a plausible number is
    the shape of lessons/0002. So this is a hard gate, not a warning.
    """
    # The FREE check runs FIRST, and it is defence in depth rather than a shortcut: the model
    # probe below is weaker than it looks, because Claude Code lists a skill by its DIRECTORY
    # name. A copy stashed as `.baseline-stash` is fully discoverable and named nothing like
    # "vigil". That exact contamination happened here, and was caught only because the stash
    # name coincidentally contained "vigil".
    #
    # So: no directory anywhere under the skills tree may declare `name: vigil`, whatever it
    # is called on disk — and finding one must cost nothing, because a guard that spends a
    # paid CLI call to discover it should not have run is a guard people disable. Ordering
    # this after the probe also made the whole function unrunnable without the CLI, which is
    # how it failed in CI while passing on the maintainer's machine.
    found = _vigil_installed()
    if found is not None:
        print(f"harness error: {found} still declares `name: vigil` — the control arm would "
              "see the skill under whatever the directory is called, and the delta would be "
              "meaningless.", file=sys.stderr)
        sys.exit(2)

    cmd = ["claude", "-p", "List the names of every skill available to you. "
                           "Output names only, one per line, nothing else."]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if r.returncode != 0:
        print(f"harness error: control probe exited {r.returncode}: {r.stderr[-400:]}",
              file=sys.stderr)
        sys.exit(2)

    if "vigil" in r.stdout.lower():
        print("harness error: the control arm can still see the VIGIL skill, so both arms "
              "would be the treatment arm and the delta would be meaningless.\n"
              f"  probe returned: {r.stdout.strip()[:200]!r}", file=sys.stderr)
        sys.exit(2)


def assert_skill_visible(model: str | None) -> None:
    """The treatment arm must prove the skill IS installed before it means anything.

    Its absence produced a 0% recall that the harness reported as a real result — "VIGIL beat
    the control on 0/2 fixtures" — when the truth was that `/vigil` resolved to nothing. A
    number from an arm that could not possibly work is worse than no number, because it looks
    like a finding (`lessons/0002`).

    Symmetric with assert_skill_invisible: each arm proves its own precondition.
    """
    if _vigil_installed() is None:
        print("harness error: the treatment arm cannot find an installed VIGIL skill. Its "
              "findings would be a bare model's, and 0% recall would read as a VIGIL failure "
              "rather than a missing install.", file=sys.stderr)
        sys.exit(2)

    cmd = ["claude", "-p", "List the names of every skill available to you. "
                           "Output names only, one per line, nothing else."]
    if model:
        cmd += ["--model", model]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False)
    if r.returncode != 0 or "vigil" not in r.stdout.lower():
        print("harness error: VIGIL is on disk but the model does not list it — the treatment "
              f"arm would measure a bare model.\n  probe: {r.stdout.strip()[:200]!r}",
              file=sys.stderr)
        sys.exit(2)


def _dump(results: dict[str, list[Result]], path: Path) -> None:
    path.write_text(json.dumps(
        {k: [{"recall": r.recall, "false_positives": r.false_positives,
              "missed": r.missed, "detected": r.detected} for r in v]
         for k, v in results.items()}, indent=2), encoding="utf-8")
    print(f"wrote {path}")


def run_control(fixture: Path, model: str | None) -> str:
    """Run the fixture with VIGIL not installed — the without-VIGIL arm.

    Isolation is PHYSICAL (the skill is not on disk during this arm), not environmental.
    The first version pointed CLAUDE_CONFIG_DIR at a fresh directory, which also severs
    credentials — the CLI reports "Not logged in" and the arm cannot run at all. And
    `--disable-slash-commands` is not isolation either: it blocks invocation while the skill
    stays in context, so the control would silently have been a second treatment arm.

    Caller is responsible for making the skill absent; assert_skill_invisible() verifies it.
    """
    cmd = ["claude", "-p", control_prompt(), "--allowedTools", "Bash,Read,Glob,Grep"]
    if model:
        cmd += ["--model", model]
    try:
        r = subprocess.run(
            cmd, cwd=fixture, capture_output=True, text=True, timeout=900, check=False,
        )
    except subprocess.TimeoutExpired:
        print(f"harness error: control timed out on {fixture.name}", file=sys.stderr)
        sys.exit(2)
    if r.returncode != 0:
        print(f"harness error: control exited {r.returncode} on {fixture.name}\n"
              f"{r.stderr[-600:]}", file=sys.stderr)
        sys.exit(2)
    return r.stdout + r.stderr


def median(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def report_delta(name: str, control: list[Result], vigil: list[Result]) -> bool:
    """Print the comparison. Returns True if VIGIL beat the control on this fixture.

    Reports a range as well as a median because a single run is a sample of size one, and
    min_recall has always been enforced against a number whose spread nobody measured.
    """
    def line(label: str, results: list[Result]) -> str:
        rec = [r.recall for r in results]
        fps = [float(len(r.false_positives)) for r in results]
        span = (f"  (min {min(rec):.0%} max {max(rec):.0%})" if len(rec) > 1 else "")
        return (f"   {label:<10} recall {median(rec):>4.0%}{span}"
                f"   false positives {median(fps):>3.0f}")

    c_rec, v_rec = median([r.recall for r in control]), median([r.recall for r in vigil])
    c_fp = median([float(len(r.false_positives)) for r in control])
    v_fp = median([float(len(r.false_positives)) for r in vigil])

    print(f"\n── {name}   ({len(control)} run(s) per arm)")
    print(line("control", control))
    print(line("vigil", vigil))
    print(f"   {'delta':<10} recall {v_rec - c_rec:+.0%}"
          f"                       false positives {v_fp - c_fp:+.0f}")

    # Recall alone is not an improvement. A skill that finds more by inventing more has moved
    # nothing, so a strictly worse false-positive count cancels a recall gain.
    better = v_rec > c_rec and v_fp <= c_fp
    if better:
        print("   → VIGIL found more without inventing more")
    elif v_rec > c_rec:
        print(f"   → recall improved but false positives rose ({c_fp:.0f} → {v_fp:.0f}); "
              "that is not an improvement")
    elif v_rec == c_rec and v_fp < c_fp:
        print("   → same recall, fewer false positives")
    else:
        print("   → NO IMPROVEMENT over a competent prompt on this fixture. "
              "Record it; do not weaken the control.")
    return better


def report(name: str, res: Result) -> None:
    mark = "PASS" if res.passed else "FAIL"
    print(f"\n── {name}  [{mark}]")
    print(f"   recall          {res.recall:.0%}  ({len(res.detected)} detected)")
    if res.missed:
        print(f"   MISSED          {', '.join(res.missed)}")
    fp = res.false_positives
    print(f"   false positives {len(fp)} / {res.max_false_positives} allowed"
          + (f"  {', '.join(fp[:5])}" if fp else ""))
    for c in res.calibration:
        print(f"   calibration     {c}")
    for d in res.severe_deflation:
        print(f"   DEFLATED        {d}")


def run_arm(names: list[str], arm: str, model: str | None, runs: int, out: Path) -> int:
    """Run ONE arm and write its scores. The harness mutates nothing.

    The previous design ran both arms inside one process, so isolating the control meant
    isolating the treatment arm too — the wrapper moved the skill aside and both arms ran
    without it. Splitting the arms makes each one's precondition explicit and checkable.
    """
    if arm == "control":
        assert_skill_invisible(model)
        print("control arm: skill confirmed ABSENT\n")
    else:
        assert_skill_visible(model)
        print("treatment arm: skill confirmed PRESENT\n")

    results: dict[str, list[Result]] = {}
    for name in names:
        fx = FIXTURES / name
        expected = json.loads((EXPECTED / f"{name}.json").read_text(encoding="utf-8"))
        raw = [run_control(fx, model) if arm == "control" else run_vigil(fx, model)
               for _ in range(runs)]
        # Save the transcripts beside the scores. A 0% recall is ambiguous between "the tool
        # missed everything" and "the scorer did not match what it found", and without the raw
        # output the only way to tell them apart is to pay for the run again. That happened:
        # an arm scored 0% while emitting three findings, and the question of which had failed
        # could not be answered from the artefacts.
        tdir = out.parent / f"{arm}-transcripts"
        tdir.mkdir(parents=True, exist_ok=True)
        for i, r in enumerate(raw):
            (tdir / f"{name}.{i}.txt").write_text(r, encoding="utf-8")
        results[name] = [score(expected, parse_findings(r)) for r in raw]
        rec = median([r.recall for r in results[name]])
        fps = median([float(len(r.false_positives)) for r in results[name]])
        print(f"  {name:<24} recall {rec:>4.0%}   false positives {fps:>3.0f}")
    _dump(results, out)
    return 0


def implausible(name: str, expected: dict[str, Any], results: list[Result]) -> str | None:
    """Flag numbers that look like a broken arm rather than a real score.

    This is the check that was missing when the harness printed "VIGIL beat the control on
    0/2 fixtures". The treatment arm had scored 0% recall on a fixture seeding six defects —
    not because VIGIL failed, but because a wrapper bug meant the skill was not installed
    while that arm ran. The number was real; what it measured was nothing.

    A warning, deliberately, not a refusal. Discarding a low score automatically would be the
    thumb on the scale this project refuses everywhere else — a genuine null result is the
    most valuable output this harness can produce. But an unremarked 0% is how a harness bug
    gets published as a finding about the tool.
    """
    seeded = len(expected.get("must_detect", []))
    if not seeded or not results:
        return None
    if all(r.recall == 0.0 for r in results):
        return (f"recall 0% across every run on a fixture seeding {seeded} defect(s). That is "
                "almost always an arm that could not run — a missing install, a parse failure, "
                "a CLI error. Confirm the arm log said 'skill confirmed PRESENT/ABSENT' and "
                "that findings parsed, before reading this as a result about VIGIL.")
    return None


def compare_arms(control_path: Path, vigil_path: Path) -> int:
    """Pure comparison of two saved arms. No CLI calls, so it is free to re-run."""
    c = json.loads(control_path.read_text(encoding="utf-8"))
    v = json.loads(vigil_path.read_text(encoding="utf-8"))
    shared = sorted(set(c) & set(v))
    if not shared:
        print("no fixtures in common between the two arms", file=sys.stderr)
        return 2

    def to_results(rows: list[dict[str, Any]]) -> list[Result]:
        return [Result(recall=r["recall"], false_positives=r["false_positives"]) for r in rows]

    improved, suspect = [], []
    for n in shared:
        v_res = to_results(v[n])
        if report_delta(n, to_results(c[n]), v_res):
            improved.append(n)
        spec_path = EXPECTED / f"{n}.json"
        spec = (json.loads(spec_path.read_text(encoding="utf-8"))
                if spec_path.exists() else {})
        warn = implausible(n, spec, v_res)
        if warn:
            print(f"   ⚠️  {warn}")
            suspect.append(n)

    counted = [n for n in shared if n not in suspect]
    print(f"\nVIGIL beat the control on {len(improved)}/{len(counted)} measurable fixture(s).")
    if suspect:
        print(f"{len(suspect)} fixture(s) EXCLUDED as unmeasured: {suspect}. A harness that "
              "reports a broken arm as a capability finding is the defect this exists to "
              "prevent — it has already happened once.")
    if len(improved) < len(shared):
        print("Fixtures with no improvement are a result about VIGIL, not a harness failure —"
              "\nPROVIDED both arms verified their preconditions. Check the arm logs said "
              "\n'skill confirmed ABSENT' and 'skill confirmed PRESENT' before believing this.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", help="run a single fixture by directory name")
    ap.add_argument("--from-file", help="score a saved transcript instead of invoking claude")
    ap.add_argument("--model", help="model override passed to claude -p")
    ap.add_argument("--arm", choices=("control", "vigil"),
                    help="run ONE arm and save its scores (see evals/baseline-prompt.md)")
    ap.add_argument("--out", type=Path, help="where --arm writes its scores")
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("CONTROL", "VIGIL"),
                    help="compare two saved arms — free, no CLI calls")
    ap.add_argument("--runs", type=int, default=1, metavar="N",
                    help="runs per arm; >1 reports a range as well as a median")
    args = ap.parse_args()

    if args.runs < 1:
        print("harness error: --runs must be at least 1", file=sys.stderr)
        return 2
    if args.compare:
        return compare_arms(*args.compare)
    if args.arm and not args.out:
        print("harness error: --arm needs --out", file=sys.stderr)
        return 2

    if not FIXTURES.is_dir() or not EXPECTED.is_dir():
        print(f"harness error: expected {FIXTURES} and {EXPECTED}", file=sys.stderr)
        return 2

    names = [args.fixture] if args.fixture else [
        p.stem for p in sorted(EXPECTED.glob("*.json")) if (FIXTURES / p.stem).is_dir()
    ]
    if not names:
        print("harness error: no fixtures with expected.json", file=sys.stderr)
        return 2

    if args.from_file and len(names) != 1:
        print("harness error: --from-file requires exactly one --fixture", file=sys.stderr)
        return 2

    if args.arm:
        return run_arm(names, args.arm, args.model, args.runs, args.out)

    ok = True
    for name in names:
        fx = FIXTURES / name
        spec_path = EXPECTED / f"{name}.json"
        if not spec_path.exists():
            print(f"harness error: no manifest at {spec_path}", file=sys.stderr)
            return 2
        if (fx / "expected.json").exists():
            print(f"harness error: {name} has an answer key inside the audited directory — "
                  "move it to evals/expected/ or the measurement is invalid", file=sys.stderr)
            return 2
        expected = json.loads(spec_path.read_text(encoding="utf-8"))
        raw = (
            Path(args.from_file).read_text(encoding="utf-8")
            if args.from_file
            else run_vigil(fx, args.model)
        )
        res = score(expected, parse_findings(raw))
        report(name, res)
        ok &= res.passed

    print("\n" + ("ALL FIXTURES PASS" if ok else "REGRESSION — a fixture missed its threshold"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
