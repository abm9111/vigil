#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""VIGIL self-audit — the skill applied to itself.

A tool that audits other repos should not ship dead links, orphaned clusters, or an ID
prefix that maps to nothing. This is the gate that keeps that true. No LLM, no network,
runs in well under a second.

Checks:
  L1  every relative markdown link resolves
  L2  every cluster/engine/mode referenced by SKILL.md exists on disk
  L3  every ID prefix in RULES.md maps to a real cluster (or is CORR)
  L4  every cluster declares Covers / Weight / ID prefix
  L5  no orphan files; clusters/ and engines/ must be named individually,
      domains|compliance-maps|companions may be covered by a bulk reference
  L6  every cluster file has a matching row in the scoring.md weights table
      (cluster -> row only; the reverse needs an allowlist for non-cluster rows
       such as "Auth & Access", which is a scoring lens rather than a file)
  L7  modes/audit.md enumerates every cluster (the router's "ALL clusters" is not enough)
  L8  every compliance standard cited in correlation.md has a compliance-maps/ entry
  L9  the correlation-pattern count agrees everywhere it is stated
  L10 weights printed in mode templates match the scoring.md table
  L11 FLAGS.md and ci-adapter.md describe the same --ci exit-code contract
  L12 no eval manifest is looser than the floor recorded in this file
  L13 cluster header weights match the scoring.md table (scoring.md is authority)
  L14 prose `file.md -> Section` references resolve (L1 only sees [](links))
  L15 any restatement of the CVE reachability ladder carries its Rule 7 fence
  L16 the cluster_score formula keeps its evidence-ceiling term
  L17 the lessons ledger is internally honest (claimed checks exist; open work tracked)
  L18 LEDGER.md matches the lessons it is generated from
  L19 contributed lessons/results/proof carry no real paths, hosts, keys or emails
  L20 every version string agrees with pyproject.toml
  L21 no unfilled publish placeholders (OWNER/REPO, <this-repo>)
  L22 SKILL.md is discoverable by Claude Code (frontmatter, name, description)
  L23 assertion evals are well-formed (ids unique, fields present, >=2 assertions)
  L24 every prose restatement of the check count matches the real one
  L25 the run-record schema stays closed — no free-text field can be added to it
  L26 proof entries are well-formed and use the controlled vocabulary
  L27 every contributed corpus bundle still passes the privacy gate
  L28 the end-of-run consent contract is intact (default no, silence is not consent,
      a decline is honoured, the record can be shown in full, there is an off switch)
  L29 the record schema's cluster vocabulary matches RULES.md

Exit: 0 clean · 1 findings · 2 harness error.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCANNED = ("clusters", "engines", "modes", "domains", "compliance-maps", "companions")

# [text](target) — relative targets only; skip http(s), mailto, anchors
LINK = re.compile(r"\[[^\]]*\]\((?!https?://|mailto:|#)([^)\s]+)\)")
FENCE = re.compile(r"```.*?```", re.S)
INLINE_CODE = re.compile(r"`[^`\n]+`")


def prose(text: str) -> str:
    """Strip fenced blocks AND inline code spans before looking for links.

    Both contain things shaped like markdown that are not markdown: shell globs and regexes
    in fenced blocks (`[@a-z0-9._-]+`), and literal examples in inline spans — a table row
    documenting "dead `[text](link)`" is describing a link, not making one. Each produced a
    false positive on this repo's own files.
    """
    return INLINE_CODE.sub("", FENCE.sub("", text))


class Report:
    def __init__(self) -> None:
        self.findings: list[tuple[str, str]] = []

    def fail(self, check: str, msg: str) -> None:
        self.findings.append((check, msg))

    def emit(self) -> int:
        if not self.findings:
            print("VIGIL self-audit: CLEAN — no dead links, orphans, or prefix gaps.")
            return 0
        print(f"VIGIL self-audit: {len(self.findings)} finding(s)\n")
        for check, msg in self.findings:
            print(f"  [{check}] {msg}")
        return 1


def md_files() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)


def check_links(r: Report) -> None:
    for f in md_files():
        for target in LINK.findall(prose(f.read_text(encoding="utf-8"))):
            resolved = (f.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                r.fail("L1", f"{f.relative_to(ROOT)} -> dead link {target!r}")


def check_skill_refs(r: Report) -> None:
    skill = ROOT / "SKILL.md"
    if not skill.exists():
        r.fail("L2", "SKILL.md missing")
        return
    text = prose(skill.read_text(encoding="utf-8"))
    for target in LINK.findall(text):
        if not (skill.parent / target.split("#", 1)[0]).resolve().exists():
            r.fail("L2", f"SKILL.md references missing file {target!r}")


def cluster_prefixes() -> dict[str, Path]:
    """Map declared ID prefix -> cluster file."""
    out: dict[str, Path] = {}
    for f in sorted((ROOT / "clusters").glob("*.md")):
        m = re.search(r"\*\*ID prefix:\*\*\s*VIGIL-([A-Z-]+)", f.read_text(encoding="utf-8"))
        if m:
            out[m.group(1)] = f
    return out


def check_cluster_headers(r: Report) -> None:
    for f in sorted((ROOT / "clusters").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        for field in ("**Covers:**", "**Weight:**", "**ID prefix:**"):
            if field not in text:
                r.fail("L4", f"{f.relative_to(ROOT)} missing {field} header")


def check_prefixes(r: Report) -> None:
    rules = (ROOT / "RULES.md").read_text(encoding="utf-8")
    declared = set(cluster_prefixes())
    # RULES.md lists prefixes as: - `SEC` — Security
    listed = set(re.findall(r"^- `([A-Z-]+)`\s+—", rules, re.M))
    for p in listed - declared - {"CORR"}:
        r.fail("L3", f"RULES.md lists prefix {p!r} with no cluster declaring it")
    for p in declared - listed:
        r.fail("L3", f"cluster declares prefix {p!r} but RULES.md does not list it")


def check_orphans(r: Report) -> None:
    """L5 — every file must be reachable.

    A wholesale reference ("ALL [domains/](domains/)") genuinely covers its directory, but
    honouring that blanket for *every* directory disabled the check for 5 of 6 — including
    clusters/ and engines/, the two where an orphan actually matters. The blanket now
    applies only where per-file listing is not the design; clusters and engines must be
    named individually somewhere.
    """
    corpus = "\n".join(f.read_text(encoding="utf-8") for f in md_files())
    bulk_ok = {"domains", "compliance-maps", "companions"}
    for d in SCANNED:
        if d in bulk_ok and (f"{d}/](" in corpus or f"ALL [{d}/" in corpus):
            continue
        for f in sorted((ROOT / d).glob("*.md")):
            rel = f"{d}/{f.name}"
            # Count only references from OTHER files — a file naming itself is not reachability.
            others = "\n".join(
                q.read_text(encoding="utf-8") for q in md_files() if q != f
            )
            if rel not in others and f.name not in others:
                r.fail("L5", f"orphan: {rel} is referenced by no other file")


def check_weight_table(r: Report) -> None:
    scoring = (ROOT / "engines" / "scoring.md").read_text(encoding="utf-8")
    section = scoring.split("### Cluster Weights", 1)
    if len(section) < 2:
        r.fail("L6", "scoring.md has no '### Cluster Weights' section")
        return
    rows = re.findall(r"^\|\s*([A-Za-z &/]+?)\s*\|\s*(\d+)%", section[1], re.M)
    if not rows:
        r.fail("L6", "scoring.md weights table parsed to zero rows")
        return
    CLUSTER_TO_ROW = {
        "security": "security",
        "code-health": "architecture & code health",
        "data-and-persistence": "data & persistence",
        "api-and-networking": "api & networking",
        "infrastructure-and-devops": "infrastructure & devops",
        "frontend-and-mobile": "frontend & mobile",
        "performance": "performance",
        "compliance-and-docs": "compliance & docs",
        "ai-and-ml": "ai & ml",
        "blockchain": "blockchain",
        "data-egress-and-provenance": "data egress & provenance",
    }
    names = {n.strip().lower() for n, _ in rows}
    for f in sorted((ROOT / "clusters").glob("*.md")):
        row = CLUSTER_TO_ROW.get(f.stem)
        if row is None:
            r.fail("L6", f"cluster {f.name} is not in check_repo.py's CLUSTER_TO_ROW map — "
                          "add it so its weight row is actually verified")
        elif row not in names:
            r.fail("L6", f"cluster {f.name} has no '{row}' row in scoring.md weights table")


def check_mode_cluster_coverage(r: Report) -> None:
    """L7 — audit mode must enumerate every cluster.

    The router says "ALL clusters", but modes/audit.md lists them in execution order and
    that list is what actually runs. Two clusters (blockchain, data-egress-and-provenance)
    were absent from it while the repo reported CLEAN, which is the gap that motivated
    this check.
    """
    audit = ROOT / "modes" / "audit.md"
    if not audit.exists():
        r.fail("L7", "modes/audit.md missing")
        return
    text = audit.read_text(encoding="utf-8")
    for f in sorted((ROOT / "clusters").glob("*.md")):
        if f.name not in text:
            r.fail("L7", f"modes/audit.md does not enumerate clusters/{f.name} — "
                          "it will not run in audit mode")


def check_compliance_citations(r: Report) -> None:
    """L8 — every standard cited in a correlation pattern must have a map.

    A citation pointing at nothing is an authoritative-looking claim with no backing —
    the exact shape of the TRUST_LAUNDERING pattern this repo defines.
    """
    corr = (ROOT / "engines" / "correlation.md")
    if not corr.exists():
        r.fail("L8", "engines/correlation.md missing")
        return
    maps = "\n".join(
        p.read_text(encoding="utf-8") for p in (ROOT / "compliance-maps").glob("*.md")
    ).lower()
    cited: set[str] = set()
    for line in corr.read_text(encoding="utf-8").splitlines():
        if line.startswith("**Compliance:**"):
            for token in re.findall(r"\b(SOC2:[A-Z0-9.]+|ISO27001:[A-Z0-9.]+|OWASP:[A-Z0-9]+"
                                    r"|NIST [A-Z]+ [A-Z]{2}\.\d+|EU AI Act Art\.\d+)", line):
                cited.add(token)
    # Maps write controls as "Art. 50" / "PS.2" / "A.5.34"; citations compress them to
    # "Art.50". Compare with whitespace removed so formatting differences are not findings.
    flat = re.sub(r"\s+", "", maps)
    for token in sorted(cited):
        # The distinctive part is the trailing control id, not the framework prefix.
        m = re.search(r"([A-Za-z]{1,4}\.?\s*[\d.]+)$", token)
        needle = re.sub(r"\s+", "", (m.group(1) if m else token).lower())
        if needle not in flat:
            r.fail("L8", f"correlation.md cites {token!r} (control {needle!r}) — "
                          "no compliance-maps/ entry covers it")


# modes/*.md print abbreviated cluster names with weights; scoring.md holds the authority.
# Explicit map, not substring matching. Testing whether one name was a substring of the other
# "matched" blockchain.md against the row "AI & ML" (because "ai" occurs inside bloc-k-ch-AI-n),
# so the missing Blockchain row went unreported. A check that passes over a real gap is
# INTEGRITY_THEATER by this repo's own definition — see engines/correlation.md pattern 10.
CLUSTER_TO_ROW = {
    "security": "security",
    "code-health": "architecture & code health",
    "data-and-persistence": "data & persistence",
    "api-and-networking": "api & networking",
    "infrastructure-and-devops": "infrastructure & devops",
    "frontend-and-mobile": "frontend & mobile",
    "performance": "performance",
    "compliance-and-docs": "compliance & docs",
    "ai-and-ml": "ai & ml",
    "blockchain": "blockchain",
    "data-egress-and-provenance": "data egress & provenance",
}

ABBREV_TO_ROW = {
    "SEC": "security",
    "CODE": "architecture & code health",
    "API": "api & networking",
    "DATA": "data & persistence",
    "INFRA": "infrastructure & devops",
    "FE": "frontend & mobile",
    "PERF": "performance",
    "COMP": "compliance & docs",
    "AIML": "ai & ml",
    "EGRESS": "data egress & provenance",
    "CHAIN": "blockchain",
}

# Floors live HERE, in code, not in the manifests this file validates. A two-file edit is
# visible in review; a one-line JSON edit is not. `evals/README.md` says never lower a
# threshold to make a run pass — this is what makes that rule more than an honour system.
THRESHOLD_FLOORS = {
    "data-export-pipeline": {"min_recall": 0.8, "max_false_positives": 3},
    "clean-control": {"min_recall": 1.0, "max_false_positives": 1},
}


def weight_rows() -> dict[str, int]:
    scoring = (ROOT / "engines" / "scoring.md").read_text(encoding="utf-8")
    section = scoring.split("### Cluster Weights", 1)
    if len(section) < 2:
        return {}
    return {
        n.strip().lower(): int(pct)
        for n, pct in re.findall(r"^\|\s*([A-Za-z &/]+?)\s*\|\s*(\d+)%", section[1], re.M)
    }


def check_pattern_count(r: Report) -> None:
    """L9 — the correlation-pattern count must agree everywhere it is stated.

    `modes/audit.md` said "Run 7 correlation pattern matchers" while `correlation.md`
    defined 10, so audit mode was instructed to skip the three newest patterns. Prose
    numbers drift silently; nothing else in this file would have caught it.
    """
    corr = (ROOT / "engines" / "correlation.md").read_text(encoding="utf-8")
    actual = len(re.findall(r"^### \d+\.\s+[A-Z_]+", corr, re.M))
    if not actual:
        r.fail("L9", "correlation.md defines no '### N. PATTERN_NAME' sections")
        return
    for f in md_files():
        # evals/ is documentation *about* the repo — its results and README quote historical
        # values on purpose ("a mode file said 7 against 10 defined"). Only instructional
        # files, the ones an auditor actually follows, have to agree with the current count.
        if "evals" in f.relative_to(ROOT).parts:
            continue
        for m in re.finditer(r"(\d+)\s+(?:cross-domain\s+)?correlation pattern",
                             f.read_text(encoding="utf-8"), re.I):
            if int(m.group(1)) != actual:
                r.fail("L9", f"{f.relative_to(ROOT)} says {m.group(1)} correlation patterns; "
                             f"correlation.md defines {actual}")


def check_template_weights(r: Report) -> None:
    """L10 — weights printed in mode templates must match the scoring table."""
    rows = weight_rows()
    if not rows:
        r.fail("L10", "could not parse the scoring.md weights table")
        return
    for f in sorted((ROOT / "modes").glob("*.md")):
        # Match both `(weight: N%)` and the bare `( N%)` used by score.md's bar chart.
        # The weight-only regex reported CLEAN over a live 8%-vs-10% drift.
        for abbrev, pct in re.findall(r"^([A-Z]{2,6})\s+.*?\((?:weight:)?\s*(\d+)%\)",
                                      f.read_text(encoding="utf-8"), re.M):
            row = ABBREV_TO_ROW.get(abbrev)
            if row is None:
                r.fail("L10", f"{f.relative_to(ROOT)} prints unknown cluster {abbrev!r}")
            elif row in rows and rows[row] != int(pct):
                r.fail("L10", f"{f.relative_to(ROOT)} prints {abbrev} at {pct}%; "
                              f"scoring.md says {rows[row]}%")


def check_exit_codes(r: Report) -> None:
    """L11 — FLAGS.md and ci-adapter.md must describe the same --ci contract.

    FLAGS.md is read on every invocation; ci-adapter.md is loaded by almost no mode. When
    they disagreed, the stale copy was the one actually in context.
    """
    flags = (ROOT / "FLAGS.md").read_text(encoding="utf-8")
    adapter = (ROOT / "engines" / "ci-adapter.md").read_text(encoding="utf-8")
    ci_block = flags.split("### `--ci`", 1)[-1].split("### `--strict`", 1)[0]
    if "N/E" in adapter and "N/E" not in ci_block:
        r.fail("L11", "ci-adapter.md gates exit codes on N/E but the FLAGS.md --ci block "
                      "does not mention it — FLAGS.md is the copy every run reads")
    for code in ("0", "1", "2"):
        if f"`{code}`" not in ci_block:
            r.fail("L11", f"FLAGS.md --ci block does not document exit code {code}")


def check_threshold_floors(r: Report) -> None:
    """L12 — no manifest may be looser than the floor recorded in this file."""
    for name, floor in THRESHOLD_FLOORS.items():
        p = ROOT / "evals" / "expected" / f"{name}.json"
        if not p.exists():
            r.fail("L12", f"no manifest at evals/expected/{name}.json")
            continue
        spec = json.loads(p.read_text(encoding="utf-8"))
        if float(spec.get("min_recall", 0)) < floor["min_recall"]:
            r.fail("L12", f"{name}: min_recall {spec.get('min_recall')} is below the "
                          f"floor {floor['min_recall']} — thresholds are not to be lowered "
                          "to make a run pass")
        if int(spec.get("max_false_positives", 99)) > floor["max_false_positives"]:
            r.fail("L12", f"{name}: max_false_positives {spec.get('max_false_positives')} "
                          f"exceeds the ceiling {floor['max_false_positives']}")
        if (ROOT / "evals" / "fixtures" / name / "expected.json").exists():
            r.fail("L12", f"{name}: answer key is inside the audited directory — "
                          "the measurement would be invalid")


def check_cluster_header_weights(r: Report) -> None:
    """L13 — a cluster's header weight must match the scoring.md table.

    `blockchain.md` advertised 10% while scoring.md said 8%; `code-health.md` said 8% against
    10%. L6 checks that a row *exists* and L10 checks *mode template* weights — neither read
    the cluster headers, so two auditors could compute two different overall scores from the
    same findings and both claim to be following the rules.
    """
    rows = weight_rows()
    if not rows:
        r.fail("L13", "could not parse the scoring.md weights table")
        return
    for f in sorted((ROOT / "clusters").glob("*.md")):
        row = CLUSTER_TO_ROW.get(f.stem)
        if row is None or row not in rows:
            continue  # L6 already reports this
        m = re.search(r"^\*\*Weight:\*\*\s*(\d+)%", f.read_text(encoding="utf-8"), re.M)
        if not m:
            r.fail("L13", f"{f.name} has no parseable '**Weight:** N%' header")
        elif int(m.group(1)) != rows[row]:
            r.fail("L13", f"{f.name} header says {m.group(1)}%; scoring.md says "
                          f"{rows[row]}% — scoring.md is authoritative")


def check_prose_section_refs(r: Report) -> None:
    """L14 — `file.md -> Section Name` prose references must resolve.

    L1 only validates markdown `[text](target)` links. Four references of the form
    "`engines/scoring.md` -> Context-Driven Adjustments" pointed at sections that were never
    written, in a file the router loads on EVERY invocation — so an auditor was instructed to
    apply machinery that did not exist. All four passed L1 as CLEAN.
    """
    pattern = re.compile(r"`([a-z_/-]+\.md)`\s*(?:->|\u2192)\s*[\"\u201c]?([A-Za-z0-9 &_()-]{4,60})")
    for f in md_files():
        for target, section in pattern.findall(f.read_text(encoding="utf-8")):
            dest = (f.parent / target).resolve()
            if not dest.exists():
                dest = (ROOT / target).resolve()
            if not dest.exists():
                r.fail("L14", f"{f.relative_to(ROOT)} -> {target!r} does not exist")
                continue
            head = section.strip().rstrip('"\u201d').strip()
            if head.lower() not in dest.read_text(encoding="utf-8").lower():
                r.fail("L14", f"{f.relative_to(ROOT)} points at {target} -> {head!r}, "
                              "which that file does not contain")


def check_downgrade_fences(r: Report) -> None:
    """L15 — any file that restates the CVE reachability ladder must carry its fence.

    RULES.md Rule 7 permits exactly one correlated severity below its constituents
    (DEPENDENCY_AND_REACHABILITY), fenced by an evidence requirement and a note that the
    downgrade never moves the severity floor. `modes/siege.md` restated the same ladder with
    neither — so the fix could be bypassed by running the adversarial mode. Prose that grants
    a downgrade in one file and fences it in another is the composition class three reviews
    kept finding.
    """
    ladder = re.compile(r"not\s+reachable|imported but not reachable", re.I)
    fence = re.compile(r"positive evidence|never the (?:severity )?floor|"
                       r"does not move the (?:severity )?floor", re.I)
    for f in md_files():
        if "evals" in f.relative_to(ROOT).parts:
            continue  # results files quote historical text
        text = f.read_text(encoding="utf-8")
        if ladder.search(text) and not fence.search(text):
            r.fail("L15", f"{f.relative_to(ROOT)} grants a reachability downgrade without the "
                          "Rule 7 fence (positive evidence + floor unchanged)")


def check_score_formula(r: Report) -> None:
    """L16 — the cluster_score formula must keep its ceiling term.

    The ceiling and the penalty formula sat 245 lines apart with no composition rule, so a
    ceiling-85 cluster with 12 points of penalties could be read as 85, 73 or 88. Now that it
    is defined, this stops a future edit silently reverting to the ambiguous form.
    """
    scoring = (ROOT / "engines" / "scoring.md").read_text(encoding="utf-8")
    if "cluster_score" not in scoring:
        r.fail("L16", "scoring.md defines no cluster_score formula")
        return
    if "ceiling" not in scoring.split("cluster_score", 1)[1][:400]:
        r.fail("L16", "the cluster_score formula in scoring.md no longer references the "
                      "evidence ceiling — the ceiling/penalty order is ambiguous again")


def check_lessons_ledger(r: Report) -> None:
    """L17 — the lessons ledger must stay honest.

    `lessons/` records times VIGIL or its self-audit was wrong. It is only worth keeping if it
    cannot rot: a lesson claiming to be mechanized must name a check that exists, and one
    still open must be tracked where open work is tracked. Otherwise it degrades into a
    folder of stories that no longer describe the code.
    """
    ldir = ROOT / "lessons"
    if not ldir.is_dir():
        return  # ledger is optional; an empty repo is not a failure
    open_design = ""
    od = ROOT / "docs" / "OPEN-DESIGN.md"
    if od.exists():
        open_design = od.read_text(encoding="utf-8")
    checks_src = (ROOT / "evals" / "check_repo.py").read_text(encoding="utf-8")

    for f in sorted(ldir.glob("[0-9]*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"---\n(.*?)\n---", text, re.S)
        if not m:
            r.fail("L17", f"lessons/{f.name} has no frontmatter block")
            continue
        fm = dict(
            re.findall(r"^([a-z_]+):\s*(.*)$", m.group(1), re.M)
        )
        for field in ("id", "date", "found_by", "missed_by", "class", "status"):
            if not fm.get(field, "").strip():
                r.fail("L17", f"lessons/{f.name} has an empty required field {field!r}")
        status = fm.get("status", "").strip()
        if status not in ("mechanized", "unmechanizable", "open"):
            r.fail("L17", f"lessons/{f.name} status {status!r} is not "
                          "mechanized/unmechanizable/open")
        elif status == "mechanized":
            named = re.findall(r"L\d+", fm.get("check", ""))
            if not named:
                r.fail("L17", f"lessons/{f.name} is mechanized but names no check")
            for c in named:
                if f"  {c} " not in checks_src and f'"{c}"' not in checks_src:
                    r.fail("L17", f"lessons/{f.name} claims check {c}, which does not exist")
        elif status == "open" and f.stem not in open_design:
            # An open lesson must be findable where open work is tracked.
            slug = f.stem.split("-", 1)[-1].split("-")[0]
            if slug and slug not in open_design.lower():
                r.fail("L17", f"lessons/{f.name} is open but is not referenced in "
                              "docs/OPEN-DESIGN.md — open work must be tracked in one place")


def check_ledger_dashboard(r: Report) -> None:
    """L18 — LEDGER.md must match what lessons/ actually says.

    A generated dashboard that drifts is worse than none: it makes a public claim about who
    contributed and what is mechanized, from stale data. Regenerate and compare.
    """
    gen = ROOT / "evals" / "build_ledger.py"
    if not gen.exists() or not (ROOT / "lessons").is_dir():
        return
    proc = subprocess.run(
        [sys.executable, str(gen), "--check"], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        r.fail("L18", (proc.stderr or proc.stdout).strip()
                      or "LEDGER.md is stale — run python3 evals/build_ledger.py")


# Domains and hosts that legitimately appear in citations, standards links and examples.
# Anything else that looks like a real host in a contributed lesson is treated as a leak.
ALLOWED_HOSTS = {
    "example.com", "example.org", "example.net", "localhost", "vigil.example",
    "github.com", "raw.githubusercontent.com", "apache.org", "www.apache.org",
    "nvlpubs.nist.gov", "csrc.nist.gov", "cwe.mitre.org", "owasp.org",
    "artificialintelligenceact.eu", "isms.online", "pypi.org", "hackerone.com",
    "foundry.paradigm.xyz", "bandit.readthedocs.io", "claude.com", "evil.com",
    "meridian-holdings.example", "northwind.example", "old.example.com",
    "new.example.com", "moonshot.cn",
}

LEAK_PATTERNS = (
    # No username is exempt. An earlier version excluded the maintainer's own login to
    # silence a false positive, which made the check blind to precisely the paths most
    # likely to leak from the maintainer's machine — and baked that login into the repo.
    (r"/(?:Users|home)/[a-z][a-z0-9._-]{2,}/", "an absolute home directory path"),
    (r"C:\\Users\\[A-Za-z]", "an absolute Windows user path"),
    (r"\b(?:sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})",
     "something shaped like an API key"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY", "a private key block"),
    (r"\b[A-Za-z0-9._%+-]+@(?!example\.|.*\.example\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
     "an email address"),
)


def check_contributed_privacy(r: Report) -> None:
    """L19 — contributed material must not carry anyone's real work.

    `lessons/` and `evals/results/` are the surfaces where an outside user describes something
    VIGIL got wrong *on their codebase*. That is exactly where proprietary paths, internal
    hosts, customer names and — worst — a description of a real system's security gaps can
    arrive by accident.

    This is not hypothetical. This repo previously shipped a live business's domains, its
    payment-compliance posture and its architecture in `CONTEXT.md` and `templates/`, and it
    took four sweeps to clear because each pass used different words for the same business.
    A contributor with less context will do worse.

    The check is deliberately noisy in one direction: it would rather flag a legitimate
    citation than let one real hostname through.
    """
    surfaces = [p for p in (ROOT / "lessons").glob("*.md")]
    results = ROOT / "evals" / "results"
    if results.is_dir():
        surfaces += list(results.glob("*.md"))
    # proof/ is the third contributed surface, and the one most likely to leak: an entry
    # showing VIGIL caught something real is *trying* to be impressive, and specificity is
    # what makes a war story impressive.
    proof = ROOT / "proof"
    if proof.is_dir():
        surfaces += list(proof.glob("*.md"))

    # A hostname needs a real TLD. Matching "anything.anything" flagged `numpy.ndarray`,
    # `date.today` and the version string `2.3` as hosts — noise that would train a
    # contributor to ignore this check, which is worse than not having it.
    TLDS = (r"com|org|net|io|ai|dev|co|app|cloud|sh|me|xyz|info|biz|"
            r"uk|eu|de|fr|nl|cn|jp|in|au|ca|ae|sa|gov|edu|mil|int")
    host_re = re.compile(
        rf"\b(?:https?://)?((?:[a-z0-9-]+\.)+(?:{TLDS}|example))\b", re.I
    )

    for f in surfaces:
        text = f.read_text(encoding="utf-8")
        rel = f.relative_to(ROOT)
        for pattern, what in LEAK_PATTERNS:
            m = re.search(pattern, text)
            if m:
                r.fail("L19", f"{rel} contains {what}: {m.group(0)[:40]!r} — "
                              "redact before committing")
        for host in set(host_re.findall(text)):
            h = host.lower()
            if h in ALLOWED_HOSTS or h.endswith(".example") or h.endswith(".md"):
                continue
            if re.fullmatch(r"[a-z_.-]+\.(py|md|json|toml|yml|yaml|txt|sha256|csv|parquet|xlsx|sql|html|js|ts)", h):
                continue  # a filename, not a host
            r.fail("L19", f"{rel} names host {host!r}, which is not in ALLOWED_HOSTS — "
                          "if it is a real system, redact it; if it is a legitimate "
                          "citation, add it to the allowlist with a reason")


def check_version_agreement(r: Report) -> None:
    """L20 — every version string agrees with pyproject.toml.

    `ci-adapter.md` advertised 1.0.0 in the SARIF and JSON output while the project was 0.4.0.
    A version in a machine artifact is what a consumer pins against, so a stale one is worse
    than none.
    """
    pyproject = ROOT / "pyproject.toml"
    if not pyproject.exists():
        return
    m = re.search(r'^version = "([^"]+)"', pyproject.read_text(encoding="utf-8"), re.M)
    if not m:
        r.fail("L20", "pyproject.toml declares no version")
        return
    want = m.group(1)
    for f in md_files():
        for found in re.findall(r'"(?:vigil_)?version": "(\d+\.\d+\.\d+)"',
                                f.read_text(encoding="utf-8")):
            # SARIF's own schema version is not ours.
            if found != want and found != "2.1.0":
                r.fail("L20", f"{f.relative_to(ROOT)} says version {found}; "
                              f"pyproject.toml says {want}")


# Strings that are fine while a repo is private and broken the moment it is published.
# `vigil.example` is deliberately absent: an example homepage is honest for a project with
# no homepage, unlike a link that resolves to the wrong place.
PUBLISH_BLOCKERS = (
    ("OWNER/REPO", "a GitHub owner/repo placeholder"),
    ("<this-repo>", "a clone-URL placeholder"),
    ("github.com/user/", "a stub GitHub URL"),
)


def check_publish_placeholders(r: Report) -> None:
    """L21 — no unfilled placeholder may reach a published repo.

    A README telling a new user to `git clone <this-repo>` and an issue form linking to
    OWNER/REPO are the first two things a visitor touches, and both fail silently: the link
    404s, the clone command is not a command. Cheap to leave in, embarrassing to ship.

    LICENSE is exempt. Its appendix contains `[yyyy]` and `[name of copyright owner]` as part
    of the canonical Apache-2.0 text — filling those in would make the file no longer the
    licence it claims to be. Attribution belongs in NOTICE, which is where it is.

    Only fires once a git remote exists. A placeholder is correct while the repo is local and
    the URL is genuinely unknown; it becomes wrong the moment there is somewhere to publish
    to. Failing before then would leave the self-audit permanently red, which teaches people
    to skim past it — the failure mode this check exists to avoid.
    """
    remotes = subprocess.run(
        ["git", "-C", str(ROOT), "remote"], capture_output=True, text=True, check=False
    )
    if not remotes.stdout.strip():
        return
    for f in sorted(ROOT.rglob("*")):
        if not f.is_file() or ".git" in f.relative_to(ROOT).parts:
            continue
        if f.name == "LICENSE" or f.suffix not in (".md", ".yml", ".yaml", ".toml", ".py"):
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for needle, what in PUBLISH_BLOCKERS:
            if needle in text and "PUBLISH_BLOCKERS" not in text:
                r.fail("L21", f"{f.relative_to(ROOT)} contains {what} ({needle!r}) — "
                              "fill it in before publishing")


def check_skill_loadable(r: Report) -> None:
    """L22 — the skill must actually be discoverable by Claude Code.

    Every other check here tests the harness. None tested the product: VIGIL could ship with
    21 green checks and frontmatter Claude Code refuses to parse. Delegates to
    check_loadable.py so the same logic serves both the self-audit and a standalone run.
    """
    script = ROOT / "evals" / "check_loadable.py"
    if not script.exists():
        r.fail("L22", "evals/check_loadable.py is missing")
        return
    proc = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        for line in (proc.stderr or proc.stdout).splitlines():
            if line.strip().startswith("-"):
                r.fail("L22", line.strip().lstrip("- "))


def check_assertion_evals(r: Report) -> None:
    """L23 — assertion evals must stay well-formed.

    These grade whether an audit REASONED correctly, which keyword matching cannot
    (lessons/0005). They are graded by a human or a judge model rather than in CI, which
    means nothing else would notice if they drifted into malformed JSON or empty stubs.
    """
    spec = ROOT / "evals" / "assertions" / "vigil.json"
    if not spec.exists():
        return
    try:
        data = json.loads(spec.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.fail("L23", f"evals/assertions/vigil.json is not valid JSON: {e}")
        return
    evals = data.get("evals", [])
    if not evals:
        r.fail("L23", "assertion spec contains no evals")
        return
    seen: set[int] = set()
    for item in evals:
        eid = item.get("id")
        if eid in seen:
            r.fail("L23", f"duplicate eval id {eid}")
        seen.add(eid)
        for field in ("prompt", "expected_output", "assertions"):
            if not item.get(field):
                r.fail("L23", f"eval {eid} has an empty {field!r}")
        if len(item.get("assertions", [])) < 2:
            r.fail("L23", f"eval {eid} has fewer than 2 assertions — one assertion is a "
                          "restatement of the prompt, not a grading criterion")


def check_stated_check_count(r: Report) -> None:
    """L24 — a prose restatement of the check count must match reality.

    Found the hard way: this repo simultaneously claimed 19, 22 and 23 checks in three
    different files. Nothing noticed, because the count is authored prose and the authority is
    code. That is precisely the drift L13 and L20 already mechanize for weights and versions —
    the number that says how much verification exists is a strange one to leave unverified.

    `lessons/`, `proof/` and `CHANGELOG.md` are exempt: "at the time there were six checks" is
    a historical statement, and correcting it would falsify the record it exists to keep.

    CI workflows are in scope. The count first drifted in a step *name* — prose in YAML is
    still prose, and scanning only markdown would have left the same claim wrong in the one
    place every contributor reads first.
    """
    src = Path(__file__).read_text(encoding="utf-8")
    real = len(set(re.findall(r'r\.fail\("(L\d+)"', src)))
    if not real:
        r.fail("L24", "could not count checks from this file's own r.fail calls")
        return
    # "26 checks", "26 structural checks", "26 structural self-checks" — the phrasing varies
    # and every variant is the same claim.
    stated = re.compile(r"\b(\d+)[ -](?:structural[ -])?(?:self-)?checks\b")
    scanned = [f for f in md_files()
               if f.relative_to(ROOT).parts[0] not in ("lessons", "proof")
               and f.name != "CHANGELOG.md"]
    scanned += sorted((ROOT / ".github").rglob("*.yml"))
    scanned += sorted((ROOT / ".github").rglob("*.yaml"))
    for f in scanned:
        rel = f.relative_to(ROOT)
        for m in stated.finditer(f.read_text(encoding="utf-8")):
            if int(m.group(1)) != real:
                r.fail("L24", f"{rel} says {m.group(1)} checks; {real} are implemented")


def check_record_schema_closed(r: Report) -> None:
    """L25 — the run-record schema must stay incapable of holding free text.

    The privacy promise for field telemetry is not "we redact" — it is that a path, hostname or
    finding description has **no field to occupy**. That property is worth exactly as much as
    it is enforced, and it dies quietly: one `{"type": "string"}` added in a hurry to capture
    "just the tool version" reopens the whole surface, and every existing test still passes.

    So: every object closed, and every string constrained by enum, const or pattern. A schema
    that cannot represent prose cannot leak it, which is a stronger guarantee than L19 (which
    greps prose and says openly that it cannot read it).
    """
    path = ROOT / "schemas" / "run-record.schema.json"
    if not path.exists():
        return
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        r.fail("L25", f"run-record schema is not valid JSON: {e}")
        return

    def walk(node: object, where: str) -> None:
        if not isinstance(node, dict):
            return
        is_object = node.get("type") == "object" or "properties" in node
        if is_object and node.get("additionalProperties") is not False:
            r.fail("L25", f"{where} is an object without additionalProperties:false — "
                          "an unknown key would be accepted, which is how content arrives")
        if node.get("type") == "string" and not (
            "enum" in node or "const" in node or "pattern" in node
        ):
            r.fail("L25", f"{where} is an unconstrained string — this is a free-text field, "
                          "and a free-text field can hold the user's work")
        for key, child in node.get("properties", {}).items():
            walk(child, f"{where}.{key}")
        for key, child in node.get("definitions", {}).items():
            walk(child, f"{where}#{key}")
        if "items" in node:
            walk(node["items"], f"{where}[]")

    walk(schema, "run-record")


PROOF_VOCAB: dict[str, set[str]] = {
    "cluster": set(),  # filled from the clusters themselves — see below
    "severity": {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"},
    "disposition": {"accepted", "false_positive", "duplicate", "deferred",
                    "wrong_severity", "not_reachable"},
}


def check_proof_entries(r: Report) -> None:
    """L26 — proof entries must be well-formed and use the controlled vocabulary.

    `proof/` answers "is this worth running?" the way `lessons/` answers "should I trust it?".
    Both are contributed surfaces, so both need a shape a maintainer can check quickly. Free
    text in a frontmatter field is where a repo name would land, and an unknown cluster prefix
    means the entry cannot be counted in the ledger.
    """
    proof = ROOT / "proof"
    if not proof.is_dir():
        return
    vocab = dict(PROOF_VOCAB)
    # Bare prefixes, as RULES.md Rule 6 defines them — `SEC`, not `VIGIL-SEC`. Using the
    # finding-ID form here was the same mistake the record schema made, and having two
    # vocabularies for one concept is precisely what L29 exists to stop.
    vocab["cluster"] = set(cluster_prefixes()) | {"CORR"}

    seen: dict[str, Path] = {}
    for f in sorted(proof.glob("[0-9]*.md")):
        text = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", text, re.S)
        if not m:
            r.fail("L26", f"{f.name} has no frontmatter")
            continue
        fields = dict(re.findall(r"^([a-z_]+):\s*(.*)$", m.group(1), re.M))
        for required in ("id", "date", "cluster", "severity", "class"):
            if not fields.get(required, "").strip():
                r.fail("L26", f"{f.name} is missing frontmatter field {required!r}")
        for field, allowed in vocab.items():
            value = fields.get(field, "").strip()
            if value and value not in allowed:
                r.fail("L26", f"{f.name}: {field}={value!r} is not in the controlled "
                              f"vocabulary — free text here is where a real system lands")
        pid = fields.get("id", "").strip()
        if pid in seen:
            r.fail("L26", f"{f.name} reuses id {pid!r} (also {seen[pid].name})")
        seen[pid] = f
        if not re.search(r"^## What generalises$", text, re.M):
            r.fail("L26", f"{f.name} has no '## What generalises' section — without it the "
                          "entry is an incident report, not proof of a class")


def check_corpus_bundles(r: Report) -> None:
    """L27 — every contributed bundle in corpus/ still passes the privacy gate.

    The gate runs when a bundle is submitted. That is the wrong time to stop checking: the
    schema tightens, a leak shape gets added, someone edits a bundle by hand in a later PR to
    "fix" a count. A file that was clean on the day it merged is not the same claim as a file
    that is clean now, and corpus/ is public and permanent.

    So this re-derives it on every push. Cheap — the whole corpus is small JSON — and it means
    the guarantee is continuous rather than a fact about one moment in the git history.
    """
    corpus = ROOT / "corpus"
    if not corpus.is_dir():
        return
    bundles = sorted(corpus.rglob("*.json"))
    if not bundles:
        return
    proc = subprocess.run(
        [sys.executable, str(ROOT / "evals" / "privacy_gate.py"), "--bundles",
         *[str(b) for b in bundles]],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        for line in (proc.stderr or proc.stdout).strip().splitlines():
            if line.strip().startswith("-") or line.startswith("BLOCKED"):
                r.fail("L27", line.strip().lstrip("- "))


# Each: (what it guarantees, pattern that must appear in engines/telemetry.md).
# Prose, because the prompt is executed by a model reading this file — there is no function to
# unit-test. That is a real limit and worth stating plainly: this check proves the instruction
# is present and unambiguous, not that a given run obeyed it.
CONSENT_CLAUSES: list[tuple[str, str]] = [
    # Each alternative must be false when the guarantee is gone. An earlier version of this
    # clause accepted a bare "default —", which still matched after the default was flipped to
    # `[y] yes (default — nothing leaves this machine)`. The check passed while the guarantee
    # was inverted, and its own mutation test passed for an unrelated reason. A loose
    # alternative in a prose check is the same defect as a porous evidence gate (lessons/0005).
    ("sharing defaults to no", r"default is no\b|\[n\][^\n]*\bdefault"),
    ("silence is not consent", r"enter must select it|enter selects no|says nothing, nothing"),
    ("non-interactive is not consent", r"non-interactive means no\b"),
    ("a decline is honoured", r"is not asked\s*\n?again|honour a no|never re-asked"),
    ("the user can see the exact record", r"prints the record in full|show me exactly"),
    ("VIGIL does not transmit", r"does not transmit|no endpoint|never transmitted"),
    ("there is an off switch", r"telemetry:\s*off"),
]


def check_consent_contract(r: Report) -> None:
    """L28 — the end-of-run consent contract must survive edits to telemetry.md.

    The whole field-learning design rests on one moment: the user is told a record exists and
    asked, with `no` as the default, what to do with it. Every other control — closed schema,
    privacy gate, contributor floor — is downstream of that and worthless without it.

    It is also the easiest thing in the repo to erode, because each individual softening is
    defensible in isolation: drop the disclosure because it is noisy, default to yes because
    participation is low, treat `--ci` as consent because nobody is watching anyway. None of
    those look like removing consent in a diff. This asserts each clause is still there.
    """
    path = ROOT / "engines" / "telemetry.md"
    if not path.exists():
        r.fail("L28", "engines/telemetry.md is missing — the consent contract lives there")
        return
    text = path.read_text(encoding="utf-8")
    for guarantee, pattern in CONSENT_CLAUSES:
        if not re.search(pattern, text, re.I):
            r.fail("L28", f"telemetry.md no longer states that {guarantee} — if this was "
                          "deliberate, the design changed and that is a conversation, "
                          "not a commit")

    # SKILL.md is what a model actually routes through, so the ask has to be visible there too.
    # A contract documented only in the engine is a contract the router can skip.
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if "telemetry.md" in skill and not re.search(r"ask|consent", skill, re.I):
        r.fail("L28", "SKILL.md routes to telemetry.md without mentioning the ask — the "
                      "router is what runs, so the consent step must be visible there")


def check_schema_prefixes(r: Report) -> None:
    """L29 — the record schema's cluster vocabulary must match RULES.md.

    Version 1 of the schema required `VIGIL-SEC` where RULES.md Rule 6 defines the prefix as
    `SEC` — `VIGIL-SEC-001` is the finding *ID*, not the prefix. Nothing caught it, because
    every check compared the schema to itself and every test used fixtures I wrote from the
    same misunderstanding. The first real run record failed validation on 100+ counts, none of
    them privacy violations; it was a vocabulary disagreement between two files that both
    claimed to define the same thing.

    L3 already ties RULES.md to the cluster files. This ties the schema to RULES.md, so the
    three cannot drift apart in a way only a live run would reveal.
    """
    schema_path = ROOT / "schemas" / "run-record.schema.json"
    if not schema_path.exists():
        return
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return  # L25 reports the malformed-JSON case
    declared = schema.get("definitions", {}).get("clusterPrefix", {}).get("enum")
    if not declared:
        r.fail("L29", "run-record schema has no definitions.clusterPrefix enum — the cluster "
                      "vocabulary must be declared in one place so it can be checked")
        return

    rules = (ROOT / "RULES.md").read_text(encoding="utf-8")
    listed = set(re.findall(r"^- `([A-Z-]+)`\s+—", rules, re.M))
    if not listed:
        r.fail("L29", "could not parse the prefix list out of RULES.md")
        return

    for extra in sorted(set(declared) - listed):
        r.fail("L29", f"schema permits cluster prefix {extra!r}, which RULES.md does not list")
    for absent in sorted(listed - set(declared)):
        r.fail("L29", f"RULES.md lists prefix {absent!r}, which the record schema rejects — "
                      "a real run emitting it would be blocked by the privacy gate")


def main() -> int:
    if not ROOT.joinpath("SKILL.md").exists():
        print(f"harness error: {ROOT} does not look like the vigil skill", file=sys.stderr)
        return 2
    r = Report()
    check_links(r)
    check_skill_refs(r)
    check_cluster_headers(r)
    check_prefixes(r)
    check_orphans(r)
    check_weight_table(r)
    check_mode_cluster_coverage(r)
    check_compliance_citations(r)
    check_pattern_count(r)
    check_template_weights(r)
    check_exit_codes(r)
    check_threshold_floors(r)
    check_cluster_header_weights(r)
    check_prose_section_refs(r)
    check_downgrade_fences(r)
    check_score_formula(r)
    check_lessons_ledger(r)
    check_ledger_dashboard(r)
    check_contributed_privacy(r)
    check_version_agreement(r)
    check_publish_placeholders(r)
    check_skill_loadable(r)
    check_assertion_evals(r)
    check_stated_check_count(r)
    check_record_schema_closed(r)
    check_proof_entries(r)
    check_corpus_bundles(r)
    check_consent_contract(r)
    check_schema_prefixes(r)
    return r.emit()


if __name__ == "__main__":
    sys.exit(main())
