# VIGIL Engine: Smart Contract Audit Orchestrator

**Purpose:** Orchestrate Slither, Aderyn, Echidna, and Foundry for comprehensive Solidity/EVM smart contract auditing. Feeds results into VIGIL's scoring and correlation engines.

## Prerequisites

```bash
# Check toolchain
echo "=== Solidity Audit Tools ==="
slither --version 2>/dev/null && echo "✓ Slither" || echo "✗ Slither (pip install slither-analyzer)"
aderyn --version 2>/dev/null && echo "✓ Aderyn" || echo "✗ Aderyn (cargo install aderyn)"
echidna --version 2>/dev/null && echo "✓ Echidna" || echo "✗ Echidna (brew install echidna or GitHub releases)"
forge --version 2>/dev/null && echo "✓ Foundry/Forge" || echo "✗ Foundry (curl -L https://foundry.paradigm.xyz | bash)"
solc --version 2>/dev/null && echo "✓ solc" || echo "✗ solc (pip install solc-select)"
mythril --version 2>/dev/null && echo "✓ Mythril" || echo "✗ Mythril (pip install mythril — optional)"
```

If no tools are installed, fall back to VIGIL's built-in Solidity grep patterns from `clusters/blockchain.md`. Report as DEGRADED.

## Detection

This engine activates when:
- `*.sol` files exist in the project
- `foundry.toml`, `hardhat.config.js/ts`, `brownie-config.yaml` exist
- `remappings.txt` or `lib/` (Foundry) detected

```bash
find . -name '*.sol' -not -path '*/node_modules/*' -not -path '*/lib/*' -not -path '*/cache/*' | head -20
ls foundry.toml hardhat.config.* brownie-config.yaml truffle-config.js 2>/dev/null
```

## Execution Pipeline

### Step 1: Project Setup (30s)

```bash
# Detect framework
if [ -f foundry.toml ]; then
  echo "Framework: Foundry"
  forge build 2>&1 | tail -5
elif [ -f hardhat.config.js ] || [ -f hardhat.config.ts ]; then
  echo "Framework: Hardhat"
  npx hardhat compile 2>&1 | tail -5
else
  echo "Framework: Unknown — attempting Foundry init"
fi

# Count contracts
find . -name '*.sol' -not -path '*/node_modules/*' -not -path '*/lib/*' -not -path '*/test/*' | wc -l

# Get contract sizes (proxy for complexity)
find . -name '*.sol' -not -path '*/node_modules/*' -not -path '*/lib/*' -not -path '*/test/*' \
  -exec wc -l {} + | sort -rn | head -20
```

### Step 2: Slither Static Analysis (2-5min)

Slither is the primary static analyzer — highest signal-to-noise ratio.

```bash
# Full analysis with JSON output
slither . --json /tmp/vigil-contracts/slither-output.json 2>&1

# If Foundry project, specify framework
slither . --foundry-out-directory out --json /tmp/vigil-contracts/slither-output.json 2>&1

# Parse high-impact detectors
python3 -c "
import json
with open('/tmp/vigil-contracts/slither-output.json') as f:
    data = json.load(f)
for d in data.get('results', {}).get('detectors', []):
    if d['impact'] in ('High', 'Medium'):
        print(f\"{d['impact']:8} {d['check']:30} {d['description'][:100]}\")
"
```

**Key Slither detectors to watch:**

| Detector | VIGIL Severity | Why |
|----------|---------------|-----|
| `reentrancy-eth` | CRITICAL | Direct ETH reentrancy |
| `reentrancy-no-eth` | HIGH | State reentrancy without ETH transfer |
| `arbitrary-send-eth` | CRITICAL | Unprotected ETH transfer |
| `suicidal` | CRITICAL | Unprotected selfdestruct |
| `unprotected-upgrade` | CRITICAL | Proxy upgrade without auth |
| `controlled-delegatecall` | CRITICAL | User-controlled delegatecall |
| `unchecked-transfer` | HIGH | ERC20 transfer return not checked |
| `locked-ether` | HIGH | Contract receives ETH but can't send |
| `tx-origin` | HIGH | tx.origin used for auth |
| `divide-before-multiply` | MEDIUM | Precision loss |
| `missing-zero-check` | MEDIUM | No zero-address validation |

### Step 3: Aderyn Analysis (1-2min)

Aderyn provides additional Rust-based detection with low false positives.

```bash
# Run Aderyn
aderyn . --output /tmp/vigil-contracts/aderyn-output.json 2>&1

# Aderyn focuses on:
# - Centralization risks
# - Unsafe casting
# - Missing events
# - Storage collision in upgradeable contracts
```

### Step 4: Echidna Fuzzing (5-10min, siege mode only)

Only run in `/vigil siege` — too slow for audit mode.

```bash
# Check for existing Echidna config
ls echidna.yaml echidna-config.yaml 2>/dev/null

# Run fuzzer on main contract
echidna . --contract {MainContract} --config echidna.yaml \
  --test-mode assertion --format json 2>&1 | tee /tmp/vigil-contracts/echidna-output.json

# If no config exists, create minimal one
cat > /tmp/vigil-contracts/echidna-default.yaml << 'ECHIDNA'
testLimit: 50000
shrinkLimit: 5000
seqLen: 100
deployer: "0x10000"
sender: ["0x20000", "0x30000"]
ECHIDNA
```

### Step 5: Manual Pattern Checks (1-2min)

VIGIL's own Solidity patterns (complement tool output):

```bash
# Access control patterns
grep -rn --include='*.sol' -E 'onlyOwner|onlyRole|require\(msg\.sender|auth|access' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# Reentrancy guards
grep -rn --include='*.sol' -E 'nonReentrant|ReentrancyGuard|_status|_locked' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# External calls before state changes (CEI violation)
grep -rn --include='*.sol' -E '\.(call|transfer|send)\(' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# Oracle usage (price manipulation risk)
grep -rn --include='*.sol' -E 'latestRoundData|getPrice|oracle|chainlink|twap' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# Flash loan interaction
grep -rn --include='*.sol' -E 'flashLoan|flashMint|IFlash|IERC3156' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# Proxy patterns (upgrade risks)
grep -rn --include='*.sol' -E 'delegatecall|upgradeTo|initializ|_disableInitializers|ERC1967' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null

# Unchecked arithmetic (Solidity <0.8)
grep -rn --include='*.sol' -E 'pragma solidity.*0\.[4-7]\.' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null
```

### Step 6: Result Correlation

Map tool output to VIGIL finding IDs:

| Source | VIGIL ID Range | Mapping |
|--------|---------------|---------|
| Slither High/Medium | VIGIL-CHAIN-0xx | Direct severity mapping |
| Aderyn findings | VIGIL-CHAIN-1xx | Cross-reference with Slither (deduplicate) |
| Echidna failures | VIGIL-CHAIN-2xx | Property violations → CRITICAL |
| VIGIL patterns | VIGIL-CHAIN-3xx | Manual pattern matches |

**Cross-tool correlation:** If Slither AND Aderyn flag the same function → increase confidence, keep higher severity. If Echidna confirms a Slither finding with a concrete counterexample → escalate to CRITICAL.

## DeFi-Specific Checks

### ERC-4626 Vault Analysis

```bash
grep -rn --include='*.sol' -E 'ERC4626|deposit|withdraw|redeem|convertToShares|convertToAssets' . \
  --exclude-dir={node_modules,lib,cache,test} 2>/dev/null
```

Check for: inflation attack, rounding direction (always round against user), first depositor manipulation.

### Oracle Price Manipulation

1. Identify all price oracle calls
2. Check if TWAP or spot price
3. Check manipulation cost vs TVL ratio
4. Flag if manipulation cost < 10% of potential profit

### Flash Loan Attack Surface

1. Find all functions callable in a single transaction
2. Check if state changes are protected against atomic execution
3. Flag functions that read and act on balances in the same call

## Output Integration

Feed results into standard VIGIL scoring via `engines/scoring.md`:
- Blockchain cluster weight: 15% (when applicable)
- CRITICAL: 25 pts penalty (reentrancy, arbitrary send, unprotected upgrade)
- HIGH: 10 pts penalty (unchecked transfer, tx.origin, oracle without TWAP)
- MEDIUM: 4 pts penalty (missing zero check, divide-before-multiply)

All findings also map to:
- `compliance-maps/owasp-top10.md` (A01 access control, A03 injection via oracle)
- `domains/defi-deep.md` and `domains/solidity-deep.md` for siege-mode deep analysis
