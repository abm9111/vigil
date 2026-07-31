# VIGIL Domain Detail: Bundle Optimization Deep-Dive

**Parent cluster:** frontend
**Loaded in:** siege mode, or --only frontend --deep

## Deep Checks

### Tree Shaking Effectiveness

```bash
# build with bundle analysis (webpack)
npx webpack --config webpack.config.js --profile --json > /tmp/webpack-stats.json
npx webpack-bundle-analyzer /tmp/webpack-stats.json --mode static --report /tmp/bundle-report.html

# build with bundle analysis (vite)
npx vite build --mode analyze
npx rollup-plugin-visualizer  # if configured

# check if barrel files defeat tree shaking
grep -rn "export \* from\|export {.*} from" src/ --include="*.ts" --include="*.tsx" | grep "index\." | head -20

# named imports vs namespace imports
grep -rn "import \* as " src/ --include="*.ts" --include="*.tsx"
```

### Code Splitting Audit

```bash
# find lazy-loaded routes
grep -rn "React.lazy\|dynamic(\|import(" src/ --include="*.tsx" --include="*.ts" | grep -v "//\|node_modules"

# routes without lazy loading
grep -rn "import.*from.*pages\|import.*from.*views\|import.*from.*screens" src/ --include="*.tsx" | grep -v "lazy\|dynamic"

# check chunk names in webpack config
grep -rn "chunkFilename\|splitChunks\|cacheGroups" webpack.config.* vite.config.*

# large synchronous imports (> 50KB estimated)
grep -rn "^import " src/ --include="*.tsx" --include="*.ts" | grep -v "from ['\"]\..*['\"]" | head -50
```

### Duplicate Module Detection

```bash
# find duplicate packages (different versions)
npm ls --all 2>/dev/null | grep -E "deduped|UNMET" | head -30
npx depcheck --json > /tmp/depcheck.json

# duplicate lodash/underscore patterns
grep -rn "from 'lodash'\|from 'underscore'\|require('lodash')" src/ --include="*.ts" --include="*.tsx"

# check package-lock for duplicate semver ranges
node -e "const l=require('./package-lock.json');const p=Object.keys(l.packages||{}).filter(k=>k.includes('node_modules/node_modules'));console.log(p.slice(0,20))"

# yarn dedupe check
yarn dedupe --check 2>/dev/null | head -20
```

### Large Dependency Analysis

```bash
# top 20 heaviest dependencies
npx cost-of-modules --no-install 2>/dev/null | head -25

# moment.js — check if replaceable with date-fns/dayjs
grep -rn "from 'moment'\|require('moment')" src/ --include="*.ts" --include="*.tsx"
# check moment locale imports
grep -rn "moment/locale\|require.*moment.*locale" src/

# full lodash vs cherry-pick
grep -rn "from 'lodash'\b" src/ | grep -v "from 'lodash/" | head -10
grep -rn "from 'lodash/" src/ | head -10

# check for heavy charting libraries
grep -rn "from 'chart.js'\|from 'd3'\|from 'echarts'\|from 'highcharts'\|from 'recharts'" src/ --include="*.tsx"
node -e "const p=require('./package.json');const heavy=['moment','@mui/material','antd','react-bootstrap','lodash','rxjs','three'];heavy.forEach(h=>{if(p.dependencies&&p.dependencies[h])console.log('HEAVY:',h,p.dependencies[h])})"
```

### CSS Unused Rules

```bash
# PurgeCSS analysis
npx purgecss --css dist/**/*.css --content dist/**/*.html dist/**/*.js --output /tmp/purged/

# check Tailwind config for content paths (unused class purge)
grep -rn "content:\|purge:" tailwind.config.*

# unused CSS with coverage (requires Chrome)
# Run: DevTools > Coverage tab > Record > Filter .css files

# CSS-in-JS audit for dead styles
grep -rn "styled\." src/ --include="*.tsx" | wc -l
grep -rn "css\`\|createStyles\|makeStyles" src/ --include="*.tsx" | wc -l

# large inline styles
grep -rn "style={{" src/ --include="*.tsx" | wc -l
```

### Font Loading Strategy

```bash
# font display strategy
grep -rn "font-display\|fontDisplay" src/ --include="*.css" --include="*.scss" public/

# variable fonts vs multiple weights
grep -rn "@font-face\|next/font\|@fontsource" src/ public/ --include="*.css" --include="*.tsx"

# Google Fonts blocking load
grep -rn "fonts.googleapis.com\|fonts.gstatic.com" public/ src/ --include="*.html" --include="*.tsx"

# preconnect hints for font CDNs
grep -rn "rel=\"preconnect\"\|rel=\"preload\"" public/ src/ --include="*.html"

# font subset analysis
grep -rn "subset\|unicode-range" src/ --include="*.css"
```

### Image Optimization

```bash
# unoptimized img tags (Next.js)
grep -rn "<img " src/ --include="*.tsx" | grep -v "next/image\|Image from"

# missing width/height causing CLS
grep -rn "<img\|<Image" src/ --include="*.tsx" | grep -v "width=\|height=\|fill"

# uncompressed image formats
find public/ src/ -name "*.png" -o -name "*.jpg" -o -name "*.jpeg" | xargs ls -lh 2>/dev/null | awk '$5 ~ /[0-9]+[KM]/ {print}' | sort -k5 -hr | head -20

# missing modern formats (WebP/AVIF)
grep -rn "\.png\|\.jpg\|\.jpeg" src/ --include="*.tsx" | grep -v "\.webp\|\.avif\|srcSet\|format=" | head -20

# lazy loading images
grep -rn "<img\|<Image" src/ --include="*.tsx" | grep -v "loading=\"lazy\"\|priority"
```

## Advanced Patterns

| Pattern | Severity | Bundle Impact |
|---------|----------|---------------|
| `import moment from 'moment'` (full 67KB gzip) | High | Replace with dayjs (2KB) or date-fns |
| `import _ from 'lodash'` (full 24KB gzip) | High | Use `import {pick} from 'lodash'` or es-toolkit |
| Barrel file with 100+ re-exports | High | Defeats tree shaking, forces full import |
| No route-level code splitting | High | Single large initial bundle |
| `import * as Icons from 'react-icons'` | High | Import individual icons only |
| CSS-in-JS at runtime (emotion/styled) | Medium | Increases JS payload, no static extraction |
| Third-party scripts in `<head>` (blocking) | High | Defer all non-critical third-party JS |
| Polyfills for modern browsers | Medium | Audit browserslist target |
| Uncompressed SVGs in bundle | Medium | Inline only small SVGs, sprite larger ones |
| Loading full i18n locale files | Medium | Dynamic locale splitting per route |
| `@sentry/browser` without tree shaking | Medium | Use modular SDK imports |
