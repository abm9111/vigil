# VIGIL Cluster: Frontend & Mobile

**Covers:** React/Vue/Angular, accessibility, i18n, mobile, bundle size, rendering
**Weight:** 10% (excluded if no frontend detected)
**ID prefix:** VIGIL-FE

## Detection

This cluster is N/A if none of these exist:
- `package.json` with react/vue/angular/svelte in dependencies
- Files matching `*.jsx`, `*.tsx`, `*.vue`, `*.svelte`
- `next.config.*`, `nuxt.config.*`, `vite.config.*`

## Deterministic Tools

### TypeScript/JavaScript Quality

```bash
# Type checking
npx tsc --noEmit 2>&1

# Lint
npx eslint . --ext .js,.jsx,.ts,.tsx --format compact 2>&1

# Bundle size analysis (if build exists)
npx next build 2>&1 | grep -A 20 'Route' || true
```

### Accessibility (a11y)

```bash
# ESLint a11y plugin (if configured)
npx eslint . --rule '{"jsx-a11y/alt-text": "error", "jsx-a11y/aria-props": "error"}' --format compact 2>&1

# Manual pattern checks
grep -rn --include='*.tsx' --include='*.jsx' -E '<img[^>]*(?!alt=)[^>]*/?>' . \
  --exclude-dir={node_modules,.git,dist,build} 2>/dev/null

# Missing aria labels on interactive elements
grep -rn --include='*.tsx' --include='*.jsx' \
  -E '<(button|a|input|select|textarea)[^>]*(?!aria-label)[^>]*>' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null | head -20

# Color contrast (check for hardcoded colors without theme)
grep -rn --include='*.tsx' --include='*.jsx' --include='*.css' \
  -E 'color:\s*#[0-9a-fA-F]{3,6}|color:\s*rgb' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null | wc -l
```

### Security (Frontend-Specific)

```bash
# dangerouslySetInnerHTML (XSS vector)
grep -rn --include='*.tsx' --include='*.jsx' 'dangerouslySetInnerHTML' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null

# innerHTML usage
grep -rn --include='*.ts' --include='*.js' '\.innerHTML\s*=' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null

# localStorage for sensitive data
grep -rn --include='*.ts' --include='*.tsx' --include='*.js' --include='*.jsx' \
  -E 'localStorage\.(set|get)Item.*\b(token|key|secret|password|auth)\b' . \
  --exclude-dir={node_modules,.git,dist} 2>/dev/null

# eval usage
grep -rn --include='*.ts' --include='*.js' --include='*.tsx' --include='*.jsx' \
  '\beval\s*(' . --exclude-dir={node_modules,.git,dist} 2>/dev/null
```

### Performance

```bash
# Large dependencies check
npx depcheck --json 2>/dev/null | head -40

# Unused dependencies
npx depcheck 2>&1 | head -20

# Image optimization
find . -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.gif' | \
  grep -v node_modules | xargs -I {} stat -f '%z %N' {} 2>/dev/null | \
  awk '$1 > 500000 {print "LARGE:", $0}' | head -10
```

## Finding Patterns

### Accessibility (VIGIL-FE-0xx)

| Pattern | Severity |
|---------|----------|
| Images without alt text | MEDIUM |
| Interactive elements without aria-label | MEDIUM |
| No skip navigation link | LOW |
| No focus management on route change | LOW |
| Insufficient color contrast (manual review) | MEDIUM |
| No keyboard navigation support | MEDIUM |

### Security (VIGIL-FE-1xx)

| Pattern | Severity |
|---------|----------|
| dangerouslySetInnerHTML with user input | CRITICAL |
| innerHTML with dynamic content | HIGH |
| Sensitive data in localStorage | HIGH |
| API keys in client-side code | CRITICAL |
| eval() usage | HIGH |
| Missing CSP headers | MEDIUM |

### Performance (VIGIL-FE-2xx)

| Pattern | Severity |
|---------|----------|
| Bundle size >500KB (JS) | MEDIUM |
| Images >500KB without optimization | MEDIUM |
| No lazy loading for below-fold content | LOW |
| No code splitting | MEDIUM |
| Unused dependencies (>5) | LOW |
| Render-blocking resources | MEDIUM |

### Rendering & State (VIGIL-FE-3xx)

| Pattern | Severity |
|---------|----------|
| useEffect without dependency array | MEDIUM |
| State mutation (direct object modification) | HIGH |
| Props drilling >3 levels deep | LOW |
| No error boundaries | MEDIUM |
| Memory leak (missing cleanup in useEffect) | HIGH |

## AI Reasoning Section

1. **UX audit:** Is the frontend accessible? Can keyboard-only users navigate it?
2. **Security posture:** What sensitive data is in the client bundle? What can be moved server-side?
3. **Performance budget:** What's the total JS bundle size? Any obvious optimization wins?
4. **State management:** Is state handled consistently? Any prop drilling or unnecessary re-renders?
5. **Mobile readiness:** Does the app work on mobile viewports? Any responsive design gaps?
