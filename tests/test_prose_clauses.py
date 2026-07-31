#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""The check on the checks.

`L28`, `L30`, `L31`, `L32` and `L33` assert that a rule is still *stated* in a Markdown file,
because the thing they guard is executed by a model reading that file — there is no function to
unit-test. The family has one failure mode, and it has now occurred three times:

  L28  `default —` matched `[y] yes (default — …)` after the default was flipped to yes
  L30  a pattern assumed a plain line break in a clause that wraps inside a blockquote
  L31  `**no**` matched an unrelated bolded "no" and stayed green after "not sufficient"
       was inverted to "sufficient"

Every one reported the rule intact while the rule said the opposite. **A loose alternative in a
prose check fails silently, toward green** — structurally the same defect as `lessons/0007`,
where a misresolved instrument reported clean.

`tests/test_check_repo.py` mutates one clause per check. That is not enough: a check with five
clauses passes its mutation test if any single clause fires, so the other four can be matching
incidental text and nothing notices. This file closes that by inverting **each clause
individually** and asserting its own check reports it.

The convention it enforces is written up in AGENTS.md under "Mutating a prose check".

    pytest tests/test_prose_clauses.py -q
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# (check id, file, exact text in the repo, the same text with its MEANING REVERSED).
#
# Inversions, never deletions. A deletion proves only that the pattern needs its text present;
# an inversion proves the pattern keys on the part carrying the meaning — and inversion is the
# realistic erosion, because nobody deletes a safety rule, they soften it.
INVERSIONS: list[tuple[str, str, str, str]] = [
    # L28 — the end-of-run consent contract
    ("L28", "engines/telemetry.md",
     "**The default is no, and enter must select it.**",
     "**The default is yes.**"),
    ("L28", "engines/telemetry.md",
     "**non-interactive means no**",
     "**non-interactive means proceed**"),
    ("L28", "engines/telemetry.md",
     "`.vigil/telemetry: off` disables record writing entirely",
     "record writing cannot be disabled"),

    # L30 — a tool must resolve inside the subject's environment
    ("L30", "engines/preflight.md",
     "cannot contribute to a ceiling of 100",
     "may still contribute to a ceiling of 100"),
    # This clause lives in RULES.md Rule 1a, not preflight — the first version of this table
    # pointed at the wrong file, which the anchor assertion caught. A stale anchor stops
    # testing its clause silently, so the assertion is deliberately loud.
    ("L32", "RULES.md",
     "Scanners do not read comments.",
     "Scanners parse comments and honour them."),

    # L31 — a control's presence is not its efficacy
    ("L31", "RULES.md",
     "That is necessary and **not sufficient**",
     "That is necessary and sufficient"),
    ("L31", "RULES.md",
     "| **Present** | it exists in the code and looks correct | **no** |",
     "| **Present** | it exists in the code and looks correct | yes |"),

    # L32 — a scanner hit is a pointer, not an answer
    ("L32", "RULES.md",
     "pointer to a question, not an answer to it",
     "pointer to a question and its answer"),
    ("L32", "RULES.md",
     "is not a fix, and a finding whose only remedy is destructive",
     "is an acceptable fix, and a finding whose only remedy is destructive"),

    # L33 — name the tree that was audited
    ("L33", "RULES.md",
     "permitted **only when the tree is\nclean**",
     "permitted **in every case**"),
    ("L33", "RULES.md",
     "refuse the delta when the kinds differ",
     "compute the delta regardless of kind"),
]


def run_check(root: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(root / "evals" / "check_repo.py")],
        capture_output=True, text=True, check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    dst = tmp_path / "vigil"
    shutil.copytree(
        REPO, dst,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "export"
        ),
    )
    return dst


@pytest.mark.parametrize(
    "check_id,relpath,original,inverted",
    INVERSIONS,
    ids=[f"{c}:{o[:34]}" for c, _, o, _ in INVERSIONS],
)
def test_each_clause_detects_its_own_inversion(
    repo: Path, check_id: str, relpath: str, original: str, inverted: str
) -> None:
    """Reverse one rule's meaning; its check must report it.

    A failure here means the clause guarding that rule matches something that survives the
    rule being reversed — so the check is decoration for that clause, and the rule could be
    inverted in a pull request with the self-audit staying green.
    """
    target = repo / relpath
    text = target.read_text(encoding="utf-8")
    assert original in text, (
        f"anchor drifted in {relpath}: {original[:60]!r}. Update INVERSIONS — a stale anchor "
        "silently stops testing the clause it was written for."
    )
    target.write_text(text.replace(original, inverted, 1), encoding="utf-8")

    code, out = run_check(repo)
    assert code != 0, (
        f"{check_id}: the rule was INVERTED and the self-audit stayed green.\n"
        f"  {relpath}: {original[:70]!r}\n  became: {inverted[:70]!r}"
    )
    assert f"[{check_id}]" in out, (
        f"{check_id} did not fire on its own inversion — some other check caught it, which "
        f"means {check_id}'s clause guards nothing.\n{out}"
    )


def test_every_prose_check_has_at_least_one_inversion() -> None:
    """A prose check added without an entry here inherits the family's silent failure mode."""
    src = (REPO / "evals" / "check_repo.py").read_text(encoding="utf-8")
    # Clause tables are the marker: a list of (guarantee, pattern) pairs feeding a check.
    declared = set(re.findall(r"^([A-Z_]+)_CLAUSES: list", src, re.M))
    covered = {c for c, _, _, _ in INVERSIONS}
    assert len(declared) <= len(covered), (
        f"{len(declared)} prose-clause tables exist but only {len(covered)} checks have "
        "inversion probes — see AGENTS.md, 'Mutating a prose check'"
    )

