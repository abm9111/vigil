# VIGIL Domain Detail: Docker & Container Security

**Parent cluster:** docker
**Loaded in:** siege mode, or --only docker --deep

## Deep Checks

### Layer Analysis & Secret Leakage in Layers

```bash
# Inspect all layers in a built image for secrets
docker history --no-trunc <image:tag> 2>/dev/null | \
  grep -iE "ENV\s+(PASSWORD|SECRET|KEY|TOKEN)|ARG\s+(PASSWORD|SECRET|KEY)"

# Dive — layer-by-layer filesystem diff (find secrets baked in)
dive <image:tag> 2>/dev/null || \
  echo "Install: brew install dive / apt install dive"

# Extract all layer filesystems and scan for secrets
docker save <image:tag> | tar xO 2>/dev/null | \
  grep -aE "(password|secret|key|token)\s*[=:]\s*[^\s]+" 2>/dev/null | head -20

# Check ENV vars baked into image metadata
docker inspect <image:tag> 2>/dev/null | \
  python3 -c "
import json, sys
data = json.load(sys.stdin)
for img in data:
    env = img.get('Config', {}).get('Env', [])
    for e in env:
        k = e.split('=')[0].upper()
        if any(x in k for x in ['PASSWORD','SECRET','KEY','TOKEN','PASS']):
            print('SENSITIVE ENV:', e[:80])
"

# Grep Dockerfiles for secrets in build args / ENV
grep -rn --include="Dockerfile*" \
  -E "^(ENV|ARG)\s+.*(PASSWORD|SECRET|KEY|TOKEN|PASS)\s*=\s*\S+" . 2>/dev/null
```

### Excessive Capabilities & Privilege

```bash
# Find containers running as root (no USER directive)
grep -rn --include="Dockerfile*" -E "^USER\s+" . 2>/dev/null || \
  echo "WARNING: No USER directives found — containers may run as root"

# Check docker-compose for privileged containers
grep -rn --include="docker-compose*.yml" --include="docker-compose*.yaml" \
  -E "privileged:\s*true|cap_add:|SYS_ADMIN|NET_ADMIN" . 2>/dev/null

# Check --cap-add in run commands
grep -rn --include="*.sh" --include="Makefile" \
  -E "docker run.*--privileged|docker run.*--cap-add\s+SYS_ADMIN" . 2>/dev/null

# Running containers: check for privileged flag
docker ps -q 2>/dev/null | while read cid; do
    priv=$(docker inspect "$cid" --format '{{.HostConfig.Privileged}}' 2>/dev/null)
    caps=$(docker inspect "$cid" --format '{{.HostConfig.CapAdd}}' 2>/dev/null)
    name=$(docker inspect "$cid" --format '{{.Name}}' 2>/dev/null)
    [ "$priv" = "true" ] && echo "PRIVILEGED: $name"
    [ "$caps" != "[]" ] && echo "EXTRA CAPS ($name): $caps"
done

# seccomp and AppArmor profiles
docker inspect <container> --format '{{.HostConfig.SecurityOpt}}' 2>/dev/null
```

### Network Exposure

```bash
# Ports bound to 0.0.0.0 (exposed to all interfaces, not just localhost)
docker-compose config 2>/dev/null | grep -E "^\s+\-\s+[0-9]+:[0-9]+" | \
  grep -v "127\.0\.0\.1\|localhost"

# Check docker-compose port bindings
grep -rn --include="docker-compose*.yml" --include="docker-compose*.yaml" \
  -E "^\s+- \"?[0-9]+:[0-9]+" . 2>/dev/null | \
  grep -v "127\.0\.0\.1" | head -20

# Running containers — check exposed ports
docker ps --format "table {{.Names}}\t{{.Ports}}" 2>/dev/null | \
  grep -v "127\.0\.0\.1" | grep "0\.0\.0\.0"

# Compose networks — check for host network mode
grep -rn --include="docker-compose*.yml" \
  -E "network_mode:\s*host" . 2>/dev/null
```

### Volume Mount Security

```bash
# Docker socket mounted (container escape via docker-in-docker)
grep -rn --include="docker-compose*.yml" --include="docker-compose*.yaml" \
  -E "/var/run/docker\.sock" . 2>/dev/null

# Sensitive host paths mounted (/ , /etc, /proc, /sys)
grep -rn --include="docker-compose*.yml" --include="docker-compose*.yaml" \
  -E "volumes:.*- /(etc|proc|sys|var|root|home):" . 2>/dev/null

# Running containers — check dangerous volume mounts
docker ps -q 2>/dev/null | while read cid; do
    mounts=$(docker inspect "$cid" --format '{{range .Mounts}}{{.Source}} -> {{.Destination}} [{{.Mode}}]{{"\n"}}{{end}}' 2>/dev/null)
    name=$(docker inspect "$cid" --format '{{.Name}}' 2>/dev/null)
    echo "$mounts" | grep -E "^/(etc|proc|sys|var/run|root|home)" && echo "  ^ in $name"
done

# Read-write mounts on sensitive dirs
grep -rn --include="docker-compose*.yml" \
  -E "- /etc.*:.*:rw|/var/run/docker.*:.*:rw" . 2>/dev/null
```

### Multi-Stage Build Optimization & Secrets

```bash
# Check if secrets are properly cleaned in single-stage builds
grep -rn --include="Dockerfile*" \
  -A 2 -B 2 -E "RUN.*pip install|RUN.*npm install|RUN.*apt-get" . 2>/dev/null | \
  grep -E "secret\|password\|token\|key"

# Verify multi-stage: final stage doesn't copy build artifacts with secrets
grep -rn --include="Dockerfile*" \
  -E "^COPY --from=build|^COPY --from=[0-9]" . 2>/dev/null

# Check if .dockerignore exists and excludes .env / secrets
[ -f .dockerignore ] || echo "WARNING: No .dockerignore found"
cat .dockerignore 2>/dev/null | grep -E "(\.env|\.git|secret|credentials|\.key|\.pem)"

# SSH keys / credentials in build context (before .dockerignore takes effect)
find . -name "*.pem" -o -name "*.key" -o -name "id_rsa" -o -name ".env" 2>/dev/null | \
  grep -v ".git\|node_modules\|venv"
```

### Base Image CVE Analysis

```bash
# Trivy — scan all base images from Dockerfiles
grep -rh "^FROM" . --include="Dockerfile*" 2>/dev/null | \
  awk '{print $2}' | grep -v "^#" | sort -u | \
  while read img; do
    echo "=== Scanning: $img ==="
    trivy image --severity HIGH,CRITICAL --no-progress --exit-code 0 "$img" 2>/dev/null | \
      grep -E "CRITICAL|HIGH" | tail -5
  done

# Grype alternative
grype . 2>/dev/null | grep -E "Critical|High" | head -20

# Check OS base image age (old Ubuntu/Debian = unpatched CVEs)
grep -rn --include="Dockerfile*" \
  -E "^FROM\s+(ubuntu|debian|centos|rhel):[0-9]" . 2>/dev/null | \
  grep -E ":14\.|:16\.|:18\.|:20\.|stretch|buster|jessie|centos:7|centos:6"
```

### Runtime Privilege Checks & Container Escape Patterns

```bash
# Read-only root filesystem (hardening check)
grep -rn --include="docker-compose*.yml" \
  -E "read_only:\s*true" . 2>/dev/null || \
  echo "INFO: No read_only filesystems configured"

# No-new-privileges security opt
grep -rn --include="docker-compose*.yml" \
  -E "no-new-privileges:true" . 2>/dev/null || \
  echo "INFO: no-new-privileges not set — processes may escalate privileges"

# Container escape via proc namespace
docker ps -q 2>/dev/null | while read cid; do
    pid=$(docker inspect "$cid" --format '{{.HostConfig.PidMode}}' 2>/dev/null)
    ipc=$(docker inspect "$cid" --format '{{.HostConfig.IpcMode}}' 2>/dev/null)
    net=$(docker inspect "$cid" --format '{{.HostConfig.NetworkMode}}' 2>/dev/null)
    name=$(docker inspect "$cid" --format '{{.Name}}' 2>/dev/null)
    [ "$pid" = "host" ] && echo "HOST PID NAMESPACE: $name"
    [ "$ipc" = "host" ] && echo "HOST IPC NAMESPACE: $name"
    [ "$net" = "host" ] && echo "HOST NETWORK NAMESPACE: $name"
done

# Ulimits — missing limits allow fork bombs
grep -rn --include="docker-compose*.yml" \
  -E "ulimits:" . 2>/dev/null || \
  echo "INFO: No ulimits configured — containers susceptible to resource exhaustion"
```

## Advanced Patterns

| Vulnerability | Severity | Indicator | Fix |
|---|---|---|---|
| `privileged: true` | CRITICAL | docker-compose or `--privileged` | Remove; use specific capabilities |
| Docker socket mount | CRITICAL | `/var/run/docker.sock` volume | Remove; use rootless Docker or alternatives |
| Root user in container | HIGH | No `USER` directive in Dockerfile | Add `USER nonroot` (UID > 0) |
| Secrets in ENV layer | HIGH | `ENV PASSWORD=` in Dockerfile | Use build secrets: `RUN --mount=type=secret` |
| `:latest` base image | HIGH | `FROM ubuntu:latest` | Pin to `ubuntu:22.04@sha256:...` |
| Host network mode | HIGH | `network_mode: host` | Use named bridge network |
| `SYS_ADMIN` capability | HIGH | `cap_add: SYS_ADMIN` | Audit need; replace with specific cap |
| No `.dockerignore` | MEDIUM | Missing file | Add; exclude `.env`, `.git`, keys |
| Sensitive host mount | HIGH | `/etc:` volume | Remove; inject config via env/secrets |
| No `read_only: true` | MEDIUM | Writable root filesystem | Enable + add tmpfs for writable paths |
| No `no-new-privileges` | MEDIUM | Missing security opt | Add `security_opt: [no-new-privileges:true]` |
| Old OS base image | HIGH | Ubuntu 18.04, Debian stretch | Upgrade to latest LTS |
| Unscanned base image | HIGH | No Trivy/Grype in CI | Add image scanning to pipeline |
