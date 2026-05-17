/**
 * Scans dist/**.html for inline <script> tags. Production CSP is
 * `script-src 'self'` (set by infra/nginx/nginx.conf and by the meta
 * tag in BaseLayout) — any inline script body would be blocked at
 * runtime. Allowed: `<script src="..."></script>` and `<script
 * type="application/json"></script>` (data islands).
 *
 * Exits non-zero if a violation is found.
 */
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const root = 'dist';
let violations = 0;

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const st = statSync(path);
    if (st.isDirectory()) walk(path);
    else if (extname(path) === '.html') scan(path);
  }
}

const tagRe = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi;
function scan(file) {
  const html = readFileSync(file, 'utf-8');
  let m;
  while ((m = tagRe.exec(html))) {
    const attrs = m[1];
    const body = m[2].trim();
    const hasSrc = /\bsrc\s*=/.test(attrs);
    const isJsonIsland = /\btype\s*=\s*["']application\/(?:ld\+)?json["']/i.test(attrs);
    if (!hasSrc && body !== '' && !isJsonIsland) {
      violations += 1;
      const where = file.replace(/^dist\//, '');
      console.error(`✗ inline <script> in ${where}: ${body.slice(0, 120).replace(/\s+/g, ' ')}…`);
    }
  }
}

walk(root);

if (violations > 0) {
  console.error(`\n${violations} inline-script violation(s). CSP would block these in production.`);
  process.exit(1);
}
console.log('✓ no inline scripts in built HTML');
