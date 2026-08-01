#!/usr/bin/env bash
# VIGIL — install as a Claude Code skill.
#
#   curl -fsSL https://raw.githubusercontent.com/abm9111/vigil/main/install.sh | bash
#
# Installs to ~/.claude/skills/vigil (override with VIGIL_DIR). Updates in place if already
# present. No sudo, no package manager, nothing outside the skills directory.
#
# It verifies the install rather than announcing it. A script that prints "success" without
# checking is the failure this repo exists to catch — see RULES.md Rule 3a: presence is not
# efficacy. If the skill did not become discoverable, this exits non-zero and says so.

set -euo pipefail

REPO_URL="${VIGIL_REPO:-https://github.com/abm9111/vigil.git}"
SKILL_DIR="${VIGIL_DIR:-$HOME/.claude/skills/vigil}"
BRANCH="${VIGIL_BRANCH:-main}"

if [ -t 1 ]; then R=$'\033[0;31m'; G=$'\033[0;32m'; Y=$'\033[1;33m'; D=$'\033[2m'; N=$'\033[0m'
else R=''; G=''; Y=''; D=''; N=''; fi

die() { printf '%serror:%s %s\n' "$R" "$N" "$1" >&2; exit 1; }
say() { printf '  %s\n' "$1"; }

# EVERYTHING below lives in main(), which is called on the very last line.
#
# This is served as `curl … | bash`, and bash executes a pipe as it arrives. A connection that
# drops mid-transfer would otherwise run whatever prefix arrived — and the prefix that matters
# contains `git reset --hard`. Today truncation happens to abort on a syntax error because the
# destructive commands sit inside an unterminated `if`, but that is luck, not design: reorder
# two blocks and it stops being true.
#
# With the wrapper, a truncated download defines a function and never calls it. Safety becomes
# structural rather than incidental — the same trade this repo makes everywhere else
# (unrepresentable over redacted, consent by construction over consent by policy).
main() {

  printf '\n  %sVIGIL%s — codebase quality and compliance audit for Claude Code\n\n' "$Y" "$N"

  command -v git >/dev/null 2>&1 || die "git is required but not installed."

  # Refuse to clobber something that is not us. A directory here may be another skill, or a
  # symlink into a working copy someone is developing in.
  if [ -e "$SKILL_DIR" ] && [ ! -d "$SKILL_DIR/.git" ]; then
    die "$SKILL_DIR exists and is not a git checkout. Move it aside, or set VIGIL_DIR."
  fi

  if [ -d "$SKILL_DIR/.git" ]; then
    origin="$(git -C "$SKILL_DIR" remote get-url origin 2>/dev/null || echo '')"
    # Exact allowlist, not a substring. `*vigil*` matched ANY remote containing the word —
    # and the next line does `reset --hard` against whatever that remote is, discarding
    # local state. A redirected or squatted remote would have won.
    case "$origin" in
      "$REPO_URL"|\
      https://github.com/abm9111/vigil.git|https://github.com/abm9111/vigil|\
      git@github.com:abm9111/vigil.git|ssh://git@github.com/abm9111/vigil.git)
        # NEVER reset --hard over someone's work. The clobber guard above protects a
        # non-VIGIL directory; this path is where a CONTRIBUTOR's own checkout lives, and
        # `reset --hard` would silently delete exactly the uncommitted work the guard's
        # comment claims to care about. Refuse and let them decide.
        if ! git -C "$SKILL_DIR" diff --quiet HEAD 2>/dev/null \
           || [ -n "$(git -C "$SKILL_DIR" ls-files --others --exclude-standard)" ]; then
          die "$SKILL_DIR has uncommitted changes. Refusing to update over them.
    Commit, stash or move them, then re-run. Nothing has been modified."
        fi
        say "updating existing install at ${D}${SKILL_DIR}${N}"
        git -C "$SKILL_DIR" fetch --quiet origin "$BRANCH"
        git -C "$SKILL_DIR" checkout --quiet "$BRANCH"
        git -C "$SKILL_DIR" merge --ff-only --quiet "origin/$BRANCH" \
          || die "$SKILL_DIR has diverged from origin/$BRANCH and cannot fast-forward.
    Your history is intact; resolve it with git, or move the directory aside." ;;
      *) die "$SKILL_DIR tracks ${origin:-an unknown remote}, which is not VIGIL.
    Refusing to reset --hard against it. Move it aside, or set VIGIL_DIR." ;;
    esac
  else
    say "cloning into ${D}${SKILL_DIR}${N}"
    mkdir -p "$(dirname "$SKILL_DIR")"
    git clone --quiet --branch "$BRANCH" -- "$REPO_URL" "$SKILL_DIR"
  fi

  # ── Verify, do not assert ────────────────────────────────────────────────────────────────
  #
  # Honest about what this proves: it runs the tree's OWN checks, so it confirms the download
  # is complete and internally consistent — not that it is authentic. A compromised source
  # could make these pass. That is inherent to `curl | bash`; the mitigation is reading the
  # script and the repo first, which the README recommends for exactly this reason.
  if command -v python3 >/dev/null 2>&1; then
    python3 "$SKILL_DIR/evals/check_loadable.py" >/dev/null 2>&1 \
      || die "installed, but the skill is not discoverable — please open an issue with this output:
      $(python3 "$SKILL_DIR/evals/check_loadable.py" 2>&1 | head -5)"
    say "${G}✓${N} discoverable as a Claude Code skill (per the tree's own checks)"

    if python3 "$SKILL_DIR/evals/check_repo.py" >/dev/null 2>&1; then
      say "${G}✓${N} self-audit clean"
    else
      say "${Y}!${N} self-audit reported findings — the skill works; run it to see them:"
      say "  ${D}python3 $SKILL_DIR/evals/check_repo.py${N}"
    fi
  else
    say "${Y}!${N} python3 not found — skipping verification. The skill itself needs no Python;"
    say "  only its self-checks do."
  fi

  version="$(git -C "$SKILL_DIR" describe --tags --always 2>/dev/null || echo 'unknown')"
  printf '\n  installed %s\n\n' "${D}${version}${N}"
  say "Try it:      ${Y}/vigil scan${N}      quick pass, ~30s"
  say "             ${Y}/vigil audit${N}     full audit with correlation"
  say "Uninstall:   ${D}rm -rf $SKILL_DIR${N}"
  printf '\n'
}

main "$@"
