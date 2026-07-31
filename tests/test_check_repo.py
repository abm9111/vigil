#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""Every self-audit check must be able to FAIL.

A check that has never been observed failing is decoration. During development each check was
verified by hand — inject a fault, watch it fire, restore. That verification was real and
completely ephemeral: nobody could re-run it, and a refactor could silently neuter a check
while the suite stayed green.

This codifies it. Each test copies the repo to a temp dir, breaks exactly one invariant, and
asserts the corresponding check reports it. `test_baseline_is_clean` asserts the unmodified
repo passes, so a test that fails for the wrong reason is distinguishable from a real fault.

    pytest tests/ -q
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def run_check(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / "evals" / "check_repo.py")],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A throwaway copy. Tests mutate it freely; the real repo is never touched."""
    dst = tmp_path / "vigil"
    shutil.copytree(
        REPO, dst,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "export"
        ),
    )
    return dst


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"anchor not found in {path.name}: {old[:60]!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def edit_all(path: Path, old: str, new: str) -> None:
    """Replace every occurrence.

    Several anchors appear twice — a markdown link carries its target in both the text and
    the href. Replacing only the first left the invariant intact and the check correctly
    stayed silent, which read as a broken check until the mutation was inspected.
    """
    text = path.read_text(encoding="utf-8")
    assert old in text, f"anchor not found in {path.name}: {old[:60]!r}"
    path.write_text(text.replace(old, new), encoding="utf-8")


def strip_lines(path: Path, *needles: str) -> None:
    """Drop every line containing any needle — for invariants asserted in several places."""
    text = path.read_text(encoding="utf-8")
    kept = [ln for ln in text.splitlines() if not any(n in ln for n in needles)]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def test_baseline_is_clean(repo: Path) -> None:
    """The unmodified repo must pass. Without this, every other test is ambiguous."""
    code, out = run_check(repo)
    assert code == 0, f"baseline is not clean:\n{out}"


def flip_share_default(repo: Path) -> None:
    """Flip the sharing default from no to yes — the realistic erosion of L28.

    Two small edits, neither of which reads as removing consent in a diff. This replaced an
    earlier mutation that deleted whole lines: the deletion fired, but for the wrong reason —
    it removed enough text to trip a different alternative in the clause, while an actual
    default-flip sailed through. Mutate the way a person would, not the way that is easy.
    """
    telemetry = repo / "engines" / "telemetry.md"
    edit(telemetry, "**The default is no, and enter must select it.**",
         "**The default is yes.**")
    edit(telemetry, "[n] no  (default", "[y] yes (default")


# Each entry: check id, a mutation that breaks exactly that invariant.
BREAKERS: list[tuple[str, Callable[[Path], None]]] = [
    ("L1", lambda r: edit(r / "README.md", "## Status", "See [x](engines/nope.md).\n\n## Status")),
    ("L2", lambda r: (r / "engines" / "preflight.md").unlink()),
    ("L3", lambda r: edit(r / "RULES.md", "- `EGRESS` — Data Egress & Provenance\n", "")),
    ("L4", lambda r: edit(r / "clusters" / "security.md", "**ID prefix:**", "**Prefix:**")),
    ("L6", lambda r: edit(r / "engines" / "scoring.md",
                          "| Blockchain | 8% |", "| Blockchain-X | 8% |")),
    ("L7", lambda r: edit_all(r / "modes" / "audit.md",
                              "blockchain.md", "REMOVED.md")),
    ("L8", lambda r: edit(r / "engines" / "correlation.md",
                          "**Compliance:** SOC2:CC6.1", "**Compliance:** SOC2:ZZ9.9")),
    ("L9", lambda r: edit(r / "modes" / "audit.md",
                          "Run all 10 correlation pattern matchers",
                          "Run 7 correlation pattern matchers")),
    ("L10", lambda r: edit(r / "modes" / "audit.md",
                           "SEC     {score}/100  {grade}  {trend}  (weight: 22%)",
                           "SEC     {score}/100  {grade}  {trend}  (weight: 30%)")),
    ("L11", lambda r: strip_lines(r / "FLAGS.md", "N/E")),
    ("L12", lambda r: edit(r / "evals" / "expected" / "data-export-pipeline.json",
                           '"min_recall": 0.8', '"min_recall": 0.2')),
    ("L13", lambda r: edit(r / "clusters" / "blockchain.md", "**Weight:** 8%", "**Weight:** 33%")),
    ("L14", lambda r: edit(r / "CONTEXT.md", "## Core Concepts",
                           "See `engines/scoring.md` -> No Such Section Here.\n\n## Core Concepts")),
    ("L15", lambda r: strip_lines(r / "modes" / "siege.md",
                                  "positive evidence", "never the severity floor",
                                  "never the** severity floor", "severity floor")),
    ("L16", lambda r: strip_lines(r / "engines" / "scoring.md", "cluster_score = min(ceiling")),
    ("L17", lambda r: edit(r / "lessons" / "0001-checker-clean-over-real-gaps.md",
                           "check: L7, L8", "check: L999")),
    ("L18", lambda r: (r / "LEDGER.md").write_text("stale\n", encoding="utf-8")),
    ("L19", lambda r: edit(r / "lessons" / "0001-checker-clean-over-real-gaps.md",
                           "## What was believed",
                           "Seen at /Users/alice/work/acme/src.\n\n## What was believed")),
    ("L20", lambda r: edit(r / "engines" / "ci-adapter.md",
                           '"vigil_version": "0.4.0"', '"vigil_version": "9.9.9"')),
    ("L22", lambda r: edit(r / "SKILL.md", "name: vigil", "nom: vigil")),
    ("L23", lambda r: edit(r / "evals" / "assertions" / "vigil.json",
                           '"id": 2,', '"id": 1,')),
    # Inject a bogus claim rather than mutating the real one: anchoring on the current count
    # makes this test fail every time a check is added, which is the opposite of useful.
    ("L24", lambda r: edit(r / "README.md", "## Status",
                           "It runs 999 checks.\n\n## Status")),
    # The mutation that matters most: one unconstrained string reopens the whole surface,
    # and every other test in this file still passes.
    ("L25", lambda r: edit(r / "schemas" / "run-record.schema.json",
                           '"partial_score": { "type": "integer"',
                           '"notes": { "type": "string" },\n    '
                           '"partial_score": { "type": "integer"')),
    # Drop a prefix RULES.md defines. A real run emitting it would be silently blocked by the
    # privacy gate — which is exactly what happened before L29 existed.
    ("L29", lambda r: edit(r / "schemas" / "run-record.schema.json",
                           '"SEC", "CODE",', '"CODE",')),
    ("L26", lambda r: edit(r / "proof" / "0001-secret-removed-from-tree-still-live-in-history.md",
                           "severity: HIGH", "severity: SEVERE")),
    ("L28", flip_share_default),
]


@pytest.mark.parametrize("check_id,break_it", BREAKERS, ids=[b[0] for b in BREAKERS])
def test_check_fires_when_broken(
    repo: Path, check_id: str, break_it: Callable[[Path], None]
) -> None:
    """Break one invariant; the matching check must report it."""
    break_it(repo)
    code, out = run_check(repo)
    assert code != 0, f"{check_id}: repo was broken but the self-audit passed:\n{out}"
    assert f"[{check_id}]" in out, f"expected {check_id} to fire, got:\n{out}"


def test_l27_regates_a_corpus_bundle(repo: Path) -> None:
    """L27 is separate: the real repo ships no bundles, so the test supplies one.

    Both halves matter. A clean bundle must not fire — a check that flags every contribution
    trains maintainers to ignore it. A bundle that leaks must fire even though it was
    presumably gated when it merged, because the schema and the leak shapes both move.
    """
    corpus = repo / "corpus"
    clean = {
        "schema_version": 1, "contributor": "someone", "vigil_version": "0.4.0",
        "records": [{
            "schema_version": 1, "vigil_version": "0.4.0", "mode": "audit",
            "clusters": [{"prefix": "SEC", "verdict": "scored"}],
            "shared": "asked-accepted",
        }],
    }
    (corpus / "someone.json").write_text(json.dumps(clean), encoding="utf-8")
    code, out = run_check(repo)
    assert code == 0 and "[L27]" not in out, f"L27 fired on a clean bundle:\n{out}"

    leaking = json.loads(json.dumps(clean))
    leaking["records"][0]["repo_path"] = "/Users/alice/work/acme"
    (corpus / "someone.json").write_text(json.dumps(leaking), encoding="utf-8")
    code, out = run_check(repo)
    assert code != 0 and "[L27]" in out, f"L27 did not re-gate a leaking bundle:\n{out}"


def test_l5_catches_an_orphan(repo: Path) -> None:
    """L5 is separate: it needs a new unreferenced file rather than an edit."""
    (repo / "engines" / "orphan-engine.md").write_text(
        "# Orphan\n\nReferenced by nothing.\n", encoding="utf-8"
    )
    code, out = run_check(repo)
    assert code != 0 and "[L5]" in out, f"L5 did not catch an orphan engine:\n{out}"


def test_l21_fires_only_once_a_remote_exists(repo: Path) -> None:
    """Publish placeholders are correct while local, wrong once there is somewhere to push.

    Both halves matter: firing early leaves the self-audit permanently red, and not firing
    at all ships `git clone <this-repo>` to a stranger.
    """
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    code, out = run_check(repo)
    assert code == 0 and "[L21]" not in out, f"L21 fired with no remote:\n{out}"

    subprocess.run(
        ["git", "remote", "add", "origin", "https://example.com/x.git"], cwd=repo, check=True
    )
    code, out = run_check(repo)
    assert code != 0 and "[L21]" in out, f"L21 did not fire with a remote set:\n{out}"


def test_every_documented_check_has_a_test() -> None:
    """The suite must keep pace with the checks.

    Adding a check without a test recreates the exact gap this file exists to close, so the
    omission is itself a failure rather than something noticed later.
    """
    src = (REPO / "evals" / "check_repo.py").read_text(encoding="utf-8")
    documented = set(re.findall(r"^  (L\d+) ", src, re.M))
    tested = {b[0] for b in BREAKERS} | {"L5", "L21", "L27"}
    missing = documented - tested
    assert not missing, f"checks with no failing-case test: {sorted(missing)}"
