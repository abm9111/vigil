# The gates, in one place, so a contributor and CI cannot diverge.
#
# `make check` is exactly what .github/workflows/self-audit.yml runs. That is the point:
# lessons/0010 records a gate verified locally that CI never saw, and the fix for a
# CI/local split is to have one definition of the gate rather than two that drift.
#
# Everything here is offline and needs no API key. The paid targets are named separately
# and are never invoked by `check`.

.DEFAULT_GOAL := check
.PHONY: check audit loadable ledger privacy test types lint eval baseline review learn clean help

## check: everything CI runs. Green here means green there.
check: audit loadable ledger privacy test types lint
	@echo "── all gates green"

## audit: 37 structural self-checks (<1s, no LLM, no network)
audit:
	python3 evals/check_repo.py

## loadable: the skill is still discoverable by Claude Code
loadable:
	python3 evals/check_loadable.py

## ledger: LEDGER.md matches the lessons it is generated from
ledger:
	python3 evals/build_ledger.py --check

## privacy: the gate clears a clean record, blocks a leaking one, and re-clears every bundle
#
# This ran in CI and not here, so a contributor could get `make check` green and have their
# contribution rejected by the gate on push — found by L34, not by anyone reading the file.
# Contributed bundles are public and permanent: "it was clean when it merged" is not the
# claim that matters, so they are re-checked on every run, not once.
privacy:
	python3 evals/privacy_gate.py evals/fixtures/records/clean.json
	@if python3 evals/privacy_gate.py evals/fixtures/records/leaking.json 2>/dev/null; then \
		echo "FAIL: privacy gate PASSED a record it must block"; exit 1; fi
	@echo "privacy gate correctly blocked the leaking record"
	@files=$$(ls corpus/*.json 2>/dev/null); \
		if [ -z "$$files" ]; then echo "no bundles yet"; \
		else python3 evals/privacy_gate.py --bundles $$files; fi

## test: every check must be able to FAIL
#
# Run with `claude` removed from PATH, because a hosted runner does not have it. Sharing the
# command with CI is not enough to share the verdict — the guards in run_eval.py probed the
# CLI before their own free filesystem check, which exits 2 here and raises FileNotFoundError
# there. Local green, CI red, three commits, one definition of the gate. Environment is part
# of the gate.
test:
	@PATH="$$(python3 -c 'import os,sys;print(os.path.dirname(sys.executable))'):/usr/bin:/bin" \
		pytest tests/ -q

types:
	mypy

# `ruff check .` — the same argument CI passes. Narrowing this to evals/*.py tests/*.py left
# scripts/ and examples/ linted in CI and not here, in the file whose header promises they
# cannot diverge.
lint:
	ruff check .

## ledger-rebuild: regenerate LEDGER.md after adding a lesson
ledger-rebuild:
	python3 evals/build_ledger.py

# ─── Targets that cost money. Never part of `check`, never run in CI. ───

## eval: score a saved transcript against a fixture (needs --fixture/--from-file)
eval:
	@echo "run: python3 evals/run_eval.py --from-file <out.txt> --fixture <name>"

## baseline: with/without-VIGIL comparison — TWO CLI arms per fixture, real spend
baseline:
	@echo 'Read docs/BASELINE.md first — every guard there exists because the obvious'
	@echo 'version produced a confident wrong number.'
	@echo ''
	@echo '  scripts/run-baseline.sh <outdir> 5'
	@echo ''
	@echo '--runs 5 is a FLOOR: the same arm has returned 0% and 83% on consecutive draws.'

## review: hand a clean clone to an outside model — the highest-yield check here
#
# Not part of `check`: it costs money and needs an engine CLI. Three rounds have found twelve
# defects that every check in this repo found none of.
review:
	@echo 'scripts/adversarial-review.sh --engine codex|grok|kimi'
	@echo 'Brief: evals/review-brief.md — edit it to sharpen a round, never to narrow one.'

## learn: aggregate local run records into learning signals
learn:
	python3 evals/learn.py --dir .vigil/runs

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache **/__pycache__

## help: list targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
