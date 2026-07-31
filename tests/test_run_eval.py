#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""Regression tests for the eval scorer.

`run_eval.py` has had **six** bugs, every one of which produced a confidently wrong number —
in both directions. A false 50% on a run that had found everything, and a false 100% on runs
containing no analysis at all. Each was found by a human or a cross-model reviewer, fixed, and
verified once by hand.

Every test below is one of those bugs. They are not hypothetical failure modes; they all
shipped. If one starts passing when it should fail, the harness has regressed to a state it
has already been in.

    pytest tests/ -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))

from run_eval import has_evidence, parse_findings, score  # noqa: E402


def spec(**over: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "must_detect": [
            {
                "id": "defect-a", "severity": "HIGH", "file": "app.py",
                "signals": ["ndarray", "numpy"], "lines": [31],
            },
            {
                "id": "defect-b", "severity": "HIGH", "file": "app.py",
                "signals": ["rmtree", "destroy"], "lines": [77],
            },
        ],
        "acceptable_extra": [],
        "max_false_positives": 0,
        "min_recall": 1.0,
        "line_tolerance": 6,
    }
    base.update(over)
    return base


def finding(fid: str, sev: str, text: str, n: int = 0) -> dict[str, str]:
    return {"id": fid, "key": f"{n}:{fid}", "severity": sev, "text": text.lower()}


# --- bug 1: hedged, evidence-free findings scored 100% -----------------------------------

def test_finding_without_a_citation_is_not_a_catch() -> None:
    r = score(spec(), [
        finding("V-1", "HIGH", "app.py ndarray numpy worth a look", 0),
        finding("V-2", "HIGH", "app.py rmtree destroy conventional but worth a note", 1),
    ])
    assert r.recall == 0.0, "findings citing no location must not count"
    assert not r.passed


@pytest.mark.parametrize("text,expected", [
    ("a ratio of 1:2 here", False),          # matched the old `:\d+` gate
    ("section 2.3:1 discusses", False),
    ("we demonstrated the issue", False),    # a word anyone can type
    ("build_export.py:33", True),
    ('"line": 77', True),
])
def test_evidence_gate_needs_a_real_location(text: str, expected: bool) -> None:
    assert has_evidence(text) is expected


# --- bug 2: line anchoring defeated by any incidental number ------------------------------

def test_wrong_lines_with_a_decoy_number_do_not_match() -> None:
    """Extracting every number, not just cited ones, let 'affects 31 rows' satisfy the anchor
    while the finding cited line 5."""
    r = score(spec(), [
        finding("V-1", "HIGH", "app.py:5 ndarray numpy affects 31 rows", 0),
        finding("V-2", "HIGH", "app.py:10 rmtree destroy seen 77 times", 1),
    ])
    assert r.recall == 0.0, "a decoy number must not satisfy the line anchor"


def test_correct_citation_matches() -> None:
    r = score(spec(), [
        finding("V-1", "HIGH", "app.py:31 ndarray numpy coercion", 0),
        finding("V-2", "HIGH", "app.py:77 rmtree destroy before read", 1),
    ])
    assert r.recall == 1.0 and r.passed


# --- bug 3: severity deflation passed --------------------------------------------------

def test_high_reported_as_medium_fails() -> None:
    """One level moves the product from 'not production-ready' (79) to 'ready' (89). An eval
    that passes what the product would ship on is not a gate."""
    r = score(spec(), [
        finding("V-1", "MEDIUM", "app.py:31 ndarray numpy", 0),
        finding("V-2", "HIGH", "app.py:77 rmtree destroy", 1),
    ])
    assert r.severe_deflation and not r.passed


def test_missing_severity_fails() -> None:
    r = score(spec(), [
        finding("V-1", "", "app.py:31 ndarray numpy", 0),
        finding("V-2", "HIGH", "app.py:77 rmtree destroy", 1),
    ])
    assert r.severe_deflation and not r.passed


def test_unrecognised_severity_does_not_crash() -> None:
    """`NEEDS_REVIEW` is blessed by RULES.md and used to raise ValueError, exiting 1 —
    indistinguishable from a real threshold miss."""
    r = score(spec(), [finding("V-1", "NEEDS_REVIEW", "app.py:31 ndarray numpy", 0)])
    assert any("unrecognised" in c for c in r.calibration)


# --- bug 4: id collisions zeroed the false-positive count --------------------------------

def test_findings_without_ids_still_count_as_false_positives() -> None:
    """Keying on a possibly-empty id let one unlabelled finding enter `claimed` and exempt
    every other unlabelled finding — the metric clean-control depends on."""
    r = score(spec(must_detect=[], max_false_positives=0), [
        finding("<unlabelled #0>", "HIGH", "app.py:9 something invented", 0),
        finding("<unlabelled #1>", "HIGH", "app.py:3 also invented", 1),
    ])
    assert len(r.false_positives) == 2


# --- bug 5: Rule 7 cost recall ----------------------------------------------------------

def test_one_correlated_finding_may_claim_several_defects() -> None:
    """An honest audit that correlates two seeded defects scored 83% with one MISSED —
    the harness penalised using the flagship feature."""
    blob = json.dumps({"correlated_findings": [{
        "id": "VIGIL-CORR-001", "severity": "HIGH",
        "contributing": ["VIGIL-A-1", "VIGIL-A-2"],
        "narrative": "app.py:77 rmtree destroy runs before the read; app.py:31 ndarray "
                     "numpy coercion writes reprs",
    }], "findings": []})
    r = score(spec(), parse_findings(f"```json\n{blob}\n```"))
    assert set(r.detected) == {"defect-a", "defect-b"}


def test_a_plain_finding_may_not_claim_two_defects() -> None:
    """The guard on the fix above: without it, recall inflates instead."""
    r = score(spec(), [finding(
        "VIGIL-SEC-001", "HIGH",
        "app.py:77 rmtree destroy and app.py:31 ndarray numpy", 0)])
    assert len(r.detected) == 1


# --- bug 6: parser truncation ------------------------------------------------------------

def test_parser_reads_both_finding_lists() -> None:
    """Reading only `findings` discarded everything correlation had absorbed — which is
    exactly the highest-value set."""
    blob = json.dumps({
        "correlated_findings": [{"id": "VIGIL-CORR-001", "severity": "HIGH", "what": "x"}],
        "findings": [{"id": "VIGIL-SEC-001", "severity": "LOW", "what": "y"}],
    })
    assert len(parse_findings(f"```json\n{blob}\n```")) == 2


def test_an_unrelated_json_block_does_not_win() -> None:
    """'Largest block wins' let a preflight tool array outvote the real report."""
    tools = json.dumps([{"tool": f"t{i}", "findings": 0} for i in range(9)])
    real = json.dumps({"findings": [
        {"id": "VIGIL-SEC-001", "severity": "HIGH", "what": "a"},
        {"id": "VIGIL-SEC-002", "severity": "LOW", "what": "b"},
    ]})
    found = parse_findings(f"```json\n{tools}\n```\n\n```json\n{real}\n```")
    assert [f["id"] for f in found] == ["VIGIL-SEC-001", "VIGIL-SEC-002"]


# --- acceptable_extra boundary ------------------------------------------------------------

def test_acceptable_extra_matches_whole_words_only() -> None:
    """Substring matching let 'merge' exempt 'merged', 'merger' and anything containing it."""
    r = score(
        spec(must_detect=[], acceptable_extra=["merge"], max_false_positives=0),
        [finding("V-1", "HIGH", "app.py:4 submerged credentials in the logs", 0)],
    )
    assert r.false_positives, "'merge' must not exempt 'submerged'"
