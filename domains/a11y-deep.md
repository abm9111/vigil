# VIGIL Domain Detail: Accessibility Deep-Dive

**Parent cluster:** frontend
**Loaded in:** siege mode, or --only frontend --deep

## Deep Checks

### WCAG 2.1 AA Compliance Scan

```bash
# axe-core CLI audit
npx axe --dir ./src --tags wcag2a,wcag2aa,wcag21aa --reporter json > /tmp/axe-report.json

# lighthouse accessibility audit
npx lighthouse http://localhost:3000 --only-categories=accessibility --output=json --output-path=/tmp/lh-a11y.json

# pa11y batch check
npx pa11y-ci --sitemap http://localhost:3000/sitemap.xml --reporter json

# HTML validator (W3C)
npx html-validate "src/**/*.html" "src/**/*.tsx"
```

### Semantic HTML Audit

```bash
# find heading hierarchy violations (h1→h3 skips, multiple h1)
grep -rn "<h[1-6]" src/ --include="*.tsx" --include="*.html" | sort

# detect div-soup: interactive elements not using semantic tags
grep -rn "onClick.*<div\|<span.*onClick" src/ --include="*.tsx"

# missing landmark roles
grep -rn "<div\|<section\|<aside" src/ --include="*.tsx" | grep -v "role="

# list misuse (ul/ol for non-list content)
grep -rn "<ul\|<ol" src/ --include="*.tsx" | grep -v "aria-label\|role="
```

### ARIA Patterns

```bash
# invalid aria-* attribute values
grep -rEn 'aria-[a-z]+="[^"]*"' src/ | grep -v "aria-label\|aria-labelledby\|aria-describedby\|aria-hidden\|aria-expanded\|aria-controls\|aria-current\|aria-live\|aria-atomic\|aria-busy\|aria-disabled\|aria-required\|aria-selected\|aria-checked\|aria-haspopup\|aria-owns\|aria-roledescription"

# redundant ARIA (role matches element semantic)
grep -rn 'role="button".*<button\|role="link".*<a\|role="heading".*<h[1-6]' src/

# aria-label on non-interactive elements
grep -rn 'aria-label=.*<div\|aria-label=.*<span\|aria-label=.*<p>' src/

# live region audit
grep -rn "aria-live" src/ --include="*.tsx"
```

### Focus Management

```bash
# tabIndex > 0 (breaks natural tab order)
grep -rn "tabIndex=[1-9]\|tabindex=[1-9]" src/ --include="*.tsx" --include="*.html"

# focus trap in modals/dialogs
grep -rn "Modal\|Dialog\|Drawer\|Sheet" src/ --include="*.tsx" | xargs grep -l "focusTrap\|focus-trap\|useFocusTrap" 2>/dev/null

# missing :focus-visible styles
grep -rn ":focus" src/ --include="*.css" --include="*.scss" | grep -v ":focus-visible"

# autoFocus misuse
grep -rn "autoFocus\|autofocus" src/ --include="*.tsx"
```

### Color Contrast Analysis

```bash
# extract color tokens for manual contrast check
grep -rEn '#[0-9a-fA-F]{3,6}|rgb\(|rgba\(|hsl\(' src/ --include="*.css" --include="*.scss" | sort -u

# check Tailwind color usage against WCAG ratios
grep -rn "text-gray-[0-9]\|text-slate-[0-9]" src/ --include="*.tsx" | grep -v "text-gray-[789]\|text-gray-9\|text-slate-[789]\|text-slate-9"
```

### Motion and Animation Preferences

```bash
# missing prefers-reduced-motion media query
grep -rn "@keyframes\|animation:\|transition:" src/ --include="*.css" --include="*.scss" | wc -l
grep -rn "prefers-reduced-motion" src/ --include="*.css" --include="*.scss" | wc -l

# JS animations bypassing CSS media query
grep -rn "useAnimation\|framer-motion\|gsap\|anime(" src/ --include="*.tsx" | xargs grep -l "prefersReducedMotion\|useReducedMotion" 2>/dev/null
```

### Form Labeling

```bash
# inputs without associated label
grep -rn "<input\|<select\|<textarea" src/ --include="*.tsx" | grep -v "aria-label\|aria-labelledby\|id="

# label for= not matching input id=
grep -rEn 'htmlFor="[^"]*"' src/ --include="*.tsx"

# required fields without aria-required
grep -rn "required\b" src/ --include="*.tsx" | grep -v "aria-required"

# error messages not linked to inputs
grep -rn "error\|invalid\|helperText" src/ --include="*.tsx" | grep -v "aria-describedby\|aria-errormessage"
```

### Keyboard Navigation

```bash
# custom dropdown/select without keyboard handler
grep -rn "dropdown\|Dropdown\|Popover\|Combobox" src/ --include="*.tsx" | xargs grep -L "onKeyDown\|onKeyUp\|onKeyPress" 2>/dev/null

# click-only handlers (no keyboard equivalent)
grep -rn "onClick=" src/ --include="*.tsx" | grep -v "onKeyDown\|onKeyUp\|role=" | head -30

# skip-to-main-content link
grep -rn "skip\|skip-to\|skip-nav\|skipLink" src/ --include="*.tsx"
```

### Touch Targets

```bash
# small touch targets (< 44x44px minimum)
grep -rEn 'w-[1-9]\b.*h-[1-9]\b|h-[1-9]\b.*w-[1-9]\b|width.*[0-9]{1,2}px.*height.*[0-9]{1,2}px' src/ --include="*.tsx" --include="*.css"

# icon buttons without text alternative
grep -rn "<IconButton\|<button.*icon\|icon.*<button" src/ --include="*.tsx" | grep -v "aria-label\|title="
```

## Advanced Patterns

| Pattern | Severity | WCAG Criterion |
|---------|----------|----------------|
| Missing skip navigation link | Medium | 2.4.1 Bypass Blocks |
| Focus not visible on all interactive elements | High | 2.4.7 Focus Visible |
| Color alone conveys meaning | High | 1.4.1 Use of Color |
| Text contrast ratio < 4.5:1 (normal) or < 3:1 (large) | High | 1.4.3 Contrast |
| Video without captions | High | 1.2.2 Captions |
| Image without alt text | High | 1.1.1 Non-text Content |
| Tooltip not keyboard accessible | Medium | 2.1.1 Keyboard |
| Auto-playing media with sound | High | 1.4.2 Audio Control |
| Timeout without warning | Medium | 2.2.1 Timing Adjustable |
| Content reflow broken at 320px | Medium | 1.4.10 Reflow |
| Dynamic content not announced | High | 4.1.3 Status Messages |
| Form error only indicated by color | High | 3.3.1 Error Identification |
