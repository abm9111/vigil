# /vigil-recon — Reconnaissance Pipeline

**Trigger:** `/vigil-recon [--target domain.com] [--scope oss|webapp|api] [--depth quick|standard|deep]`
**Time:** 2-15 minutes depending on depth
**Purpose:** External reconnaissance that feeds targets and attack surface data into the VIGIL audit pipeline

## Tool Chain

### Required (install if missing)

```bash
# Check toolchain
for tool in subfinder dnsx httpx katana nuclei semgrep ffuf; do
  command -v $tool >/dev/null 2>&1 && echo "✓ $tool" || echo "✗ $tool — MISSING"
done

# Install missing (Go-based tools)
# subfinder: go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
# dnsx: go install -v github.com/projectdiscovery/dnsx/cmd/dnsx@latest
# httpx: go install -v github.com/projectdiscovery/httpx/cmd/httpx@latest
# katana: go install -v github.com/projectdiscovery/katana/cmd/katana@latest
# nuclei: go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
# ffuf: go install -v github.com/ffuf/ffuf/v2@latest
# semgrep: pip install semgrep
```

### Optional (enhance results)

```bash
for tool in gau waybackurls dnsReaper subzy trufflehog; do
  command -v $tool >/dev/null 2>&1 && echo "✓ $tool" || echo "✗ $tool — optional"
done
```

## Execution by Depth

### Quick Recon (2-3 min)

Target: Known domain, need fast surface scan.

```bash
# 1. Subdomain enumeration (passive only)
subfinder -d {domain} -silent -o /tmp/vigil-recon/subs.txt 2>/dev/null
wc -l /tmp/vigil-recon/subs.txt

# 2. Resolve live hosts
cat /tmp/vigil-recon/subs.txt | dnsx -silent -o /tmp/vigil-recon/resolved.txt 2>/dev/null

# 3. HTTP probe (title, status, tech detect)
cat /tmp/vigil-recon/resolved.txt | httpx -silent -title -status-code -tech-detect \
  -o /tmp/vigil-recon/live.txt 2>/dev/null

# 4. Quick nuclei scan (critical/high only)
nuclei -l /tmp/vigil-recon/live.txt -severity critical,high -silent \
  -o /tmp/vigil-recon/nuclei-quick.txt 2>/dev/null
```

### Standard Recon (5-8 min)

Target: Bounty program, need thorough surface.

```bash
mkdir -p /tmp/vigil-recon/{domain}

# 1. Subdomain enumeration (passive + brute)
subfinder -d {domain} -all -silent -o /tmp/vigil-recon/{domain}/subs-passive.txt
# Optional: brute force common subdomains
# ffuf -w /path/to/subdomains-top1million-5000.txt -u "https://FUZZ.{domain}" -mc 200,301,302,403 -o /tmp/vigil-recon/{domain}/subs-brute.json

# Merge and deduplicate
sort -u /tmp/vigil-recon/{domain}/subs-passive.txt > /tmp/vigil-recon/{domain}/subs-all.txt

# 2. DNS resolution + record types
cat /tmp/vigil-recon/{domain}/subs-all.txt | dnsx -silent -a -aaaa -cname -mx -ns \
  -resp -o /tmp/vigil-recon/{domain}/dns.txt

# 3. Dangling CNAME check (subdomain takeover)
cat /tmp/vigil-recon/{domain}/dns.txt | grep CNAME | while read line; do
  cname=$(echo $line | awk '{print $NF}')
  host $cname 2>/dev/null | grep -q "NXDOMAIN" && echo "TAKEOVER CANDIDATE: $line"
done > /tmp/vigil-recon/{domain}/takeover-candidates.txt

# 4. HTTP probe with full fingerprinting
cat /tmp/vigil-recon/{domain}/subs-all.txt | httpx -silent \
  -title -status-code -tech-detect -content-length -web-server -cdn \
  -follow-redirects -o /tmp/vigil-recon/{domain}/live.txt

# 5. URL discovery (crawl + archive)
cat /tmp/vigil-recon/{domain}/live.txt | awk '{print $1}' | katana -silent -d 3 \
  -o /tmp/vigil-recon/{domain}/urls-crawl.txt 2>/dev/null
# gau {domain} --threads 5 --o /tmp/vigil-recon/{domain}/urls-archive.txt 2>/dev/null

# 6. Nuclei scan (all severities + interesting templates)
nuclei -l /tmp/vigil-recon/{domain}/live.txt -severity critical,high,medium \
  -t cves/ -t exposures/ -t misconfiguration/ -t takeovers/ \
  -silent -o /tmp/vigil-recon/{domain}/nuclei.txt 2>/dev/null

# 7. CORS check on all live endpoints
cat /tmp/vigil-recon/{domain}/live.txt | awk '{print $1}' | while read url; do
  resp=$(curl -sk -H "Origin: https://evil.com" -I "$url" 2>/dev/null)
  echo "$resp" | grep -qi "access-control-allow-origin.*evil\|access-control-allow-origin.*\*" && \
    echo "CORS VULN: $url"
  echo "$resp" | grep -qi "access-control-allow-credentials.*true" && \
    echo "CORS+CREDS: $url"
done > /tmp/vigil-recon/{domain}/cors.txt
```

### Deep Recon (10-15 min)

Target: High-value bounty target, need exhaustive coverage.

Everything in Standard, plus:

```bash
# 8. JavaScript file extraction and analysis
cat /tmp/vigil-recon/{domain}/urls-crawl.txt | grep -iE '\.js$' | sort -u \
  > /tmp/vigil-recon/{domain}/js-files.txt

# Extract API endpoints, secrets, and sensitive paths from JS
while read jsurl; do
  curl -sk "$jsurl" 2>/dev/null | grep -oE '(api|v[0-9]+)/[a-zA-Z0-9_/]+' | sort -u
done < /tmp/vigil-recon/{domain}/js-files.txt > /tmp/vigil-recon/{domain}/api-endpoints.txt

# 9. Parameter discovery
cat /tmp/vigil-recon/{domain}/urls-crawl.txt | grep '?' | \
  awk -F'?' '{print $2}' | tr '&' '\n' | cut -d'=' -f1 | sort -u \
  > /tmp/vigil-recon/{domain}/params.txt

# 10. Technology fingerprinting
httpx -l /tmp/vigil-recon/{domain}/subs-all.txt -silent -tech-detect -json \
  -o /tmp/vigil-recon/{domain}/tech.json 2>/dev/null

# 11. Full nuclei (all templates including info)
nuclei -l /tmp/vigil-recon/{domain}/live.txt -silent \
  -o /tmp/vigil-recon/{domain}/nuclei-full.txt 2>/dev/null

# 12. Secret scanning in discovered JS/configs
trufflehog filesystem /tmp/vigil-recon/{domain}/ --only-verified --json \
  2>/dev/null > /tmp/vigil-recon/{domain}/secrets.json
```

## OSS Scope (Source Code Recon)

For open-source targets, skip network recon and go straight to code:

```bash
# Clone the target (shallow for speed)
git clone --depth=50 {repo_url} /tmp/vigil-recon/oss/{project}

# Get project metadata
cd /tmp/vigil-recon/oss/{project}
git log --oneline -20
wc -l $(find . -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.go' | grep -v node_modules | grep -v .venv)

# Run VIGIL audit on the cloned source
# → Hand off to /vigil audit /tmp/vigil-recon/oss/{project}
```

## Output: Recon Summary → VIGIL Handoff

```
╔══════════════════════════════════════════════════════════╗
║  VIGIL Recon — {domain} ({depth} scan)                  ║
╚══════════════════════════════════════════════════════════╝

Surface:
  Subdomains: {N} found, {M} live
  URLs: {N} crawled, {M} from archives
  JS files: {N} analyzed
  Parameters: {N} unique
  API endpoints: {N} discovered

Immediate Findings:
  🔴 {nuclei_critical} critical (Nuclei)
  🟠 {nuclei_high} high
  🟡 {nuclei_medium} medium
  ⚪ {cors_vulns} CORS issues
  ⚪ {takeover_candidates} subdomain takeover candidates

Technology Stack:
  {tech fingerprint summary}

Files saved: /tmp/vigil-recon/{domain}/
  subs-all.txt    — {N} subdomains
  live.txt        — {M} live hosts
  nuclei.txt      — {K} findings
  cors.txt        — {L} CORS issues
  api-endpoints.txt — {P} API paths

Next: /vigil audit --target {interesting_endpoint}
      /vigil-bounty --finding {nuclei_finding_id}
```

## Rules

1. **NEVER scan outside defined scope** — only targets in the bounty program's asset list
2. **Respect rate limits** — use `-rate-limit 10` flag on nuclei/httpx for production targets
3. **No active exploitation** — recon ONLY identifies surface, does not exploit
4. **Log everything** — all tool output to `/tmp/vigil-recon/{domain}/` for audit trail
5. **Check program scope** before each scan — some programs exclude specific subdomains
6. **Use VPN/proxy** for non-OSS targets — never scan from home IP on production systems
