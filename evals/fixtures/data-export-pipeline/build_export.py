#!/usr/bin/env python3
"""Build the customer analytics export bundle for the partner data exchange.

Reads the enriched customer table, flattens it, and writes an XLSX + CSV bundle
plus a checksum manifest for the receiving organisation.

    python3 build_export.py
"""
from __future__ import annotations

import hashlib
import shutil
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "export"
SOURCE = ROOT / "customer_registry.json"
ENRICHED = ROOT / "enrichment.json"

SNAPSHOT = date(2026, 3, 1)
LIST_SEP = " | "


def flatten(df: pd.DataFrame) -> pd.DataFrame:
    """Render list-valued cells as delimited text."""
    out = df.copy()
    for col in out.columns:
        if out[col].map(lambda v: isinstance(v, (list, tuple))).any():
            out[col] = out[col].map(
                lambda v: LIST_SEP.join(str(x) for x in v)
                if isinstance(v, (list, tuple))
                else ("" if v is None else v)
            )
    return out


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def recipient_readme(rows: int) -> str:
    return f"""# Segment Analytics Export — Partner Instructions

Snapshot: {SNAPSHOT.isoformat()} · Built: {date.today().isoformat()}
Rows: {rows}

## Columns

| Column | Meaning |
|---|---|
| `segment_code` | Segment identifier |
| `segment_name` | Segment display name |
| `account_count` | Accounts in segment |
| `risk_tier` | Assigned risk tier |
| `summary` | Segment description |
| `recommended_action` | Suggested next step for this segment |
| `tags` | Segment tags |

Split multi-value columns on ` {LIST_SEP.strip()} `.

## Verifying

Compare each file against MANIFEST.sha256, included in this bundle.
"""


def main() -> None:
    # Fresh output directory for every build.
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    df = pd.read_parquet(ROOT / "segments.parquet")
    enrich = pd.read_json(ENRICHED)
    df = df.merge(enrich, on="segment_code", how="left")

    flat = flatten(df)
    flat.to_csv(OUT / "segments.csv", index=False)
    flat.to_excel(OUT / "segments.xlsx", index=False)
    (OUT / "README.md").write_text(recipient_readme(len(flat)), encoding="utf-8")

    files = sorted(p for p in OUT.rglob("*") if p.is_file())
    manifest = "\n".join(f"{sha256(p)}  {p.relative_to(OUT)}" for p in files)
    (OUT / "MANIFEST.sha256").write_text(manifest + "\n", encoding="utf-8")

    print(f"wrote {len(files) + 1} files to {OUT}")


if __name__ == "__main__":
    main()
