#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""The guards that decide whether a baseline measurement means anything.

Three of these were broken in sequence, each discovered by the next attempt rather than by a
test, and every one produced a *plausible number from an invalid measurement*:

  1. isolation via CLAUDE_CONFIG_DIR also severed credentials — the control arm was never
     logged in, so it could not run at all
  2. the skill was stashed INSIDE the skills tree, where it stayed discoverable under its new
     name. Caught only because that name happened to contain "vigil"; called `.baseline-stash`
     it would have sailed through and silently made the control a second treatment arm
  3. both filesystem guards used `Path.rglob`, which does not follow symlinks — and a skill
     under development is almost always a symlink. The guard was blind in the commonest
     install shape

The third one mattered most in combination: with the control-arm guard blind, a wrapper bug
ran BOTH arms without the skill, the treatment arm scored 0% recall, and the harness reported
"VIGIL beat the control on 0/2 fixtures" as a finding. That is `lessons/0002` — a contaminated
measurement that looks like a result — rebuilt from scratch.

These tests are free: they exercise the filesystem half of each guard against a temporary
skills tree via CLAUDE_CONFIG_DIR. No CLI calls, no tokens.

    pytest tests/test_baseline_guards.py -q
"""
from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))

import run_eval  # noqa: E402

SKILL = "---\nname: vigil\ndescription: x\n---\n\n# body\n"


@pytest.fixture
def skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    root = tmp_path / "cfg" / "skills"
    root.mkdir(parents=True)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "cfg"))
    yield root


def install(root: Path, name: str, *, symlink: bool = False, nested: str | None = None) -> Path:
    real = root.parent / f"real-{name}"
    real.mkdir(parents=True, exist_ok=True)
    (real / "SKILL.md").write_text(SKILL, encoding="utf-8")
    target = root / nested / name if nested else root / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if symlink:
        target.symlink_to(real, target_is_directory=True)
    else:
        target.mkdir()
        (target / "SKILL.md").write_text(SKILL, encoding="utf-8")
    return target


# ─────────────────────────────────────────────────────────── _vigil_installed


def test_finds_a_plain_directory_install(skills: Path) -> None:
    install(skills, "vigil")
    assert run_eval._vigil_installed() is not None


def test_finds_a_SYMLINKED_install(skills: Path) -> None:
    """The shape that broke it. `rglob` will not descend into a symlinked directory, and a
    skill under development is a symlink into the working copy."""
    install(skills, "vigil", symlink=True)
    assert run_eval._vigil_installed() is not None, (
        "a symlinked skill was invisible to the guard — this is how VIGIL is installed"
    )


def test_finds_it_under_ANY_directory_name(skills: Path) -> None:
    """Claude Code lists a skill by directory name, so stashing it as `.baseline-stash` leaves
    it fully discoverable while defeating any name-based check. The guard must key on the
    declared `name:`, not on the path."""
    install(skills, ".baseline-stash")
    assert run_eval._vigil_installed() is not None, (
        "a renamed copy evaded the guard — the exact contamination that occurred"
    )


def test_finds_a_nested_install(skills: Path) -> None:
    install(skills, "vigil", nested="some-plugin")
    assert run_eval._vigil_installed() is not None


def test_returns_none_when_genuinely_absent(skills: Path) -> None:
    install(skills, "something-else")
    (skills / "something-else" / "SKILL.md").write_text(
        "---\nname: something-else\ndescription: x\n---\n", encoding="utf-8")
    assert run_eval._vigil_installed() is None


def test_returns_none_on_an_empty_tree(skills: Path) -> None:
    assert run_eval._vigil_installed() is None


def test_missing_skills_dir_is_not_a_crash(tmp_path: Path,
                                           monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "nope"))
    assert run_eval._vigil_installed() is None


# ─────────────────────────────────────────────────── the guards refuse, before spending


def test_control_guard_refuses_when_the_skill_is_present(skills: Path) -> None:
    """Must exit BEFORE the model probe — a guard that spends a token to discover it should
    not have run is a guard that people disable."""
    install(skills, "vigil", symlink=True)
    with pytest.raises(SystemExit) as e:
        run_eval.assert_skill_invisible(None)
    assert e.value.code == 2


def test_control_guard_refuses_a_renamed_copy(skills: Path) -> None:
    install(skills, ".baseline-stash")
    with pytest.raises(SystemExit):
        run_eval.assert_skill_invisible(None)


def test_treatment_guard_refuses_when_the_skill_is_absent(skills: Path) -> None:
    """The guard that did not exist. Its absence let a treatment arm run with no skill, score
    0% recall, and be reported as 'VIGIL beat the control on 0/2 fixtures'."""
    with pytest.raises(SystemExit) as e:
        run_eval.assert_skill_visible(None)
    assert e.value.code == 2


def test_the_two_guards_are_mutually_exclusive(skills: Path) -> None:
    """Whatever the state, exactly one of them must object. If both pass, the harness has no
    idea which arm it is running."""
    install(skills, "vigil", symlink=True)
    present_ok = _passes(run_eval.assert_skill_invisible)
    install_absent = skills / "vigil"
    install_absent.unlink()
    absent_ok = _passes(run_eval.assert_skill_visible)
    assert not present_ok and not absent_ok


def _passes(fn: object) -> bool:
    try:
        fn(None)  # type: ignore[operator]
    except SystemExit:
        return False
    except Exception:
        return False
    return True


def test_env_override_is_honoured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CLAUDE_CONFIG_DIR must steer the scan, or a test suite silently checks the developer's
    real skills directory and passes for the wrong reason."""
    cfg = tmp_path / "elsewhere"
    (cfg / "skills" / "vigil").mkdir(parents=True)
    (cfg / "skills" / "vigil" / "SKILL.md").write_text(SKILL, encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(cfg))
    found = run_eval._vigil_installed()
    assert found is not None and str(cfg) in str(found)
