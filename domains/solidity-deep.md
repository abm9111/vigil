# VIGIL Domain Detail: Solidity & EVM Security

**Parent cluster:** Blockchain
**Loaded in:** siege mode, or `--only blockchain --deep`

## Deep Checks

### Reentrancy Detection

```bash
# Find all external calls
grep -rn --include='*.sol' -E '\.(call|delegatecall|staticcall|send|transfer)\s*[\({]' . \
  --exclude-dir={node_modules,cache,artifacts} 2>/dev/null

# Check if state changes happen after external calls (classic reentrancy)
# Look for pattern: external_call() followed by state = value
grep -rn --include='*.sol' -B5 -A10 '\.call\{' . --exclude-dir={node_modules,cache} 2>/dev/null | \
  grep -E 'balances\[|\.transfer\(|mapping.*=|state.*='
```

### Flash Loan Attack Surface

```bash
# Functions that read price/balance and make decisions
grep -rn --include='*.sol' -E 'balanceOf|getReserves|latestRoundData|getPrice|totalSupply' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# Check for same-transaction price manipulation protection
grep -rn --include='*.sol' -E 'TWAP|timeWeightedAverage|_blockTimestamp|lastUpdate' . \
  --exclude-dir={node_modules,cache} 2>/dev/null
```

### Proxy & Upgrade Patterns

```bash
# Detect upgrade patterns
grep -rn --include='*.sol' -E 'UUPSUpgradeable|TransparentUpgradeableProxy|initializer|__gap' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# Missing storage gap in upgradeable contracts
grep -rn --include='*.sol' -E 'contract.*Upgradeable|contract.*Proxy' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# Check for initialize() without initializer modifier
grep -rn --include='*.sol' 'function initialize' . --exclude-dir={node_modules,cache} 2>/dev/null | \
  grep -v 'initializer'
```

### Gas Optimization Issues

```bash
# Unbounded loops (DoS via gas)
grep -rn --include='*.sol' -E 'for\s*\(.*\.length|while\s*\(' . --exclude-dir={node_modules,cache} 2>/dev/null

# Storage reads in loops
grep -rn --include='*.sol' -B2 -A5 'for\s*\(' . --exclude-dir={node_modules,cache} 2>/dev/null | \
  grep -E 'storage|mapping|state'
```

## Advanced Patterns

| Pattern | Severity | Detection |
|---------|----------|-----------|
| Unprotected `initialize()` | CRITICAL | No `initializer` modifier on init function |
| Missing storage gap `__gap` | HIGH | Upgradeable contract without `uint256[50] __gap` |
| Unchecked `ecrecover` | CRITICAL | `ecrecover` without checking return != address(0) |
| Signature malleability | HIGH | Using `ecrecover` without EIP-712 |
| Oracle price with no staleness check | CRITICAL | `latestRoundData()` without checking `updatedAt` |
| Unbounded array iteration | HIGH | `for(i=0; i<array.length; i++)` with user-controlled array |
| Front-runnable function | HIGH | State-changing function without commit-reveal or private mempool |
| Missing event on state change | MEDIUM | `transfer`, `approve`, admin functions without `emit` |
| Hardcoded chain ID | MEDIUM | `block.chainid == 1` instead of parameter |
| Fallback/receive without limit | MEDIUM | `receive() external payable {}` with no checks |
