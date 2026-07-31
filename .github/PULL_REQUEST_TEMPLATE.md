## What and why

<!-- If this is a lesson, link the issue. If it changes a rule, state the evidence. -->

## Checklist

- [ ] `python3 evals/check_repo.py` passes
- [ ] `pytest tests/ -q` passes
- [ ] `mypy && ruff check .` pass
- [ ] If a check was added: a test proves it **fails** when its invariant is broken
- [ ] If a lesson was added: `python3 evals/build_ledger.py` re-run, and it contains
      nothing identifying a real system
- [ ] No eval threshold was lowered to make a run pass
