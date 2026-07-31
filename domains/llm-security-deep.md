# VIGIL Domain Detail: LLM Security Deep-Dive

**Parent cluster:** security
**Loaded in:** siege mode, or --only security --deep

## Deep Checks

### Prompt Injection — Direct

```bash
# user input injected directly into system prompt
grep -rn "system.*prompt\|system_prompt\|systemPrompt" src/ --include="*.py" --include="*.ts" | head -20
# check if user content flows in
grep -rn "f\"{.*user\|f'{.*user\|`${.*user\|format.*user_input\|\+ user_" src/ --include="*.py" --include="*.ts" | head -20

# template literal injection into prompt
grep -rn 'f""".*{user\|f'"'"'.*{user\|`.*${req\|`.*${user\|`.*${body' src/ --include="*.py" --include="*.ts" | head -20

# concatenation of untrusted data into messages array
grep -rn "messages\.append\|messages\.push\|messages\[" src/ --include="*.py" --include="*.ts" | grep -v "role.*system\|#\|//" | head -20

# missing role separation (user content in system role)
grep -rn '"role".*"system"\|role=.system' src/ --include="*.py" --include="*.ts" | head -10
```

### Prompt Injection — Indirect (RAG / Tool Output)

```bash
# tool output inserted into prompt without sanitization
grep -rn "tool_output\|tool_result\|function_result\|tool_call_result" src/ --include="*.py" --include="*.ts" | head -20

# document content from DB/web injected into prompt
grep -rn "context\|retrieved\|chunks\|documents" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test" | head -30
# check if sanitization applied before prompt insertion
grep -rn "sanitize\|escape\|strip_tags\|bleach\|dompurify\|clean_text" src/ --include="*.py" --include="*.ts" | wc -l

# web scraping content fed to LLM
grep -rn "requests\.get\|httpx\|fetch.*url\|scrape\|crawl" src/ --include="*.py" --include="*.ts" | xargs grep -l "openai\|anthropic\|llm\|chat" 2>/dev/null | head -10
```

### Jailbreak Pattern Detection

```bash
# detect if model output is checked before acting on it
grep -rn "model_output\|llm_response\|completion\|\.choices\[0\]" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "validate\|check\|verify\|guard\|filter" src/ --include="*.py" --include="*.ts" | grep -i "output\|response\|completion" | head -10

# role-play escape patterns in prompt templates
grep -rn "pretend\|act as\|ignore previous\|DAN\|jailbreak\|roleplay" src/ --include="*.py" --include="*.ts" -i | head -10

# guardrails / moderation API usage
grep -rn "moderations\|content.filter\|guardrails\|nemo-guardrails\|llm-guard\|rebuff" src/ --include="*.py" --include="*.ts" | wc -l
```

### Output Validation

```bash
# LLM output used in code execution
grep -rn "eval(\|exec(\|subprocess\|os\.system\|child_process" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "llm\|openai\|anthropic\|completion" src/ --include="*.py" --include="*.ts" -l | xargs grep -l "eval\|exec\|subprocess" 2>/dev/null

# LLM output used in SQL queries
grep -rn "\.execute(\|\.query(\|f\"SELECT\|f'SELECT\|cursor\.execute" src/ --include="*.py" | head -20
grep -rn "llm\|openai\|completion" src/ --include="*.py" -l | xargs grep -l "execute\|query\|SELECT" 2>/dev/null

# LLM output rendered as HTML (XSS via LLM)
grep -rn "dangerouslySetInnerHTML\|innerHTML\|v-html\|marked\|DOMParser" src/ --include="*.tsx" --include="*.ts" | head -20

# structured output validation (Pydantic/Zod)
grep -rn "response_model\|parse_obj\|\.parse(\|zodParse\|safeParse\|jsonschema\|validate(" src/ --include="*.py" --include="*.ts" | grep -i "llm\|completion\|output\|response" | head -10
```

### Tool Use Safety

```bash
# tool definitions with filesystem access
grep -rn '"type".*"function"\|tools=\[' src/ --include="*.py" --include="*.ts" | head -20
grep -rn "read_file\|write_file\|delete_file\|os\.remove\|shutil\|pathlib" src/ --include="*.py" | grep -i "tool\|function\|agent" | head -10

# tool definitions with network access
grep -rn "requests\|httpx\|aiohttp\|fetch\|curl" src/ --include="*.py" --include="*.ts" | grep -i "tool\|agent\|function" | head -10

# tool result passed back without validation
grep -rn "tool_result\|function_call.*result\|ToolMessage" src/ --include="*.py" --include="*.ts" | head -20

# agent loop without iteration limit
grep -rn "while.*True\|while.*running\|max_steps\|max_iterations\|MAX_STEPS" src/ --include="*.py" --include="*.ts" | grep -i "agent\|loop\|step" | head -10
```

### PII Leakage to LLM Providers

```bash
# PII fields flowing into prompts
grep -rn "email\|phone\|ssn\|passport\|national_id\|dob\|date_of_birth\|credit_card" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test\|spec" | head -30

# check if PII is masked/anonymized before prompt construction
grep -rn "mask\|anonymize\|redact\|hash\|pii_filter\|presidio" src/ --include="*.py" --include="*.ts" | wc -l

# logs of prompts containing PII
grep -rn "logger\.\|logging\.\|console\.log\|print(" src/ --include="*.py" --include="*.ts" | grep -i "prompt\|message\|user_input" | head -20

# LLM provider region / data residency config
grep -rn "azure_endpoint\|api_base\|base_url\|openai\.api_base" src/ --include="*.py" --include="*.ts" | head -10
```

### Cost Attack Vectors

```bash
# missing input token limits
grep -rn "max_tokens\|max_input_tokens\|truncate\|trim_prompt" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "openai\|anthropic\|llm" src/ --include="*.py" --include="*.ts" -l | xargs grep -L "max_tokens\|max_input" 2>/dev/null | head -10

# user-controlled prompt length
grep -rn "user.*prompt\|body.*prompt\|req\..*.prompt\|request.*query" src/ --include="*.py" --include="*.ts" | grep -v "//\|#\|test" | head -20

# rate limiting on LLM endpoints
grep -rn "RateLimiter\|rate_limit\|throttle\|slowapi\|limiter" src/ --include="*.py" --include="*.ts" | grep -i "llm\|chat\|completion\|api" | head -10

# missing cost tracking / budget enforcement
grep -rn "usage\.total_tokens\|usage\[.total_tokens\|prompt_tokens\|completion_tokens" src/ --include="*.py" --include="*.ts" | wc -l
```

### RAG Poisoning

```bash
# document ingestion without content validation
grep -rn "ingest\|upsert\|add_documents\|index\|embed" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "validate\|sanitize\|clean\|strip" src/ --include="*.py" --include="*.ts" | grep -i "ingest\|document\|chunk\|content" | head -10

# access control on retrieved documents
grep -rn "similarity_search\|search\|retrieve\|vector_store\|pgvector" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "user_id\|tenant_id\|permission\|acl\|filter.*user" src/ --include="*.py" --include="*.ts" | grep -i "search\|retriev\|query" | head -10

# source attribution — can users manipulate source metadata
grep -rn "metadata\|source\|author\|origin" src/ --include="*.py" --include="*.ts" | grep -i "ingest\|store\|embed" | head -10
```

## Advanced Patterns

| Pattern | Severity | Category |
|---------|----------|----------|
| User input directly in `system` role message | Critical | Direct prompt injection |
| Web-scraped content in RAG without sanitization | High | Indirect prompt injection |
| LLM output passed to `eval()` or `exec()` | Critical | Code injection via LLM |
| No max_tokens limit on user-initiated calls | High | Cost attack |
| PII in prompt without masking | High | Privacy / GDPR |
| Tool with write-filesystem capability, no path restriction | Critical | Agent sandbox escape |
| Infinite agent loop (no max_steps) | High | DoS / runaway cost |
| Streaming response with XSS-unsafe rendering | High | XSS via LLM output |
| Single tenant vector store (cross-tenant retrieval) | Critical | Data isolation breach |
| LLM output trusted as SQL/shell input | Critical | Injection via LLM hallucination |
| No content moderation on public-facing LLM endpoint | High | Jailbreak / ToS violation |
| Logging full prompt with user PII | Medium | Privacy / compliance |
