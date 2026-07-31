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

from run_eval import Result, control_prompt, median, report_delta  # noqa: E402


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


def test_baseline_refuses_a_saved_transcript() -> None:
    """--from-file scores one arm; a comparison needs two, and silently scoring the same
    transcript twice would print a delta of exactly zero."""
    r = run_cli("--baseline", "--from-file", "x.txt", "--fixture", "clean-control")
    assert r.returncode == 2 and "cannot score a saved transcript" in r.stderr


def test_runs_must_be_positive() -> None:
    r = run_cli("--baseline", "--runs", "0")
    assert r.returncode == 2
