# VIGIL Domain Detail: WebSocket Patterns Deep-Dive

**Parent cluster:** backend
**Loaded in:** siege mode, or --only backend --deep

## Deep Checks

### Authentication on Connection

```bash
# JWT/token validation in WebSocket handshake
grep -rn "on.*connect\|on_connect\|websocket.*connect\|upgrade.*websocket" src/ --include="*.py" --include="*.ts" | head -20
grep -rn "Authorization\|token\|jwt\|bearer\|verify_token\|authenticate" src/ --include="*.py" --include="*.ts" | grep -i "websocket\|ws\|socket" | head -20

# anonymous connections allowed
grep -rn "io\.on\('connection'\|@websocket_route\|async def websocket\|websocket\.accept()" src/ --include="*.py" --include="*.ts") | head -20
grep -rn "auth.*required\|require_auth\|authenticated\|login_required" src/ --include="*.py" --include="*.ts") | grep -i "ws\|websocket\|socket" | head -10

# token passed in query string (logged in server access logs)
grep -rn "query.*token\|params.*token\|searchParams.*token\|token.*query" src/ --include="*.py" --include="*.ts") | grep -i "ws\|websocket\|connect" | head -10

# re-authentication after token expiry
grep -rn "token.*expir\|jwt.*expir\|refresh.*token\|unauthorized.*close\|close.*1008" src/ --include="*.py" --include="*.ts") | head -10
```

### Message Validation

```bash
# incoming message schema validation
grep -rn "websocket\.receive\|ws\.on\('message'\|on_message\|recv()\|receive_text\|receive_json" src/ --include="*.py" --include="*.ts") | head -20
# check if validation follows
grep -rn "pydantic\|zod\|validate\|parse\|schema\|jsonschema\|marshal" src/ --include="*.py" --include="*.ts") | grep -i "ws\|message\|socket" | head -10

# type coercion without validation
grep -rn "JSON\.parse\|json\.loads\|json\.parse" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket\|message\|receive" | head -20

# message type routing without exhaustive check
grep -rn "message\.type\|msg\.type\|data\.type\|payload\.type\|event\.type" src/ --include="*.py" --include="*.ts") | head -20
grep -rn "switch.*type\|if.*type.*===\|if.*type ==" src/ --include="*.py" --include="*.ts") | grep -i "message\|msg\|event" | head -10

# binary message deserialization (msgpack, protobuf)
grep -rn "msgpack\|protobuf\|flatbuffers\|cbor\|receive_bytes\|BINARY" src/ --include="*.py" --include="*.ts") | head -10
```

### Rate Limiting Per Connection

```bash
# per-connection rate limiting
grep -rn "rate_limit\|RateLimiter\|throttle\|token_bucket\|sliding_window" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket\|connection\|message" | head -20

# global rate limiting missing per-connection granularity
grep -rn "RateLimiter\|slowapi\|express-rate-limit\|rate.limit" src/ --include="*.py" --include="*.ts") | head -10

# max messages per second enforcement
grep -rn "max_messages\|msg_per_sec\|message_count\|MESSAGE_LIMIT\|flood" src/ --include="*.py" --include="*.ts") | head -10

# connection limit per user/IP
grep -rn "max_connections\|connection_limit\|max_conn\|per_user\|per_ip" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket" | head -10
```

### Reconnection Strategy

```bash
# client-side reconnection logic
grep -rn "reconnect\|onclose\|onerror\|RECONNECT\|backoff\|retry" src/ --include="*.ts" --include="*.tsx") | grep -i "ws\|websocket\|socket" | head -20

# exponential backoff
grep -rn "exponential\|backoff\|Math\.pow\|2 \*\*\|retryDelay\|retryCount" src/ --include="*.ts" --include="*.tsx") | grep -i "ws\|reconnect\|retry" | head -10

# max reconnection attempts (prevent infinite loop)
grep -rn "maxRetries\|MAX_RETRIES\|maxReconnect\|retryCount.*>\|attempts.*>" src/ --include="*.ts" --include="*.tsx") | grep -i "ws\|socket" | head -10

# session state recovery after reconnect
grep -rn "resume\|recover\|replay\|missed_messages\|last_event_id\|sequence" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket\|reconnect" | head -10
```

### Heartbeat / Ping-Pong

```bash
# server-side ping/heartbeat
grep -rn "ping\|pong\|heartbeat\|keepalive\|PING\|ping_interval" src/ --include="*.py" --include="*.ts") | grep -v "//\|#\|test" | head -20

# missing stale connection cleanup
grep -rn "close.*stale\|remove.*inactive\|cleanup.*connection\|ping_timeout\|CLOSE_TIMEOUT" src/ --include="*.py" --include="*.ts") | head -10

# Python websockets library ping config
grep -rn "ping_interval=\|ping_timeout=\|close_timeout=" src/ --include="*.py") | head -10

# Socket.IO heartbeat
grep -rn "pingInterval\|pingTimeout\|heartbeatInterval" src/ --include="*.ts") | head -10
```

### Message Size Limits

```bash
# max message size enforcement
grep -rn "max_size\|MAX_SIZE\|maxPayload\|max_message_size\|message_size_limit\|max_bytes" src/ --include="*.py" --include="*.ts") | grep -i "ws\|message\|socket" | head -20

# missing size check before processing
grep -rn "receive_text\|receive_bytes\|receive_json\|ws\.on\('message'" src/ --include="*.py" --include="*.ts") | xargs grep -L "len(\|\.length\|size\|limit" 2>/dev/null | head -10

# Python websockets default max_size (1MB)
grep -rn "websockets\.serve\|websocket\.serve\|serve(" src/ --include="*.py") | grep -v "max_size=" | head -10

# Socket.IO maxHttpBufferSize
grep -rn "maxHttpBufferSize\|perMessageDeflate\|compression" src/ --include="*.ts") | head -10
```

### Binary Message Handling

```bash
# binary data deserialization safety
grep -rn "receive_bytes\|BINARY\|ArrayBuffer\|Buffer\.from\|Uint8Array" src/ --include="*.py" --include="*.ts") | head -20

# file upload via WebSocket (high risk)
grep -rn "file.*upload\|upload.*file\|binary.*file\|ArrayBuffer.*file" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket\|message" | head -10

# content-type validation for binary
grep -rn "content_type\|mime_type\|magic_bytes\|file_type" src/ --include="*.py" --include="*.ts") | grep -i "binary\|bytes\|buffer\|ws" | head -10
```

### Broadcast Patterns

```bash
# broadcast to all connections (potential data leak)
grep -rn "broadcast\|io\.emit\|io\.to.*emit\|channel\.send_all\|manager\.broadcast" src/ --include="*.py" --include="*.ts") | head -20

# missing authorization check before broadcast
grep -rn "broadcast\|emit.*all\|to_all" src/ --include="*.py" --include="*.ts") | xargs grep -L "auth\|permission\|role\|user_id" 2>/dev/null | head -10

# fan-out to large number of connections (memory/CPU)
grep -rn "for.*connection\|for.*client\|for.*socket\|connections\.forEach\|clients\.forEach" src/ --include="*.py" --include="*.ts") | head -20

# Redis pub/sub for horizontal scaling
grep -rn "redis.*pubsub\|redis.*subscribe\|pubsub\|redis\.publish\|ioredis.*subscribe" src/ --include="*.py" --include="*.ts") | head -10
```

### Room and Namespace Isolation

```bash
# Socket.IO namespace authorization
grep -rn "io\.of(\|namespace\|nsp\b" src/ --include="*.ts") | head -20
grep -rn "io\.of(" src/ --include="*.ts") | xargs grep -L "auth\|middleware\|use(" 2>/dev/null | head -10

# room-level access control
grep -rn "join.*room\|socket\.join\|joinRoom\|leave_room" src/ --include="*.py" --include="*.ts") | head -20
grep -rn "room.*permission\|can.*join\|authorized.*room\|check.*room" src/ --include="*.py" --include="*.ts") | wc -l

# cross-tenant room isolation
grep -rn "room_id\|channel_id\|tenant_id" src/ --include="*.py" --include="*.ts") | grep -i "ws\|socket\|room" | head -20

# namespace per tenant vs shared namespace
grep -rn "namespace.*tenant\|tenant.*namespace\|org.*room\|room.*org" src/ --include="*.py" --include="*.ts") | head -10
```

## Advanced Patterns

| Pattern | Severity | Category |
|---------|----------|----------|
| No authentication on WebSocket handshake | Critical | Auth bypass |
| Token passed in query string (logged in access logs) | High | Credential exposure |
| No per-connection rate limiting | High | DoS / message flooding |
| Unbounded message size (no max_size) | High | Memory exhaustion |
| Broadcast without recipient authorization check | High | Data leakage |
| No stale connection cleanup (missing ping/timeout) | Medium | Resource leak |
| Client reconnects infinitely without backoff | Medium | Server amplification |
| Shared namespace across tenants | Critical | Cross-tenant data leak |
| JSON.parse without try/catch in message handler | Medium | Crash on malformed input |
| File upload via WebSocket without MIME validation | High | Malicious file upload |
| No sequence number / replay protection | Medium | Message replay attack |
| Missing room membership check before targeted send | High | Unauthorized message delivery |
