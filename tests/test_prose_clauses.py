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
    # ── L28 · the end-of-run consent contract ──────────────────────────────────────────
    ("L28", "engines/telemetry.md", "**The default is no, and enter must select it.**",
     "**The default is yes.**"),
    ("L28", "engines/telemetry.md", "[n] no  (default", "[y] yes (default"),
    ("L28", "engines/telemetry.md", "enter must select it", "enter may select either"),
    ("L28", "engines/telemetry.md", "**non-interactive means no**",
     "**non-interactive means proceed**"),
    ("L28", "engines/telemetry.md", "is not asked\nagain", "is asked again"),
    ("L28", "engines/telemetry.md", "prints the record in full",
     "prints a summary of the record"),
    ("L28", "engines/telemetry.md", "does not transmit", "transmits"),
    ("L28", "engines/telemetry.md", "`.vigil/telemetry: off` disables record writing entirely",
     "record writing cannot be disabled"),

    # ── L30 · a tool must resolve inside the subject's environment ─────────────────────
    ("L30", "engines/preflight.md", "must resolve inside the subject",
     "may resolve anywhere relative to the subject"),
    ("L30", "engines/preflight.md", "absolute path of every tool", "name of every tool"),
    ("L30", "engines/preflight.md", "cannot contribute to a ceiling of 100",
     "may still contribute to a ceiling of 100"),
    ("L30", "engines/preflight.md", "clean result is **not\n> evidence**",
     "clean result is **evidence**"),
    ("L30", "engines/preflight.md", "project-local invocation", "global invocation"),

    # ── L31 · a control's presence is not its efficacy ─────────────────────────────────
    ("L31", "RULES.md", "may reduce a finding's severity only on demonstrated efficacy",
     "may reduce a finding's severity without demonstrated efficacy"),
    ("L31", "RULES.md", "| **Executed**", "| Executed"),
    ("L31", "RULES.md", "That is necessary and **not sufficient**",
     "That is necessary and sufficient"),
    ("L31", "RULES.md", "| **Present** | it exists in the code and looks correct | **no** |",
     "| **Present** | it exists in the code and looks correct | yes |"),
    ("L31", "RULES.md", "including its empty, first-call and error branches",
     "including its steady-state branches"),
    ("L31", "RULES.md", "the finding keeps its undiminished\nseverity",
     "the finding loses its severity"),

    # ── L32 · a scanner hit is a pointer, not an answer ────────────────────────────────
    ("L32", "RULES.md", "pointer to a question, not an answer to it",
     "pointer to a question and its answer"),
    ("L32", "RULES.md", "required **starting** point, never\nbecause it is a sufficient",
     "required point, and sufficient"),
    ("L32", "RULES.md", "read the flagged location", "skim the flagged location"),
    ("L32", "RULES.md", "Scanners do not read comments.", "Scanners read comments."),
    ("L32", "RULES.md", "is not a fix, and a finding whose only remedy is destructive",
     "is an acceptable fix, and a finding whose only remedy is destructive"),
    ("L32", "RULES.md", "Withdrawing a hit is harder than reducing one",
     "Withdrawing a hit is easier than reducing one"),
    ("L32", "RULES.md", "A withdrawn hit is reported as withdrawn",
     "A withdrawn hit may go unreported"),

    # ── L33 · name the tree that was audited ──────────────────────────────────────────
    ("L33", "RULES.md", "permitted **only when the tree is\nclean**",
     "permitted **in every case**"),
    ("L33", "RULES.md", "tracked only", "whatever was scanned"),
    ("L33", "RULES.md", "different subjects", "the same subject"),
    ("L33", "RULES.md", "refuse the delta when the kinds differ",
     "compute the delta regardless of kind"),
    ("L33", "RULES.md", "Secret and PII scans read ignored paths too",
     "Secret and PII scans never read ignored paths too"),
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


def test_every_clause_has_an_inversion_probe() -> None:
    """One probe per CLAUSE, not per check.

    The first version of this test compared table-count to check-count, which a cross-model
    review showed proves almost nothing: a five-clause check passes its single mutation if any
    ONE clause fires, leaving the other four free to match incidental text. Four such clauses
    were leaking at the time — L30, L31 (x2) and L33 — while this test was green.

    Counting probes per check is the weakest assertion that would have caught them.
    """
    import sys
    sys.path.insert(0, str(REPO / "evals"))
    import check_repo as C

    tables = {"L28": C.CONSENT_CLAUSES, "L30": C.RESOLUTION_CLAUSES,
              "L31": C.EFFICACY_CLAUSES, "L32": C.POINTER_CLAUSES,
              "L33": C.SUBJECT_CLAUSES}
    probes: dict[str, int] = {}
    for check_id, *_ in INVERSIONS:
        probes[check_id] = probes.get(check_id, 0) + 1

    thin = {c: (probes.get(c, 0), len(t)) for c, t in tables.items()
            if probes.get(c, 0) < len(t)}
    assert not thin, (
        "clauses without their own inversion probe (check: probes/clauses) — "
        f"{thin}. A clause with no probe can match incidental text and keep the check "
        "green while its rule says the opposite. See AGENTS.md, 'Mutating a prose check'."
    )



# ───────────────────────────────────── the two attacks that beat the fragment form


NEGATION_ATTACKS: list[tuple[str, str, str, str]] = [
    # Insertion. Every word of the rule survives; a clause is spliced into the middle that
    # reverses it. The fragment `only on demonstrated efficacy` matched the result verbatim.
    ("L31", "RULES.md",
     "**A mitigation may reduce a finding's severity only on demonstrated efficacy.**",
     "**A mitigation may reduce a finding's severity — and this is deliberately not "
     "restricted to only on demonstrated efficacy; a control that is present and wired up "
     "is enough.**"),
    # Historical quotation. The rule is preserved word for word and demoted to a description
    # of what used to be true. This one flipped consent to OPT-OUT with all eight L28 clauses
    # green, which is the most damaging single edit anyone could make to this repository.
    ("L28", "engines/telemetry.md",
     "**The default is no, and enter must select it.** If the user says nothing, "
     "nothing is shared.",
     "**The default is yes.** Earlier versions specified that **The default is no, and enter "
     "must select it.** If the user says nothing, nothing is shared. That is no longer the "
     "behaviour."),
]


@pytest.mark.parametrize("check_id,rel,old,new", NEGATION_ATTACKS,
                         ids=[f"{c}-{r.split('/')[-1]}" for c, r, _, _ in NEGATION_ATTACKS])
def test_negating_around_an_intact_rule_is_caught(
    tmp_path: Path, check_id: str, rel: str, old: str, new: str
) -> None:
    """A rule can be reversed without deleting a word of it. That must not pass.

    Both edits below left every fragment the old checks searched for exactly where it was, and
    both were reported clean. They are not adversarial constructions — keeping the old sentence
    as a historical note is how documentation drifts in every repository.

    A regex cannot prove meaning, and this does not claim to. It claims that the sentence
    stating a rule must appear *as* that rule: intact, beginning a sentence, and not walked
    back by the prose around it.
    """
    dst = tmp_path / "vigil"
    shutil.copytree(REPO, dst, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache", "export"))
    target = dst / rel
    text = target.read_text(encoding="utf-8")
    assert old in text, f"anchor drifted in {rel}"
    target.write_text(text.replace(old, new, 1), encoding="utf-8")

    proc = subprocess.run([sys.executable, str(dst / "evals" / "check_repo.py")],
                          capture_output=True, text=True, check=False)
    out = proc.stdout + proc.stderr
    assert proc.returncode != 0, f"the rule was reversed and the audit passed:\n{out}"
    assert f"[{check_id}]" in out, f"expected {check_id} to object, got:\n{out}"
