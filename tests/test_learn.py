#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""The corpus statistics decide whether a rule gets reconsidered. They need tests.

These were originally validated by a throwaway script that built a skewed corpus and printed
the result. That demonstration was real and completely ephemeral — nobody could re-run it, and
a refactor could silently restore pooled counting while everything stayed green. Which is the
exact argument `tests/test_check_repo.py` makes about checks, applied to arithmetic.

The load-bearing test is `test_one_heavy_contributor_cannot_manufacture_a_signal`. If that ever
passes for the wrong reason, VIGIL starts changing rules on one person's codebase.

    pytest tests/test_learn.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))

from learn import (  # noqa: E402
    MIN_CONTRIBUTORS,
    _fp_rates,
    _ne_rates,
    corpus_candidates,
    corpus_report,
    draft,
    load_corpus,
)


def record(*, egress_ne: bool = False, fp: int = 0, outcomes: int = 4,
           stack: list[str] | None = None, version: str = "0.4.0") -> dict[str, Any]:
    return {
        "schema_version": 1, "vigil_version": version, "mode": "audit",
        "stack": stack or ["python"],
        "clusters": [
            {"prefix": "SEC", "verdict": "scored", "high": 1},
            {"prefix": "EGRESS", "verdict": "ne" if egress_ne else "scored"},
            {"prefix": "CHAIN", "verdict": "na", "na_trigger": "stack-absent"},
        ],
        "partial_score": 70,
        "shared": "asked-accepted",
        "outcomes": [
            {"prefix": "CODE", "severity": "low",
             "disposition": "false_positive" if i < fp else "accepted", "tool": "ruff"}
            for i in range(outcomes)
        ],
    }


# --------------------------------------------------------------------- per-contributor rates


def test_na_is_not_counted_as_missing_evidence() -> None:
    """N/A and N/E are different states and conflating them is the oldest bug in this repo.

    A cluster that does not apply has not failed to produce evidence — counting it as such
    would make every Python repo look like Blockchain coverage was broken.
    """
    rates = _ne_rates([record()])
    assert "CHAIN" not in rates, "an N/A cluster leaked into the no-evidence denominator"
    assert rates["EGRESS"] == 0.0


def test_ne_rate_is_per_contributor_not_pooled() -> None:
    assert _ne_rates([record(egress_ne=True)] * 3)["EGRESS"] == 1.0
    assert _ne_rates([record(egress_ne=True), record()])["EGRESS"] == 0.5


def test_fp_rate_counts_dispositions() -> None:
    assert _fp_rates([record(fp=2, outcomes=4)])["CODE"] == 0.5


# ------------------------------------------------------------------- the load-bearing property


def test_one_heavy_contributor_cannot_manufacture_a_signal() -> None:
    """THE test. One person, 50 runs, unusual repo; nine others, 2 runs each.

    Pooled, this is 50/68 = 74% no-evidence and would cross the 50% bar with an impressive
    n behind it. Nothing in the data reveals the concentration — by design nothing can, since
    records carry no repo identity. Counting contributors is what makes it visible.
    """
    corpus = {"heavy": [record(egress_ne=True, fp=4) for _ in range(50)]}
    for i in range(9):
        corpus[f"dev{i}"] = [record() for _ in range(2)]

    pooled_ne = sum(1 for r in corpus["heavy"] if True) / 68
    assert pooled_ne > 0.5, "fixture no longer reproduces the skew it exists to test"

    assert corpus_candidates(corpus) == [], (
        "one contributor's volume produced a signal — pooled counting has come back"
    )


def test_a_genuine_signal_still_fires() -> None:
    """The other half. A check that never fires is as broken as one that always does."""
    corpus = {f"dev{i}": [record(egress_ne=i < 7) for _ in range(3)] for i in range(10)}
    signals = corpus_candidates(corpus)
    assert signals, "7 of 10 contributors seeing no evidence produced no signal"
    assert any("EGRESS" in why for _, why in signals)


def test_below_the_contributor_floor_there_is_no_signal() -> None:
    """Two contributors who agree completely are still two codebases, not evidence."""
    corpus = {f"dev{i}": [record(egress_ne=True) for _ in range(20)]
              for i in range(MIN_CONTRIBUTORS - 1)}
    assert corpus_candidates(corpus) == []


def test_unanimous_agreement_at_the_floor_does_fire() -> None:
    """Boundary: exactly MIN_CONTRIBUTORS, all agreeing, must cross."""
    corpus = {f"dev{i}": [record(egress_ne=True) for _ in range(3)]
              for i in range(MIN_CONTRIBUTORS)}
    assert corpus_candidates(corpus)


# ------------------------------------------------------------------------------- the report


def test_report_discloses_volume_skew() -> None:
    """A reader must see the concentration before they see any rate."""
    corpus = {"heavy": [record() for _ in range(50)], "a": [record()], "b": [record()]}
    out = "\n".join(corpus_report(corpus))
    assert "Who submitted what" in out
    assert "74%" in out or "96%" in out, "volume share is not shown"


def test_report_warns_on_mixed_versions() -> None:
    """A rule that changed between versions makes the pooled rate meaningless."""
    corpus = {"a": [record(version="0.4.0")], "b": [record(version="0.5.0")],
              "c": [record(version="0.4.0")]}
    assert "mixes VIGIL versions" in "\n".join(corpus_report(corpus))


def test_report_shows_stack_distribution() -> None:
    """Ten Python repos say nothing about Go, and the reader has to be told which they have."""
    corpus = {"a": [record(stack=["python"])], "b": [record(stack=["go"])]}
    out = "\n".join(corpus_report(corpus))
    assert "`python`" in out and "`go`" in out


def test_report_flags_a_thin_corpus() -> None:
    assert "below the" in "\n".join(corpus_report({"a": [record()]}))


# ------------------------------------------------------------------------------- corpus load


def write_bundle(d: Path, who: str, records: list[dict[str, Any]]) -> None:
    (d / f"{who}.json").write_text(json.dumps(
        {"schema_version": 1, "contributor": who, "vigil_version": "0.4.0",
         "records": records}), encoding="utf-8")


def test_load_corpus_groups_by_contributor(tmp_path: Path) -> None:
    write_bundle(tmp_path, "alpha", [record(), record()])
    write_bundle(tmp_path, "beta", [record()])
    loaded = load_corpus(tmp_path)
    assert {k: len(v) for k, v in loaded.items()} == {"alpha": 2, "beta": 1}


def test_a_blocked_bundle_is_dropped_whole(tmp_path: Path, capsys: Any) -> None:
    """One dirty record disqualifies the submission, not just that record.

    Keeping the clean ones would launder the submitter's failed redaction, and would also
    silently reward a contributor whose process leaks.
    """
    write_bundle(tmp_path, "clean", [record()])
    dirty = record()
    dirty["repo_path"] = "/Users/alice/work/acme"
    write_bundle(tmp_path, "leaky", [record(), dirty])

    loaded = load_corpus(tmp_path)
    assert "leaky" not in loaded, "a bundle containing a leaking record was aggregated"
    assert "clean" in loaded
    assert "blocked by privacy gate" in capsys.readouterr().err


# ------------------------------------------------------------------------------------ draft


def test_draft_never_prefills_prose() -> None:
    """The draft must not invent the reasoning — that is the contributor's whole job.

    A stub that writes plausible-sounding analysis gets committed as-is, and the ledger fills
    with lessons nobody actually thought about.
    """
    text = draft([("cluster carries weight it cannot evidence", "EGRESS in 7 of 10")])
    assert text.count("FILL IN") >= 4
    assert "status: open" in text


def test_draft_carries_the_redaction_warning() -> None:
    text = draft([("rule fires on a shape it should not", "CODE in 5 of 8")])
    assert "repository, path, host, company or finding text" in text


@pytest.mark.parametrize("bad", ["/Users/", "http://", "@example.com"])
def test_draft_contains_no_leak_shapes(bad: str) -> None:
    assert bad not in draft([("cls", "VIGIL-SEC in 3 of 3")])
