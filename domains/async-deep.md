# VIGIL Domain Detail: Async / Concurrency Deep-Dive

**Parent cluster:** backend
**Loaded in:** siege mode, or --only backend --deep

## Deep Checks

### Event Loop Blocking

```bash
# Node.js: detect synchronous CPU-heavy operations
grep -rn "JSON.parse\|JSON.stringify" src/ --include="*.ts" --include="*.js" | grep -v "//\|test\|spec" | head -20
grep -rn "fs\.readFileSync\|fs\.writeFileSync\|fs\.existsSync" src/ --include="*.ts" | grep -v "//\|config\|startup"

# crypto operations on main thread
grep -rn "crypto\.pbkdf2Sync\|crypto\.scryptSync\|bcrypt\.hashSync" src/ --include="*.ts"

# Python: detect blocking I/O in async context
grep -rn "time\.sleep\|requests\.get\|requests\.post" src/ --include="*.py" | grep -v "def test_\|# "
grep -rn "async def\|await " src/ --include="*.py" | xargs grep -l "time\.sleep\|requests\." 2>/dev/null

# detect long regex in hot paths
grep -rn "\.match(\|\.test(\|\.replace(" src/ --include="*.ts" | grep -v "//\|spec\|test" | head -30
```

### Promise Rejection Handling

```bash
# unhandled promise rejections (Node.js)
grep -rn "\.then(" src/ --include="*.ts" --include="*.js" | grep -v "\.catch(\|\.finally(" | head -30
grep -rn "new Promise(" src/ --include="*.ts" | grep -v "reject\|catch" | head -20

# async functions without try/catch
grep -rn "^  async\|^async function\|= async (" src/ --include="*.ts" | head -20
# then check: those files missing try/catch patterns
grep -rn "async function\|async (" src/ --include="*.ts" -l | xargs grep -L "try {" 2>/dev/null | head -10

# Python asyncio unhandled coroutines
grep -rn "asyncio\.create_task\|loop\.create_task" src/ --include="*.py" | grep -v "\.add_done_callback\|result()" | head -20

# fire-and-forget patterns
grep -rn "void " src/ --include="*.ts" | grep -v "//\|return void\|: void" | head -20
```

### Race Condition Patterns

```bash
# read-modify-write without transaction
grep -rn "findOne\|findById\|SELECT.*WHERE" src/ --include="*.ts" --include="*.py" | head -20
# check same files for subsequent update without transaction wrapper
grep -rn "session\|transaction\|BEGIN\|COMMIT" src/ --include="*.ts" --include="*.py" | wc -l

# check-then-act (TOCTOU)
grep -rn "if.*exists\|if.*!exists" src/ --include="*.ts" --include="*.py" | grep -v "await " | head -20

# concurrent cache updates without locking
grep -rn "cache\.get\|redis\.get\|\.get(" src/ --include="*.ts" | head -20

# Python: asyncio.gather without error isolation
grep -rn "asyncio\.gather(" src/ --include="*.py" | grep -v "return_exceptions=True" | head -10

# TypeScript: multiple awaits on same mutable resource
grep -rn "await " src/ --include="*.ts" | awk -F: '{print $1}' | sort | uniq -d | head -10
```

### Deadlock Detection

```bash
# nested lock acquisition order inconsistency
grep -rn "acquire\|lock\(\|mutex\|semaphore" src/ --include="*.ts" --include="*.py" | head -30

# Python threading deadlock risk: nested locks
grep -rn "threading\.Lock\|threading\.RLock\|asyncio\.Lock" src/ --include="*.py"
grep -rn "with.*lock\|await.*lock\|lock\.acquire" src/ --include="*.py" | head -20

# database-level deadlock: transactions acquiring locks in different order
grep -rn "FOR UPDATE\|LOCK TABLE\|SELECT.*FOR SHARE" src/ --include="*.ts" --include="*.py" | head -10

# circular awaits between services
grep -rn "await.*Service\|await.*Client" src/ --include="*.ts" | awk '{print $1}' | sort | uniq -c | sort -rn | head -10
```

### Semaphore and Concurrency Limits

```bash
# missing concurrency limits on parallel operations
grep -rn "Promise\.all(\|asyncio\.gather(" src/ --include="*.ts" --include="*.py" | head -30
# check if p-limit or semaphore wraps these
grep -rn "p-limit\|pLimit\|bottleneck\|Semaphore\|asyncio\.Semaphore" src/ --include="*.ts" --include="*.py" | wc -l

# unbounded fan-out patterns
grep -rn "\.map(.*async\|\.map(.*await" src/ --include="*.ts" | head -20

# Python: asyncio.Semaphore usage
grep -rn "Semaphore(" src/ --include="*.py"
```

### Worker Thread Patterns

```bash
# Node.js worker threads
grep -rn "worker_threads\|new Worker(" src/ --include="*.ts" --include="*.js"
grep -rn "workerData\|parentPort\|postMessage" src/ --include="*.ts"

# CPU-bound work not offloaded to worker
grep -rn "for.*let i\|while.*i <\|reduce(" src/ --include="*.ts" | grep -v "//\|test\|spec" | head -20

# Python multiprocessing vs threading
grep -rn "from multiprocessing\|import threading\|concurrent\.futures" src/ --include="*.py"
grep -rn "ProcessPoolExecutor\|ThreadPoolExecutor" src/ --include="*.py"
```

### Connection Pool Starvation

```bash
# pool size vs concurrent requests
grep -rn "pool_size\|poolSize\|max_connections\|maxConnections\|min\|max" src/ --include="*.ts" --include="*.py" | grep -i "pool\|connect" | head -20

# connections not released on error
grep -rn "\.connect(\|pool\.acquire\|pool\.query" src/ --include="*.ts" | head -20
# check corresponding release/finally patterns
grep -rn "pool\.release\|client\.release\|\.end()" src/ --include="*.ts" | wc -l

# HTTP client without keep-alive / connection reuse
grep -rn "new.*HttpClient\|axios\.create\|fetch(" src/ --include="*.ts" | head -20
grep -rn "agent:\|keepAlive:\|maxSockets:" src/ --include="*.ts" | wc -l
```

### Backpressure Handling

```bash
# Node.js streams without backpressure
grep -rn "\.pipe(\|createReadStream\|createWriteStream" src/ --include="*.ts" | grep -v "pipeline\|pump" | head -20
grep -rn "readable\.pipe\|writable\.write" src/ --include="*.ts" | grep -v "if.*write\|drain" | head -10

# SSE/WebSocket message queue without limits
grep -rn "res\.write\|ws\.send\|socket\.emit" src/ --include="*.ts" | head -20
grep -rn "highWaterMark\|objectMode\|MAX_BUFFER" src/ --include="*.ts" | wc -l

# Python async generators without backpressure
grep -rn "async for\|async_generator\|aiostream" src/ --include="*.py" | head -20
```

## Advanced Patterns

| Pattern | Severity | Category |
|---------|----------|----------|
| `await` inside `forEach` loop | High | Runs sequentially, defeats async purpose OR fire-and-forget |
| `Promise.all` on 1000+ items with no concurrency limit | High | Pool exhaustion / OOM |
| Mutex not released in error path | Critical | Deadlock |
| Async constructor (`new X()` where X fetches data) | Medium | Race on initialization |
| `setInterval` callback longer than interval | High | Event loop starvation |
| `JSON.parse` of 10MB+ payload on main thread | High | Blocks for 100-500ms |
| Redis/DB query in tight loop (N+1 async) | High | Hammers connection pool |
| Missing `await` on fire-and-forget DB write | Medium | Silent data loss |
| `asyncio.run()` called inside running event loop | Critical | RuntimeError crash |
| No timeout on external HTTP calls | High | Connection leak on hung upstream |
