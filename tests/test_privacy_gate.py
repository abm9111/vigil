#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""The privacy gate is the only thing standing between a real user's repo and this project.

`lessons/0001` is about a checker that reported clean over real gaps. A privacy gate has the
same failure mode and a worse blast radius: if it passes what it cannot understand, the first
time anyone finds out is when someone's architecture is in a public git history.

So every test here asserts the gate says **no**. The one test that asserts a pass exists only
so the others are meaningful.

    pytest tests/test_privacy_gate.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "evals"))

from privacy_gate import GateError, check_bundle, scan_leaks, validate  # noqa: E402


@pytest.fixture
def schema() -> dict[str, Any]:
    return json.loads((REPO / "schemas" / "run-record.schema.json").read_text(encoding="utf-8"))


def clean_record() -> dict[str, Any]:
    """Modelled on the FIRST REAL run record, not on what I imagined one would look like."""
    return {
        "schema_version": 1,
        "vigil_version": "0.4.0",
        "mode": "audit",
        "timestamp_bucket": "2026-Q3",
        "stack": ["python", "fastapi", "docker"],
        "repo_size_bucket": "medium",
        "duration_bucket": "10-30min",
        "tools": {"available": ["git", "ruff", "gitleaks"], "missing": ["eslint", "tsc"]},
        "clusters": [
            {"prefix": "SEC", "verdict": "scored", "ceiling": 100, "critical": 0, "high": 1},
            {"prefix": "DATA", "verdict": "scored", "ceiling": 85, "info": 1},
            {"prefix": "FE", "verdict": "ne", "ceiling": None},
            {"prefix": "CHAIN", "verdict": "na", "na_trigger": "no-contract-files"},
        ],
        "correlations": [
            {"pattern": "TRUST_LAUNDERING", "severity": "high", "primary": "EGRESS",
             "constituents": 2},
        ],
        "verdict": "incomplete",
        "partial_score": 71,
        "capped_to": 59,
        "cap_reason": "critical",
        "transmitted": False,
        "shared": "asked-accepted",
        "tree_state": "clean",
        "outcomes": [
            {"prefix": "SEC", "severity": "high", "disposition": "accepted", "tool": "gitleaks"},
        ],
    }


def check(record: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    return validate(record, schema, schema, "rec")


def test_a_clean_record_passes(schema: dict[str, Any]) -> None:
    """Without this the suite could pass by rejecting everything."""
    assert check(clean_record(), schema) == []


def test_unknown_field_is_rejected(schema: dict[str, Any]) -> None:
    """The main event. Content arrives as a field nobody declared."""
    rec = clean_record()
    rec["repo_path"] = "/Users/alice/work/acme"
    errs = check(rec, schema)
    assert any("repo_path" in e for e in errs), errs


def test_free_text_in_an_enum_field_is_rejected(schema: dict[str, Any]) -> None:
    """The second way content arrives: a legal field carrying an illegal value."""
    rec = clean_record()
    rec["mode"] = "audit of acme-billing internal API"
    assert any("not one of the permitted values" in e for e in check(rec, schema))


def test_nested_unknown_field_is_rejected(schema: dict[str, Any]) -> None:
    """Closure has to hold at depth, not just at the top level."""
    rec = clean_record()
    rec["clusters"][0]["evidence"] = "SQL injection in src/billing/charge.py:88"
    assert any("evidence" in e for e in check(rec, schema))


def test_unknown_cluster_prefix_is_rejected(schema: dict[str, Any]) -> None:
    rec = clean_record()
    rec["clusters"][0]["prefix"] = "ACME-INTERNAL"
    assert check(rec, schema)


def test_out_of_range_score_is_rejected(schema: dict[str, Any]) -> None:
    rec = clean_record()
    rec["partial_score"] = 420
    assert any("maximum" in e for e in check(rec, schema))


def test_boolean_is_not_accepted_as_an_integer(schema: dict[str, Any]) -> None:
    """bool subclasses int in Python — a validator that forgets this accepts True as a score."""
    rec = clean_record()
    rec["partial_score"] = True
    assert any("boolean" in e for e in check(rec, schema))


def test_missing_required_field_is_rejected(schema: dict[str, Any]) -> None:
    rec = clean_record()
    del rec["mode"]
    assert any("mode" in e for e in check(rec, schema))


def test_unknown_schema_keyword_fails_closed() -> None:
    """A schema asserting something the gate does not implement must not report a pass.

    This is the `lessons/0001` shape: silence from a checker that did not actually look.
    """
    bad = {"type": "object", "additionalProperties": False,
           "properties": {"x": {"type": "string", "enum": ["a"], "oneOf": [{}]}}}
    with pytest.raises(GateError, match="does not implement"):
        validate({"x": "a"}, bad, bad, "rec")


def test_unresolvable_ref_fails_closed() -> None:
    bad = {"type": "object", "additionalProperties": False,
           "properties": {"x": {"$ref": "#/definitions/nope"}}}
    with pytest.raises(GateError, match="does not resolve"):
        validate({"x": 1}, bad, bad, "rec")


def test_external_ref_fails_closed() -> None:
    """A remote $ref would mean fetching a schema to validate; refuse instead."""
    bad = {"type": "object", "additionalProperties": False,
           "properties": {"x": {"$ref": "https://example.com/s.json"}}}
    with pytest.raises(GateError, match="unsupported"):
        validate({"x": 1}, bad, bad, "rec")


@pytest.mark.parametrize("payload", [
    "/Users/alice/secret-project",
    "contact bob@acme-internal.com",
    "https://api.acme-internal.com/v1",
    "AKIAIOSFODNN7EXAMPLE",
    "-----BEGIN RSA PRIVATE KEY-----",
    "10.0.4.19",
])
def test_leak_scan_catches_shapes(payload: str) -> None:
    """Defence in depth. If one of these ever fires on a real record, the schema leaked."""
    assert scan_leaks(payload), f"leak scan missed: {payload!r}"


def test_leak_scan_is_quiet_on_a_clean_record() -> None:
    """A noisy gate trains people to ignore it, which is how L19's TLD list got tightened."""
    assert scan_leaks(json.dumps(clean_record())) == []


# ---------------------------------------------------------------- bundles (multi-contributor)


@pytest.fixture
def bundle_schema() -> dict[str, Any]:
    return json.loads((REPO / "schemas" / "bundle.schema.json").read_text(encoding="utf-8"))


def write_bundle(tmp_path: Path, payload: dict[str, Any]) -> Path:
    p = tmp_path / "b.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_clean_bundle_passes(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0",
                                "vigil_version": "0.4.0", "records": [clean_record()]})
    assert check_bundle(p, bundle_schema, schema) == []


def test_bundle_validates_every_record_not_just_the_first(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    """The realistic failure: a long submission where only one record is dirty.

    Checking the envelope, or only records[0], would pass this — and the whole point of
    bundling is that submissions are long enough that nobody reads every record by hand.
    """
    dirty = clean_record()
    dirty["finding"] = "SQL injection in src/pay.py:12"
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0",
                                "records": [clean_record(), clean_record(), dirty]})
    errs = check_bundle(p, bundle_schema, schema)
    assert any("records[2]" in e for e in errs), errs


def test_contributor_handle_cannot_be_a_sentence(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    """The one identity field is also the one place prose could hide in an envelope."""
    p = write_bundle(tmp_path, {"schema_version": 1,
                                "contributor": "acme corp internal security team",
                                "records": [clean_record()]})
    assert any("contributor" in e for e in check_bundle(p, bundle_schema, schema))


def test_bundle_with_no_records_is_rejected(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0", "records": []})
    assert check_bundle(p, bundle_schema, schema)


def test_a_record_that_never_asked_cannot_be_bundled(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    """CONSENT IS STRUCTURAL. `shared` has no default, so a run that never put the question
    produces a record that cannot answer it — and therefore cannot be contributed.

    This is the case a policy would have missed: the first real run wrote a record, disclosed
    it to the user, gitignored it, and never asked. Every instruction was followed except the
    one that mattered, and L28 cannot detect that because it reads documentation, not runs.
    """
    rec = clean_record()
    del rec["shared"]
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0", "records": [rec]})
    assert any("not consent" in e for e in check_bundle(p, bundle_schema, schema))


def test_a_record_that_does_not_name_its_tree_cannot_be_bundled(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    """lessons/0010 — pooling a working-tree audit with a tracked-tree audit averages answers
    to different questions, and the result looks perfectly well-formed."""
    rec = clean_record()
    del rec["tree_state"]
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0", "records": [rec]})
    assert any("tree_state" in e for e in check_bundle(p, bundle_schema, schema))


def test_unknown_is_an_acceptable_tree_state(
    tmp_path: Path, bundle_schema: dict[str, Any], schema: dict[str, Any]
) -> None:
    """A gate that only accepts certainty pressures runs into guessing. Admitting ignorance
    must be cheaper than fabricating a value."""
    rec = clean_record()
    rec["tree_state"] = "unknown"
    p = write_bundle(tmp_path, {"schema_version": 1, "contributor": "dev0", "records": [rec]})
    assert check_bundle(p, bundle_schema, schema) == []
