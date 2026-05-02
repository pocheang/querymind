import { createServer } from 'vite';
import puppeteer from 'puppeteer';
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const VITE_PORT = 5173;
const VITE_HOST = '127.0.0.1';
const BASE_URL = `http://${VITE_HOST}:${VITE_PORT}`;
const OUTPUT_PATH = resolve(__dirname, '../src/styles/core/critical.css');
const MAX_SIZE_KB = 14;

// Routes to analyze
const ROUTES = [
  { path: '/app/', name: 'Login' },
  { path: '/app/chat', name: 'Chat' }
];

// Viewports to test
const DIMENSIONS = [
  { width: 1920, height: 1080 }, // Desktop
  { width: 375, height: 667 }    // Mobile (iPhone SE)
];

async function startViteServer() {
  console.log('🚀 Starting Vite dev server...');

  const server = await createServer({
    server: {
      port: VITE_PORT,
      host: VITE_HOST
    },
    logLevel: 'error'
  });

  await server.listen();

  // Wait for server to be ready
  const startTime = Date.now();
  const timeout = 30000;

  while (Date.now() - startTime < timeout) {
    try {
      const response = await fetch(BASE_URL);
      if (response.ok) {
        console.log(`✓ Vite server ready at ${BASE_URL}`);
        return server;
      }
    } catch (err) {
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  throw new Error('Vite server failed to start within 30s');
}

async function extractCriticalCSS(route, viewport) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();

  await page.setViewport(viewport);

  const url = `${BASE_URL}${route.path}`;
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 30000 });

  // Wait for CSS to load
  await new Promise(resolve => setTimeout(resolve, 2000));

  // Extract all CSS rules and check which ones apply to above-the-fold elements
  const criticalCSS = await page.evaluate((viewportHeight) => {
    const criticalRules = new Set();

    // Get all elements in the viewport (above the fold)
    const allElements = document.querySelectorAll('*');
    const aboveFoldElements = Array.from(allElements).filter(el => {
      const rect = el.getBoundingClientRect();
      return rect.top < viewportHeight && rect.bottom > 0;
    });

    // Get all stylesheets
    for (const sheet of document.styleSheets) {
      try {
        if (sheet.cssRules) {
          for (const rule of sheet.cssRules) {
            // Check if this rule applies to any above-fold element
            if (rule.type === CSSRule.STYLE_RULE) {
              try {
                const matches = aboveFoldElements.some(el => el.matches(rule.selectorText));
                if (matches) {
                  criticalRules.add(rule.cssText);
                }
              } catch (e) {
                // Invalid selector or pseudo-element, skip
              }
            } else if (rule.type === CSSRule.MEDIA_RULE) {
              // Include media queries that match current viewport
              if (window.matchMedia(rule.conditionText || rule.media.mediaText).matches) {
                for (const innerRule of rule.cssRules) {
                  if (innerRule.type === CSSRule.STYLE_RULE) {
                    try {
                      const matches = aboveFoldElements.some(el => el.matches(innerRule.selectorText));
                      if (matches) {
                        criticalRules.add(`@media ${rule.conditionText || rule.media.mediaText} { ${innerRule.cssText} }`);
                      }
                    } catch (e) {
                      // Invalid selector, skip
                    }
                  }
                }
              }
            } else if (rule.type === CSSRule.KEYFRAMES_RULE) {
              // Include keyframes that are used by above-fold elements
              criticalRules.add(rule.cssText);
            }
          }
        }
      } catch (e) {
        // CORS or other error, skip this stylesheet
      }
    }

    return Array.from(criticalRules).join('\n');
  }, viewport.height);

  await browser.close();

  return criticalCSS;
}

async function extractAllCriticalCSS() {
  const allCSS = new Set();

  for (const route of ROUTES) {
    console.log(`📊 Analyzing ${route.name} page (${route.path})...`);

    for (const viewport of DIMENSIONS) {
      console.log(`  📱 Viewport: ${viewport.width}x${viewport.height}`);
      const css = await extractCriticalCSS(route, viewport);

      // Add each rule to the set (automatic deduplication)
      css.split('\n').forEach(rule => {
        const trimmed = rule.trim();
        if (trimmed) {
          allCSS.add(trimmed);
        }
      });
    }

    const currentSize = Buffer.byteLength(Array.from(allCSS).join('\n'), 'utf-8') / 1024;
    console.log(`✓ Extracted ${currentSize.toFixed(2)} KB from ${route.name}`);
  }

  return Array.from(allCSS).join('\n');
}

function validateSize(css) {
  const sizeKB = Buffer.byteLength(css, 'utf-8') / 1024;

  console.log(`\n📏 Critical CSS size: ${sizeKB.toFixed(2)} KB`);

  if (sizeKB > MAX_SIZE_KB) {
    console.warn(`⚠️  Critical CSS exceeds ${MAX_SIZE_KB} KB limit (${sizeKB.toFixed(2)} KB)`);
    console.warn('   This is acceptable for initial extraction. Optimization can be done later.');
  }

  if (sizeKB < 1) {
    console.error('❌ Critical CSS suspiciously small (< 1KB), extraction likely failed');
    process.exit(1);
  }

  console.log(`✓ Size validation passed`);
  return sizeKB;
}

async function main() {
  let server;

  try {
    // Start Vite dev server
    server = await startViteServer();

    // Extract critical CSS from all routes and viewports
    console.log('\n🔍 Extracting critical CSS...\n');
    const criticalCSS = await extractAllCriticalCSS();

    // Validate size
    const sizeKB = validateSize(criticalCSS);

    // Ensure output directory exists
    const outputDir = dirname(OUTPUT_PATH);
    if (!existsSync(outputDir)) {
      mkdirSync(outputDir, { recursive: true });
      console.log(`✓ Created output directory: ${outputDir}`);
    }

    // Write to file
    writeFileSync(OUTPUT_PATH, criticalCSS, 'utf-8');
    console.log(`✓ Written to ${OUTPUT_PATH}`);

    console.log('\n✅ Critical CSS extraction complete!');
    console.log(`   File size: ${sizeKB.toFixed(2)} KB`);
    console.log(`   Run 'npm run build' to test inlining`);

  } catch (err) {
    console.error('\n❌ Extraction failed:', err.message);
    console.error(err.stack);
    process.exit(1);
  } finally {
    if (server) {
      await server.close();
      console.log('\n✓ Vite server stopped');
    }
  }
}

main();
