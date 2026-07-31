#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 LocalForge
"""Gate between a local run record and anything leaving the user's machine.

Nothing VIGIL learns from a real user may carry that user's work. `L19` enforces this on
`lessons/` by grepping prose, and openly admits it cannot read prose — it catches hostnames,
not "we rely on a legacy service for authorisation and it is not covered by tests".

This gate is the structural half, and it is the one that actually holds. A run record is
validated against `schemas/run-record.schema.json`, where every string is an enum or a bounded
pattern and `additionalProperties` is false at every level. A file path has no field to live
in. The record is not redacted — it was never able to hold the thing in the first place.

The regex scan below is defence in depth, not the mechanism. If it ever fires, the schema had
a hole, and that is the bug to fix.

FAILS CLOSED. Unreadable file, missing schema, unknown keyword, unexpected exception — all
non-zero. A gate that passes when it cannot tell is not a gate (`lessons/0001`).

    python3 evals/privacy_gate.py <record.json> [...]
    python3 evals/privacy_gate.py --dir .vigil/runs
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas" / "run-record.schema.json"
BUNDLE_SCHEMA_PATH = ROOT / "schemas" / "bundle.schema.json"

# Defence in depth only. The schema is the mechanism; if one of these fires the schema leaked.
LEAK_SHAPES: list[tuple[str, str]] = [
    (r"/(?:Users|home)/[A-Za-z0-9._-]+", "an absolute home path"),
    (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "an email address"),
    (r"\b(?:[a-z0-9-]+\.)+(?:com|org|net|io|ai|dev|co|app|cloud|ae|uk|de)\b", "a hostname"),
    (r"\b(?:sk|pk|ghp|gho|xox[bp]|AKIA|AIza)[-_A-Za-z0-9]{10,}", "an API-key shape"),
    (r"-----BEGIN [A-Z ]*PRIVATE KEY-----", "a private key block"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "an IP address"),
]


class GateError(Exception):
    """Anything that means the record cannot be cleared."""


def _resolve(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    """Follow a local $ref. Only '#/...' pointers are supported; anything else fails closed."""
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not isinstance(ref, str) or not ref.startswith("#/"):
        raise GateError(f"unsupported $ref {ref!r} — cannot validate, refusing to pass")
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict) or part not in node:
            raise GateError(f"$ref {ref!r} does not resolve")
        node = node[part]
    if not isinstance(node, dict):
        raise GateError(f"$ref {ref!r} does not point at a schema object")
    return node


# Keywords this validator understands. An unknown keyword in the schema means the schema is
# asserting something we are not checking, so we refuse rather than pass a partial validation.
KNOWN = {
    "$schema", "$id", "$ref", "title", "description", "definitions",
    "type", "enum", "const", "properties", "additionalProperties", "required",
    "items", "minItems", "uniqueItems", "minimum", "maximum", "pattern",
}

TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict, "array": list, "string": str, "integer": int,
    "number": (int, float), "boolean": bool, "null": type(None),
}


def validate(node: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> list[str]:
    schema = _resolve(schema, root)
    errs: list[str] = []

    unknown = set(schema) - KNOWN
    if unknown:
        raise GateError(f"{path}: schema uses keyword(s) {sorted(unknown)} this gate does not "
                        "implement — refusing to report a pass it cannot justify")

    if "const" in schema and node != schema["const"]:
        errs.append(f"{path}: expected {schema['const']!r}, got {node!r}")

    if "enum" in schema and node not in schema["enum"]:
        # The important error. A value outside the enum is exactly how free text would arrive.
        errs.append(f"{path}: {node!r} is not one of the permitted values — "
                    "free text cannot be recorded here")

    expected = schema.get("type")
    if expected:
        want = TYPES.get(expected)
        if want is None:
            raise GateError(f"{path}: unknown type {expected!r}")
        # bool is an int subclass in Python; an integer field must not accept True.
        if expected in ("integer", "number") and isinstance(node, bool):
            errs.append(f"{path}: expected {expected}, got boolean")
        elif not isinstance(node, want):
            errs.append(f"{path}: expected {expected}, got {type(node).__name__}")
            return errs  # structure is wrong; deeper checks would be noise

    if isinstance(node, str) and "pattern" in schema and not re.search(schema["pattern"], node):
        errs.append(f"{path}: {node!r} does not match {schema['pattern']!r}")

    if isinstance(node, (int, float)) and not isinstance(node, bool):
        if "minimum" in schema and node < schema["minimum"]:
            errs.append(f"{path}: {node} is below minimum {schema['minimum']}")
        if "maximum" in schema and node > schema["maximum"]:
            errs.append(f"{path}: {node} is above maximum {schema['maximum']}")

    if isinstance(node, dict):
        props: dict[str, Any] = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in node:
                errs.append(f"{path}: missing required field {req!r}")
        if schema.get("additionalProperties") is False:
            for key in node:
                if key not in props:
                    errs.append(f"{path}: unexpected field {key!r} — the schema is closed, so "
                                "an unknown field is either a typo or smuggled content")
        for key, value in node.items():
            if key in props:
                errs += validate(value, props[key], root, f"{path}.{key}")

    if isinstance(node, list):
        if "minItems" in schema and len(node) < schema["minItems"]:
            errs.append(f"{path}: needs at least {schema['minItems']} item(s)")
        if schema.get("uniqueItems"):
            seen = [json.dumps(x, sort_keys=True) for x in node]
            if len(set(seen)) != len(seen):
                errs.append(f"{path}: contains duplicate items")
        if "items" in schema:
            for i, item in enumerate(node):
                errs += validate(item, schema["items"], root, f"{path}[{i}]")

    return errs


def scan_leaks(raw: str) -> list[str]:
    """Defence in depth. A hit here means the schema failed, not that redaction is needed."""
    out: list[str] = []
    for pattern, what in LEAK_SHAPES:
        m = re.search(pattern, raw)
        if m:
            out.append(f"raw record contains {what} ({m.group(0)[:24]!r}) — the schema should "
                       "have made this impossible; fix the schema, not the record")
    return out


def check_bundle(path: Path, bundle_schema: dict[str, Any],
                 record_schema: dict[str, Any]) -> list[str]:
    """Validate a contributed bundle: envelope first, then every record inside it.

    Two schemas rather than one cross-file $ref, because resolving a $ref to another file
    means the validator must fetch something to decide, and this gate refuses to pass anything
    it had to reach for. The composition is explicit so the failure mode is obvious: a bundle
    whose envelope is fine but whose third record smuggles a path is still blocked, and the
    error says which record.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path.name}: {exc}"]
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"{path.name} is not valid JSON: {exc}"]

    errs = validate(bundle, bundle_schema, bundle_schema, path.name)
    records = bundle.get("records") if isinstance(bundle, dict) else None
    if isinstance(records, list):
        for i, record in enumerate(records):
            errs += validate(record, record_schema, record_schema, f"{path.name}.records[{i}]")
    errs += scan_leaks(raw)
    return errs


def check_file(path: Path, schema: dict[str, Any]) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read {path.name}: {exc}"]
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"{path.name} is not valid JSON: {exc}"]
    return validate(record, schema, schema, path.name) + scan_leaks(raw)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("records", nargs="*", type=Path)
    ap.add_argument("--dir", type=Path, help="validate every *.json in this directory")
    ap.add_argument("--bundles", action="store_true",
                    help="treat inputs as contributed bundles (envelope + every record inside)")
    args = ap.parse_args()

    targets: list[Path] = list(args.records)
    if args.dir:
        if not args.dir.is_dir():
            print(f"--dir {args.dir} is not a directory", file=sys.stderr)
            return 2
        targets += sorted(args.dir.rglob("*.json") if args.bundles
                          else args.dir.glob("*.json"))
    if not targets:
        print("nothing to clear", file=sys.stderr)
        return 2

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        bundle_schema = json.loads(BUNDLE_SCHEMA_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot load schema: {exc}", file=sys.stderr)
        return 2

    blocked = 0
    for path in targets:
        try:
            errs = (check_bundle(path, bundle_schema, schema) if args.bundles
                    else check_file(path, schema))
        except GateError as exc:
            errs = [str(exc)]
        except Exception as exc:  # fail closed on anything unexpected — see module docstring
            errs = [f"gate raised {type(exc).__name__}: {exc}"]
        if errs:
            blocked += 1
            print(f"BLOCKED {path.name}", file=sys.stderr)
            for e in errs:
                print(f"  - {e}", file=sys.stderr)

    total = len(targets)
    if blocked:
        print(f"\nprivacy gate: {blocked}/{total} record(s) BLOCKED — nothing may be "
              "contributed until these are clean", file=sys.stderr)
        return 1
    print(f"privacy gate: {total} record(s) CLEAR — no field in these can hold your work")
    return 0


if __name__ == "__main__":
    sys.exit(main())
