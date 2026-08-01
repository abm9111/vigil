#!/usr/bin/env bash
# Two passes. Isolation wraps ONLY the control pass.
#
# The previous version moved the skill aside and ran both arms inside that window, so the
# treatment arm also ran without VIGIL and scored 0% recall — which the harness reported as
# "VIGIL beat the control on 0/2". Each arm now runs in its own process with its own verified
# precondition, and the comparison is a separate, free step.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LINK="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills/vigil"
STASH="${TMPDIR:-/tmp}/vigil-stash-$$"      # OUTSIDE the skills tree — inside it stays discoverable
OUT="${1:?usage: run-baseline.sh <outdir> [runs]}"
RUNS="${2:-1}"
mkdir -p "$OUT"

restore() { [ -e "$STASH" ] && [ ! -e "$LINK" ] && mv "$STASH" "$LINK" && echo "  [restored]"; }
trap restore EXIT INT TERM HUP

[ -L "$LINK" ] || { echo "expected $LINK to be a symlink"; exit 2; }

echo "── pass 1/2: CONTROL (skill removed) ───────────────────────"
mv "$LINK" "$STASH"
( cd "$REPO" && python3 evals/run_eval.py --arm control --runs "$RUNS" --out "$OUT/control.json" )
c=$?
restore
[ $c -ne 0 ] && { echo "control arm failed ($c) — not proceeding"; exit $c; }

echo "── pass 2/2: TREATMENT (skill restored) ────────────────────"
( cd "$REPO" && python3 evals/run_eval.py --arm vigil --runs "$RUNS" --out "$OUT/vigil.json" )
v=$?
[ $v -ne 0 ] && { echo "treatment arm failed ($v)"; exit $v; }

echo "── comparison (free, no CLI calls) ─────────────────────────"
( cd "$REPO" && python3 evals/run_eval.py --compare "$OUT/control.json" "$OUT/vigil.json" )
