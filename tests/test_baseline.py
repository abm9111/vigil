#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""The with/without-VIGIL comparison, minus the parts that cost money.

The CLI arms cannot run here — they need an API key and real spend. What can be tested is the
part that decides what the numbers *mean*, and that is where a benchmark actually goes wrong:
a verdict rule that quietly counts "found more findings" as "got better".

    pytest tests/test_baseline.py -q
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))

from run_eval import (  # noqa: E402
    Result,
    control_prompt,
    implausible,
    median,
    report_delta,
)


def res(recall: float, fps: int) -> Result:
    return Result(recall=recall, false_positives=[f"fp{i}" for i in range(fps)])


# ------------------------------------------------------------------------- the verdict rule


def test_more_recall_with_no_extra_noise_is_an_improvement() -> None:
    assert report_delta("f", [res(0.4, 2)], [res(0.8, 2)]) is True


def test_more_recall_bought_with_more_false_positives_is_not_an_improvement() -> None:
    """The failure mode that makes a benchmark useless.

    A skill that raises recall by producing more findings overall has not improved anything —
    it has traded one number for another. `clean-control` exists for the same reason. If this
    ever returns True, VIGIL can look better by getting louder.
    """
    assert report_delta("f", [res(0.4, 1)], [res(0.9, 6)]) is False


def test_no_improvement_is_reported_not_hidden(capsys: pytest.CaptureFixture[str]) -> None:
    """A null result is the whole point of running this. It has to be legible."""
    assert report_delta("f", [res(0.8, 1)], [res(0.8, 1)]) is False
    assert "NO IMPROVEMENT" in capsys.readouterr().out


def test_worse_recall_is_not_an_improvement() -> None:
    assert report_delta("f", [res(0.9, 1)], [res(0.5, 0)]) is False


def test_same_recall_with_fewer_false_positives_is_called_out(
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_delta("f", [res(0.8, 5)], [res(0.8, 1)])
    assert "fewer false positives" in capsys.readouterr().out


def test_delta_reports_a_range_when_there_are_several_runs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One run is a sample of size one; thresholds have been enforced against unmeasured spread."""
    report_delta("f", [res(0.2, 1), res(0.6, 1), res(0.4, 1)], [res(0.8, 1)] * 3)
    out = capsys.readouterr().out
    assert "min 20%" in out and "max 60%" in out


def test_median_is_not_the_mean() -> None:
    """An outlier run must not drag the headline number."""
    assert median([0.1, 0.5, 0.6]) == 0.5
    assert median([0.0, 1.0]) == 0.5


# ---------------------------------------------------------------------------- control prompt


def test_control_prompt_is_read_from_its_own_file() -> None:
    p = control_prompt()
    assert "CRITICAL" in p and "JSON" in p
    assert "vigil" not in p.lower(), "the control must not mention the skill under test"


def test_control_prompt_still_hands_the_control_its_advantages() -> None:
    """Guards against the control being quietly weakened to inflate the delta.

    Each of these is something VIGIL provides that the control is deliberately given too, so
    the measurement is of the skill's structure rather than of prompt quality. Deleting one
    would raise VIGIL's apparent value without changing VIGIL.
    """
    p = control_prompt().lower()
    for advantage in ("severity", "line", "json", "security", "test"):
        assert advantage in p, f"control prompt no longer asks for {advantage!r}"
    assert "before forming an opinion" in p, "control no longer told to run tools first"


def test_control_prompt_fails_loudly_if_the_fence_goes_missing(tmp_path: Path) -> None:
    """A silently-empty control prompt would produce a huge, meaningless delta."""
    src = (REPO / "evals" / "baseline-prompt.md").read_text(encoding="utf-8")
    broken = tmp_path / "baseline-prompt.md"
    broken.write_text(src.replace("## The prompt", "## Something Else"), encoding="utf-8")
    code = (
        f"import sys, pathlib; sys.path.insert(0, {str(REPO / 'evals')!r}); import run_eval; "
        f"run_eval.BASELINE_PROMPT_FILE = pathlib.Path({str(broken)!r}); "
        "run_eval.control_prompt()"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=False)
    assert r.returncode == 2, "a missing control prompt did not fail closed"


# ------------------------------------------------------------------------------ CLI guards


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPO / "evals" / "run_eval.py"), *args],
        capture_output=True, text=True, check=False,
    )


def test_arm_requires_an_output_path() -> None:
    """--arm writes scores for later comparison; without --out the run is spent and lost."""
    r = run_cli("--arm", "control", "--fixture", "clean-control")
    assert r.returncode == 2 and "needs --out" in r.stderr


def test_compare_is_free_and_needs_no_cli(tmp_path: Path) -> None:
    """The comparison step must never invoke the model. A scoring bug should cost a re-run of
    arithmetic, not a re-measurement — the arms are the expensive part."""
    import json as _json
    a = tmp_path / "c.json"
    b = tmp_path / "v.json"
    a.write_text(_json.dumps({"f": [{"recall": 0.4, "false_positives": ["x"],
                                     "missed": [], "detected": []}]}))
    b.write_text(_json.dumps({"f": [{"recall": 0.8, "false_positives": [],
                                     "missed": [], "detected": []}]}))
    r = run_cli("--compare", str(a), str(b))
    assert r.returncode == 0
    assert "+40%" in r.stdout and "1/1" in r.stdout


def test_runs_must_be_positive() -> None:
    r = run_cli("--arm", "control", "--out", "/dev/null", "--runs", "0")
    assert r.returncode == 2


# ─────────────────────────────────────────── the check that would have caught the void run


def test_zero_recall_on_a_seeded_fixture_is_flagged_as_unmeasured() -> None:
    """The exact scenario that shipped a false headline.

    A treatment arm scored 0% recall because the skill was not installed while it ran, and the
    harness printed "VIGIL beat the control on 0/2 fixtures" as a finding about VIGIL.
    """
    spec = {"must_detect": [{"id": f"d{i}"} for i in range(6)]}
    assert implausible("f", spec, [Result(recall=0.0)]) is not None


def test_a_genuine_low_score_is_NOT_flagged() -> None:
    """The line that matters. Excluding a disappointing result would be the thumb on the scale
    this project refuses everywhere else — a null result is the most valuable output here."""
    spec = {"must_detect": [{"id": f"d{i}"} for i in range(6)]}
    assert implausible("f", spec, [Result(recall=0.17)]) is None


def test_partial_zero_is_not_flagged() -> None:
    """One zero run among several is variance, not a broken arm."""
    spec = {"must_detect": [{"id": "d"}]}
    assert implausible("f", spec, [Result(recall=0.0), Result(recall=0.8)]) is None


def test_clean_control_is_never_flagged() -> None:
    """A fixture seeding nothing SHOULD score 0 recall — that is its purpose, not a fault."""
    assert implausible("clean-control", {"must_detect": []}, [Result(recall=0.0)]) is None
