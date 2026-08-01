#!/usr/bin/env bash
# adversarial-review.sh — hand this repo to an outside model and collect what it finds.
#
# Three rounds of this have found twelve defects that 36 checks and 176 tests found none of.
# It is the highest-yield verification available here, so it should be repeatable by anyone,
# not a thing that happened once in somebody's terminal.
#
#   scripts/adversarial-review.sh                      # default engine, verdict to ./
#   scripts/adversarial-review.sh --engine grok        # grok | kimi | codex
#   scripts/adversarial-review.sh --out /tmp/v.md --ref HEAD
#
# ENGINE ROTATION IS THE POINT. Overlap between different model families has been near zero;
# overlap between two runs of the same family is unmeasured and probably high. Rotating buys
# more than re-running.
#
# Requires: the chosen engine's CLI, authenticated. Nothing else. Never writes to this repo —
# the reviewer works on a throwaway clone, read-only.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BRIEF="$REPO/evals/review-brief.md"
ENGINE="${VIGIL_REVIEW_ENGINE:-codex}"
REF="HEAD"
OUT=""

while [ $# -gt 0 ]; do
  case "$1" in
    --engine) ENGINE="${2:?--engine needs a value}"; shift 2 ;;
    --out)    OUT="${2:?--out needs a value}";       shift 2 ;;
    --ref)    REF="${2:?--ref needs a value}";       shift 2 ;;
    -h|--help) sed -n '2,20p' "$0" | sed -E 's|^# ?||'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

[ -f "$BRIEF" ] || { echo "missing $BRIEF — the brief is not optional" >&2; exit 69; }

# Validate the engine BEFORE cloning: a typo should not cost a clone, and an unattended run
# should fail on the argument rather than three minutes later.
case "$ENGINE" in
  codex) command -v codex >/dev/null || { echo "codex not on PATH" >&2; exit 69; } ;;
  grok|kimi) command -v "$ENGINE-review" >/dev/null || {
      echo "$ENGINE-review not on PATH — see the sandbox repo's README" >&2; exit 69; } ;;
  *) echo "unknown engine '$ENGINE' (codex|grok|kimi)" >&2; exit 64 ;;
esac

# Unattended runs need a ceiling. A CLI handed an unavailable model retries rather than
# failing — the first test of this script sat in a retry loop against a model the account
# could not use, producing nothing and never returning. `timeout` turns that into exit 124.
LIMIT="${VIGIL_REVIEW_TIMEOUT:-1800}"
if command -v timeout >/dev/null; then RUN=(timeout "$LIMIT")
elif command -v gtimeout >/dev/null; then RUN=(gtimeout "$LIMIT")
else RUN=(); echo "note: no timeout(1) — install coreutils before scheduling this" >&2; fi

SHA="$(git -C "$REPO" rev-parse --short "$REF" 2>/dev/null)" || {
  echo "not a git ref: $REF" >&2; exit 64; }
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${OUT:-$REPO/review-$ENGINE-$STAMP.md}"

# A throwaway clone, so a reviewer that ignores "read only" cannot touch the working tree.
WORK="$(mktemp -d "${TMPDIR:-/tmp}/vigil-review-XXXXXX")"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT INT TERM HUP

git clone --quiet --no-hardlinks "$REPO" "$WORK/repo" || { echo "clone failed" >&2; exit 70; }
git -C "$WORK/repo" checkout --quiet "$SHA" || { echo "checkout $SHA failed" >&2; exit 70; }

echo "── adversarial review"
echo "   engine : $ENGINE"
echo "   subject: $SHA (clean clone — see RULES.md Rule 10a, a report names its tree)"
echo "   verdict: $OUT"
echo

# stdin from /dev/null: a CLI that thinks stdin is piped waits for input forever, and the
# symptom is a job that never returns rather than one that fails.
case "$ENGINE" in
  codex)
    "${RUN[@]}" codex exec -s read-only -m "${VIGIL_REVIEW_MODEL:-gpt-5.5}" \
      -c model_reasoning_effort=high -C "$WORK/repo" --skip-git-repo-check \
      "$(cat "$BRIEF")" </dev/null >"$OUT" 2>"$WORK/err.log"
    ;;
  grok|kimi)
    "${RUN[@]}" "$ENGINE-review" "$WORK/repo" "$BRIEF" "$OUT" </dev/null 2>"$WORK/err.log"
    ;;
esac
rc=$?
[ $rc -eq 124 ] && { echo "engine exceeded ${LIMIT}s and was killed — no verdict" >&2; exit 2; }

# ── Implausibility guards ────────────────────────────────────────────────────────────
#
# Every one of these is a failure that already happened, and each produced a file that looked
# like a clean review. An empty verdict is a TOOLING RESULT, never a finding — the first run
# of this exited 0 with a zero-length verdict because the default model was not available on
# the account, and "no findings" was one careless step from being reported as good news.
if [ $rc -ne 0 ]; then
  echo "engine exited $rc — verdict not trustworthy" >&2
  sed -n '$p' "$WORK/err.log" >&2
  exit 2
fi
if grep -qiE '"type": *"(error|invalid_request_error)"|is not supported when using' "$WORK/err.log" 2>/dev/null; then
  echo "engine reported an API error — the model may be unavailable on this account:" >&2
  grep -iE 'error' "$WORK/err.log" | tail -2 >&2
  exit 2
fi
words=$(wc -w <"$OUT" | tr -d ' ')
if [ "$words" -lt 80 ]; then
  echo "verdict is $words words — that is a broken run, not a clean repository." >&2
  echo "  stderr tail:" >&2; tail -3 "$WORK/err.log" >&2
  exit 2
fi

echo "── verdict written: $OUT ($words words)"
echo "   Findings are PROPOSALS. Nothing here is applied without a human reading it —"
echo "   see CODEOWNERS: the maintainer read is the control L19 cannot be."
