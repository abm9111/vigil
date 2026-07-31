# VIGIL Adapter: Cursor IDE

**Purpose:** Instructions for using VIGIL in Cursor IDE via its AI features.

## Setup

Add to `.cursorrules` or Cursor's custom instructions:

```
When asked to audit, review, or check code quality, follow the VIGIL methodology:

1. Run deterministic tools first (ruff, bandit, eslint, etc.)
2. Parse tool output into findings with severity levels
3. Apply cross-domain correlation (check if findings on the same endpoint compound)
4. Score each domain cluster 0-100 with weighted overall score
5. Report with VIGIL-{CLUSTER}-{NNN} finding IDs

Severity levels: CRITICAL (25pt penalty), HIGH (10pt), MEDIUM (4pt), LOW (1pt)
Production-ready requires overall >= 80 AND every applicable cluster at full
evidence coverage. Partial evidence or any N/E cluster => INCOMPLETE, never a pass.
```

## Usage in Cursor

1. Select code or open a file
2. Ask Cursor AI: "Run a VIGIL audit on this file" or "Check security with VIGIL methodology"
3. For project-wide: "VIGIL scan this project"

## Limitations in Cursor

- Cannot run CLI tools directly (no bash access in chat)
- Relies on AI analysis only (no deterministic tool enforcement)
- No baseline/trend tracking
- Best used for single-file or small-scope reviews

## Recommended Workflow

1. Use Cursor for inline `/vigil-explain` style deep-dives on specific findings
2. Use Claude Code for full `/vigil audit` with tool execution
3. Use CI for `/vigil watch --ci` automated gates
