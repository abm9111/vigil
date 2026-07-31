#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""Verify VIGIL is actually loadable as a Claude Code skill.

Every other check in this repo tests the *harness*. None tested the product. VIGIL could
have shipped with 21 green checks, 40 passing tests, and frontmatter Claude Code refuses to
parse — and nothing would have noticed. Verification pointed slightly away from the thing
that matters, which is the same shape as the defects `lessons/` records.

Two modes, deliberately:

  (default)  structural — free, offline, no CLI. Asserts everything Claude Code needs to
             discover and route the skill. Runs in CI on every push.
  --live     integration — installs into a throwaway skills dir and invokes `claude` to
             confirm it actually resolves. Costs API usage, needs the CLI, so it is opt-in
             and never runs in CI. Same split as run_eval.py's --from-file.

Run:  python3 evals/check_loadable.py [--live]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"

# Claude Code discovers a skill from YAML frontmatter at the very top of SKILL.md.
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
FIELD = re.compile(r"^([a-z_]+):\s*(.*)$", re.M)

# The name is used as an identifier: lowercase, digits and hyphens.
NAME_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


def fail(msgs: list[str], msg: str) -> None:
    msgs.append(msg)


def check_structural() -> list[str]:
    """Everything required for discovery, checked without loading anything."""
    problems: list[str] = []

    if not SKILL.exists():
        return ["SKILL.md is missing — Claude Code has nothing to discover"]

    raw = SKILL.read_text(encoding="utf-8")

    if not raw.startswith("---"):
        return ["SKILL.md does not open with a `---` frontmatter fence; "
                "content before it makes the skill undiscoverable"]

    m = FRONTMATTER.match(raw)
    if not m:
        return ["SKILL.md frontmatter is not closed by a second `---` on its own line"]

    fields = dict(FIELD.findall(m.group(1)))

    name = fields.get("name", "").strip().strip('"').strip("'")
    if not name:
        fail(problems, "frontmatter has no `name`")
    elif not NAME_RE.match(name):
        fail(problems, f"`name` {name!r} is not a valid identifier "
                       "(lowercase letters, digits, hyphens; must start with a letter)")
    elif name != ROOT.name and ROOT.name not in ("vigil",):
        # A mismatch is legal but confusing: the directory is what a user types after
        # cloning, the name is what routes.
        fail(problems, f"`name` is {name!r} but the directory is {ROOT.name!r}")

    desc = fields.get("description", "").strip().strip('"').strip("'")
    if not desc:
        fail(problems, "frontmatter has no `description` — this is the text the model "
                       "matches against to decide whether to load the skill, so an empty "
                       "one means it never triggers")
    elif len(desc) < 40:
        fail(problems, f"`description` is {len(desc)} chars; too terse to route reliably")
    elif len(desc) > 1024:
        fail(problems, f"`description` is {len(desc)} chars; overlong descriptions cost "
                       "context on every session that lists skills")

    # The body has to survive being read as markdown.
    body = raw[m.end():]
    if not body.strip():
        fail(problems, "SKILL.md has frontmatter but no body")
    if body.count("```") % 2:
        fail(problems, "SKILL.md has an odd number of ``` fences — an unclosed code block "
                       "swallows the rest of the file")

    return problems


def check_live(claude_bin: str) -> list[str]:
    """Install into a throwaway skills dir and confirm `claude` resolves the skill.

    Uses CLAUDE_CONFIG_DIR so nothing touches the caller's real configuration.
    """
    problems: list[str] = []
    if not shutil.which(claude_bin):
        return [f"`{claude_bin}` is not on PATH — cannot run the live check"]

    with tempfile.TemporaryDirectory() as tmp:
        cfg = Path(tmp) / "config"
        (cfg / "skills").mkdir(parents=True)
        shutil.copytree(
            ROOT, cfg / "skills" / "vigil",
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*_cache", "export"),
        )
        env = {**os.environ, "CLAUDE_CONFIG_DIR": str(cfg)}
        try:
            r = subprocess.run(
                [claude_bin, "-p", "List the names of every skill available to you. "
                                   "Output names only, one per line, nothing else."],
                capture_output=True, text=True, timeout=300, check=False, env=env,
            )
        except subprocess.TimeoutExpired:
            return ["live check timed out after 300s"]

        if r.returncode != 0:
            return [f"`claude` exited {r.returncode}: {(r.stderr or r.stdout)[-400:]}"]
        if "vigil" not in r.stdout.lower():
            problems.append(
                "the skill did not appear in the model's own list of available skills.\n"
                f"        output was: {r.stdout.strip()[:300]!r}"
            )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="also invoke the Claude CLI (costs API usage, not run in CI)")
    ap.add_argument("--claude-bin", default="claude")
    args = ap.parse_args()

    problems = check_structural()
    mode = "structural"

    if args.live and not problems:
        problems += check_live(args.claude_bin)
        mode = "structural + live"
    elif args.live:
        print("skipping live check — fix the structural problems first", file=sys.stderr)

    if problems:
        print(f"VIGIL loadability ({mode}): {len(problems)} problem(s)\n", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    print(f"VIGIL loadability ({mode}): OK — discoverable as a Claude Code skill")
    return 0


if __name__ == "__main__":
    sys.exit(main())
