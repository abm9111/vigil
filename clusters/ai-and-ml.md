# VIGIL Cluster: AI & ML

**Covers:** ML pipelines, model management, data validation, bias, prompt injection, LLM security
**Weight:** 8% (excluded if no ML/AI detected)
**ID prefix:** VIGIL-AIML

## Detection

This cluster is N/A if none of these exist:
- Python packages: torch, tensorflow, sklearn, transformers, langchain, openai, anthropic, llamaindex
- Files matching: `*model*`, `*train*`, `*inference*`, `*pipeline*`, `*agent*`, `*prompt*`
- Directories: `models/`, `ml/`, `ai/`, `agents/`

```bash
# Detect AI/ML presence
grep -rn --include='*.py' \
  -E 'import (torch|tensorflow|sklearn|transformers|langchain|openai|anthropic|llama_index|crewai|autogen)' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

## Deterministic Tools

### LLM Security

```bash
# Prompt injection vectors (user input → LLM prompt)
grep -rn --include='*.py' -E 'f["\x27].*\{.*user.*\}.*prompt|prompt.*\+.*input|messages.*append.*user' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# API key exposure
grep -rn --include='*.py' -E 'openai\.api_key|OPENAI_API_KEY|ANTHROPIC_API_KEY|api_key\s*=' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Tool calling without validation
grep -rn --include='*.py' -E 'tool_call|function_call|tools\s*=' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Output validation
grep -rn --include='*.py' -E 'response\.(content|text|choices)|completion\.' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### MCP Server & Tool Metadata Security

```bash
# MCP server definitions (tool poisoning surface)
grep -rn --include='*.py' --include='*.js' --include='*.ts' --include='*.json' \
  -E 'mcp|mcpServers|tool_name|tool_description|MCP' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Tool descriptions that could contain injection payloads
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'description.*=.*["\x27].*ignore|description.*=.*["\x27].*instead|description.*=.*["\x27].*system' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# MCP tool input validation (or lack thereof)
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'tool_input|tool_call.*args|function_call.*arguments' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Server-side tool execution without sandboxing
grep -rn --include='*.py' \
  -E 'exec\(|eval\(|subprocess\.(run|call|Popen).*tool|os\.system.*tool' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# MCP transport security (stdio vs HTTP)
grep -rn -E 'stdio|sse|streamable.*http|localhost.*mcp|127\.0\.0\.1.*mcp' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null

# Tool result injection (LLM reads tool output that could contain adversarial text)
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'tool_result|function_result|tool_output' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

**MCP-specific attack patterns to check:**
1. **Tool poisoning:** Malicious tool descriptions that instruct the LLM to exfiltrate data
2. **Rug pull tools:** Tool that changes behavior after initial trust-building calls
3. **Cross-tool injection:** Tool A's output contains instructions that affect Tool B's execution
4. **Schema override:** Tool with overloaded parameter names that shadow system parameters
5. **Transport MITM:** HTTP-based MCP without TLS (stdio is safe, HTTP is not)

### Indirect Prompt Injection Detection

```bash
# User content flowing into system/tool prompts
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'system.*message.*user|system.*prompt.*input|system.*f["\x27].*\{' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# RAG retrieval without content sanitization
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'retrieve|search.*embed|vector.*query|similarity.*search' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Multi-modal injection surface (images, PDFs, URLs fed to LLM)
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'image.*content|pdf.*extract|url.*fetch.*prompt|file.*read.*llm' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Agent loop without iteration/cost limits
grep -rn --include='*.py' --include='*.js' --include='*.ts' \
  -E 'while.*True.*tool|max_steps|max_iterations|max_turns|loop.*agent' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null
```

### Model Management

```bash
# Model versioning
grep -rn -E 'model_version|model_name|model_id|checkpoint' . \
  --exclude-dir={node_modules,.venv,.git} 2>/dev/null

# Large model files in git
git ls-files --others --exclude-standard 2>/dev/null | xargs file 2>/dev/null | \
  grep -iE 'data|binary' | head -10
find . -name '*.bin' -o -name '*.pt' -o -name '*.h5' -o -name '*.onnx' -o -name '*.safetensors' | \
  grep -v .venv | grep -v node_modules 2>/dev/null

# Model loading patterns
grep -rn --include='*.py' -E '\.load_model\(|\.from_pretrained\(|torch\.load\(|pickle\.load\(' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

### Data Validation

```bash
# Input validation before inference
grep -rn --include='*.py' -E 'validate|sanitize|clean.*input|preprocess' . \
  --exclude-dir={.venv,node_modules,.git,tests} 2>/dev/null

# Data pipeline checks
grep -rn --include='*.py' -E 'assert.*shape|assert.*dtype|check.*schema' . \
  --exclude-dir={.venv,node_modules,.git} 2>/dev/null
```

## Finding Patterns

### LLM Security (VIGIL-AIML-0xx)

| Pattern | Severity |
|---------|----------|
| User input directly in prompt (no sanitization) | HIGH |
| LLM output used in SQL/command without validation | CRITICAL |
| API key hardcoded for LLM service | HIGH |
| No output validation on LLM response | MEDIUM |
| Tool/function calling without permission checks | HIGH |
| Prompt template injection via variable interpolation | HIGH |
| No rate limiting on LLM API calls | MEDIUM |
| No cost monitoring for LLM usage | MEDIUM |
| MCP tool description contains injection payload | CRITICAL |
| MCP tool executes code without sandbox | CRITICAL |
| MCP HTTP transport without TLS | HIGH |
| MCP tool result not sanitized before LLM consumption | HIGH |
| RAG retrieval without content sanitization | HIGH |
| Agent loop without max iteration/cost limit | HIGH |
| Indirect prompt injection via retrieved documents | HIGH |
| Multi-modal injection (image/PDF/URL content to LLM) | HIGH |
| Cross-tool injection (Tool A output affects Tool B) | HIGH |

### Model Management (VIGIL-AIML-1xx)

| Pattern | Severity |
|---------|----------|
| Model files in git (should be in artifact store) | MEDIUM |
| No model versioning | MEDIUM |
| pickle.load on untrusted data | CRITICAL |
| No model validation before deployment | HIGH |
| Hardcoded model paths | LOW |

### Data Quality (VIGIL-AIML-2xx)

| Pattern | Severity |
|---------|----------|
| No input validation before inference | HIGH |
| No schema validation on training data | MEDIUM |
| Missing data type checks | MEDIUM |
| No handling of missing/null values | MEDIUM |
| Training data in source control (large files) | MEDIUM |

### Bias & Fairness (VIGIL-AIML-3xx)

| Pattern | Severity |
|---------|----------|
| No bias testing/evaluation | MEDIUM |
| Protected attributes used as features | HIGH |
| No model card/documentation | LOW |
| No A/B testing framework | LOW |

## AI Reasoning Section

1. **Prompt injection surface:** Where can user input reach LLM prompts? Are there sanitization layers?
2. **Output trust boundary:** Is LLM output treated as trusted? Is it validated before use in actions?
3. **Cost exposure:** What's the max cost per request? Any runaway potential?
4. **Model supply chain:** Are models loaded from trusted sources? Any deserialization risks?
5. **Agent safety:** If using autonomous agents, what's the blast radius of a hallucinated action?
