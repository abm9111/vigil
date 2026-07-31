# VIGIL Cluster: Blockchain & Smart Contracts

**Covers:** Solidity, Vyper, Move, Rust (Solana/Soroban), smart contract security
**Weight:** 8% (authoritative source: engines/scoring.md; N/A if no contracts detected)
**ID prefix:** VIGIL-CHAIN

## Detection

This cluster is N/A if none of these exist:
- Files: `*.sol`, `*.vy`, `*.move`, `*.cairo`
- Directories: `contracts/`, `src/` with Solidity
- Config: `hardhat.config.*`, `foundry.toml`, `truffle-config.*`, `brownie-config.*`, `Move.toml`, `Anchor.toml`
- Dependencies: `@openzeppelin`, `solmate`, `forge-std`

```bash
# Detect blockchain presence
find . -name '*.sol' -o -name '*.vy' -o -name '*.move' -o -name '*.cairo' 2>/dev/null | \
  grep -v node_modules | grep -v cache | head -5
ls hardhat.config.* foundry.toml truffle-config.* brownie-config.* Move.toml Anchor.toml 2>/dev/null
```

## Deterministic Tools

### Solidity / EVM

```bash
# Slither (if installed — best Solidity static analyzer)
slither . --json .vigil/slither-results.json 2>&1

# Semgrep with Solidity rulesets
semgrep scan --config p/solidity --config p/decurity-audit --config p/trailofbits \
  --metrics=off --sarif --output .vigil/semgrep/raw/solidity.sarif \
  --severity MEDIUM --severity HIGH --severity CRITICAL . 2>&1

# Aderyn (Rust-based, fast)
aderyn . --output .vigil/aderyn-report.json 2>&1 || true

# Solhint (linter)
npx solhint 'contracts/**/*.sol' 2>&1
```

### Pattern Scans (No Tools Required)

```bash
# Reentrancy: external call before state change
grep -rn --include='*.sol' -E '\.(call|send|transfer)\s*\(' . --exclude-dir={node_modules,cache} 2>/dev/null

# Unchecked return values
grep -rn --include='*.sol' -E '\.call\{' . --exclude-dir={node_modules,cache} 2>/dev/null | \
  grep -v 'require\|assert\|if'

# tx.origin usage (phishing vulnerability)
grep -rn --include='*.sol' 'tx\.origin' . --exclude-dir={node_modules,cache} 2>/dev/null

# Floating pragma (version not pinned)
grep -rn --include='*.sol' 'pragma solidity \^' . --exclude-dir={node_modules,cache} 2>/dev/null

# Selfdestruct (deprecated, dangerous)
grep -rn --include='*.sol' 'selfdestruct\|suicide' . --exclude-dir={node_modules,cache} 2>/dev/null

# Delegatecall (proxy pattern — verify safety)
grep -rn --include='*.sol' 'delegatecall' . --exclude-dir={node_modules,cache} 2>/dev/null

# Uninitialized storage pointers
grep -rn --include='*.sol' -E 'storage\s+\w+;' . --exclude-dir={node_modules,cache} 2>/dev/null

# Block.timestamp dependency
grep -rn --include='*.sol' 'block\.timestamp' . --exclude-dir={node_modules,cache} 2>/dev/null

# Missing access control
grep -rn --include='*.sol' -E 'function\s+\w+.*public|function\s+\w+.*external' . \
  --exclude-dir={node_modules,cache} 2>/dev/null | grep -v 'onlyOwner\|onlyRole\|require.*msg\.sender\|modifier'

# Arbitrary ETH send
grep -rn --include='*.sol' -E '\.transfer\(|\.send\(|\.call\{value' . --exclude-dir={node_modules,cache} 2>/dev/null
```

### Vyper

```bash
# Vyper compiler with security warnings
vyper -f abi . 2>&1 | grep -i 'warning\|error' | head -20

# Pattern: raw_call (similar risk to delegatecall)
grep -rn --include='*.vy' 'raw_call\|send\|selfdestruct' . 2>/dev/null
```

### Move (Aptos/Sui)

```bash
# Move Prover (formal verification)
aptos move prove 2>&1 || sui move prove 2>&1 || true

# Pattern: public entry functions without access control
grep -rn --include='*.move' 'public entry fun\|public fun' . 2>/dev/null
```

### Solana (Rust/Anchor)

```bash
# Anchor build + IDL check
anchor build 2>&1 | tail -20

# Missing signer checks
grep -rn --include='*.rs' -E '#\[account\(' . --exclude-dir={target} 2>/dev/null | grep -v 'has_one\|constraint\|signer'

# Unchecked account ownership
grep -rn --include='*.rs' 'AccountInfo' . --exclude-dir={target} 2>/dev/null | \
  grep -v 'check_owner\|owner.*==\|Program::id'
```

## Finding Patterns

### Reentrancy (VIGIL-CHAIN-0xx)

| Pattern | Severity |
|---------|----------|
| External call before state update (classic reentrancy) | CRITICAL |
| Cross-function reentrancy (shared state) | CRITICAL |
| Read-only reentrancy (view function manipulation) | HIGH |
| Missing reentrancy guard on ETH-receiving function | HIGH |

### Access Control (VIGIL-CHAIN-1xx)

| Pattern | Severity |
|---------|----------|
| Public/external function missing access control | CRITICAL |
| tx.origin for authentication | CRITICAL |
| Missing role validation on admin function | HIGH |
| Default admin not set in constructor | MEDIUM |
| Centralization risk (single owner controls critical) | MEDIUM |

### Value Handling (VIGIL-CHAIN-2xx)

| Pattern | Severity |
|---------|----------|
| Unchecked return value on low-level call | HIGH |
| Integer overflow/underflow (pre-0.8.0 Solidity) | CRITICAL |
| Precision loss in division before multiplication | HIGH |
| Flash loan attack surface | HIGH |
| Arbitrary ETH drain (unprotected withdrawal) | CRITICAL |

### Contract Design (VIGIL-CHAIN-3xx)

| Pattern | Severity |
|---------|----------|
| Floating pragma (not pinned to specific version) | MEDIUM |
| Use of selfdestruct | HIGH |
| Uninitialized storage pointer | CRITICAL |
| Block.timestamp dependency for critical logic | MEDIUM |
| Front-running vulnerability (no commit-reveal) | HIGH |
| Missing event emissions for state changes | LOW |
| Upgradeable proxy without storage gap | HIGH |

### Oracle & External Dependencies (VIGIL-CHAIN-4xx)

| Pattern | Severity |
|---------|----------|
| Stale oracle price (no freshness check) | CRITICAL |
| Single oracle dependency (no fallback) | HIGH |
| Missing slippage protection | HIGH |
| Hardcoded addresses (no registry/proxy) | MEDIUM |

## AI Reasoning Section

1. **Attack surface:** Which functions are external/public? Can an attacker reach them without auth?
2. **Value flow:** Trace where ETH/tokens move. Any path from user input to transfer without validation?
3. **State consistency:** Are there multi-step operations that can be interrupted (reentrancy, front-running)?
4. **Upgrade safety:** If upgradeable, can the admin rug-pull? Are there timelocks?
5. **Economic attacks:** Can flash loans or price manipulation exploit any function?
6. **Cross-contract risk:** Which external contracts are called? What if they're malicious?
