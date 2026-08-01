# The gates, in one place, so a contributor and CI cannot diverge.
#
# `make check` is exactly what .github/workflows/self-audit.yml runs. That is the point:
# lessons/0010 records a gate verified locally that CI never saw, and the fix for a
# CI/local split is to have one definition of the gate rather than two that drift.
#
# Everything here is offline and needs no API key. The paid targets are named separately
# and are never invoked by `check`.

.DEFAULT_GOAL := check
.PHONY: check audit loadable ledger test types lint eval baseline learn clean help

## check: everything CI runs. Green here means green there.
check: audit loadable ledger test types lint
	@echo "── all gates green"

## audit: 33 structural self-checks (<1s, no LLM, no network)
audit:
	python3 evals/check_repo.py

## loadable: the skill is still discoverable by Claude Code
loadable:
	python3 evals/check_loadable.py

## ledger: LEDGER.md matches the lessons it is generated from
ledger:
	python3 evals/build_ledger.py --check

## test: every check must be able to FAIL
test:
	pytest tests/ -q

types:
	mypy

lint:
	ruff check evals/*.py tests/*.py

## ledger-rebuild: regenerate LEDGER.md after adding a lesson
ledger-rebuild:
	python3 evals/build_ledger.py

# ─── Targets that cost money. Never part of `check`, never run in CI. ───

## eval: score a saved transcript against a fixture (needs --fixture/--from-file)
eval:
	@echo "run: python3 evals/run_eval.py --from-file <out.txt> --fixture <name>"

## baseline: with/without-VIGIL comparison — TWO CLI arms per fixture, real spend
baseline:
	python3 evals/run_eval.py --baseline --runs 3

## learn: aggregate local run records into learning signals
learn:
	python3 evals/learn.py --dir .vigil/runs

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache **/__pycache__

## help: list targets
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## /  /'
