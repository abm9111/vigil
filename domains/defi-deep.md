# VIGIL Domain Detail: DeFi Protocol Security

**Parent cluster:** Blockchain
**Loaded in:** siege mode, or `--only blockchain --deep`

## Deep Checks

### Price Manipulation

```bash
# Spot price usage (vulnerable to flash loans)
grep -rn --include='*.sol' -E 'getReserves|balanceOf.*pair|slot0|sqrtPriceX96' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# TWAP protection check
grep -rn --include='*.sol' -E 'observe|consult|TWAP|OracleLibrary' . \
  --exclude-dir={node_modules,cache} 2>/dev/null
```

### Token Integration Risks

```bash
# ERC-20 edge cases
grep -rn --include='*.sol' -E 'transfer\(|transferFrom\(' . --exclude-dir={node_modules,cache} 2>/dev/null

# Fee-on-transfer handling
grep -rn --include='*.sol' -E 'balanceBefore|balanceAfter|actualAmount' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# Rebasing token handling
grep -rn --include='*.sol' -E 'shares|wrapperToken|underlying' . \
  --exclude-dir={node_modules,cache} 2>/dev/null
```

### MEV & Front-Running

```bash
# Slippage protection
grep -rn --include='*.sol' -E 'minAmount|amountOutMin|deadline|slippage' . \
  --exclude-dir={node_modules,cache} 2>/dev/null

# Sandwich attack surface
grep -rn --include='*.sol' -E 'swap\(|exactInput\(|exactOutput\(' . \
  --exclude-dir={node_modules,cache} 2>/dev/null
```

## Advanced Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| Spot price for valuation | CRITICAL | Using AMM reserves/balances for pricing — flash loan manipulable |
| Missing slippage parameter | CRITICAL | Swap function with no `minAmountOut` — sandwich attackable |
| No deadline on swap | HIGH | Transaction can be delayed and executed at worse price |
| Fee-on-transfer not handled | HIGH | Token with transfer fee causes accounting mismatch |
| Rebasing token breaks accounting | HIGH | Stored balance != actual balance after rebase |
| Hardcoded token addresses | MEDIUM | Cannot adapt to token migrations |
| Missing return value check on `transfer` | HIGH | Some ERC-20s return false instead of reverting |
| Approval race condition | MEDIUM | `approve()` without first setting to 0 |
| Infinite approval pattern | MEDIUM | `approve(type(uint256).max)` — permanent exposure |
| Flashloan callback unprotected | CRITICAL | Callback function callable by anyone, not just pool |
