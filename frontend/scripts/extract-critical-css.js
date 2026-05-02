import { createServer } from 'vite';
import { generate } from 'critical';
import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
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
  const timeout = 30000; // 30s timeout

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

async function extractCriticalCSS(route) {
  console.log(`📊 Analyzing ${route.name} page (${route.path})...`);

  try {
    const { css } = await generate({
      base: BASE_URL,
      src: route.path,
      target: {
        css: OUTPUT_PATH
      },
      dimensions: DIMENSIONS,
      inline: false,
      extract: true,
      minify: true,
      penthouse: {
        timeout: 10000,
        renderWaitTime: 500,
        blockJSRequests: false
      },
      ignore: {
        atrule: ['@font-face'],
        rule: [/\.modal/, /\.dropdown/, /\.tooltip/]
      }
    });

    console.log(`✓ Extracted ${(Buffer.byteLength(css, 'utf-8') / 1024).toFixed(2)} KB from ${route.name}`);
    return css;
  } catch (err) {
    console.error(`❌ Failed to extract CSS from ${route.name}:`, err.message);
    throw err;
  }
}

function deduplicateCSS(cssArray) {
  console.log('🔄 Deduplicating CSS rules...');

  // Merge all CSS and use Set to remove exact duplicates
  // Note: This preserves CSS structure (media queries, keyframes, etc.)
  // by treating the entire CSS string as-is rather than parsing rules
  const allCSS = cssArray.join('\n');

  // Split by newlines and remove exact duplicate lines
  const lines = allCSS.split('\n');
  const seen = new Set();
  const deduplicated = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed && !seen.has(trimmed)) {
      seen.add(trimmed);
      deduplicated.push(line);
    }
  }

  return deduplicated.join('\n');
}

function validateSize(css) {
  const sizeKB = Buffer.byteLength(css, 'utf-8') / 1024;

  console.log(`📏 Critical CSS size: ${sizeKB.toFixed(2)} KB`);

  if (sizeKB > MAX_SIZE_KB) {
    console.error(`❌ Critical CSS exceeds ${MAX_SIZE_KB} KB limit (${sizeKB.toFixed(2)} KB)`);
    console.error('Consider excluding more selectors or reducing viewport coverage');
    process.exit(1);
  }

  if (sizeKB < 1) {
    console.error('❌ Critical CSS suspiciously small (< 1KB), extraction likely failed');
    process.exit(1);
  }

  console.log(`✓ Size validation passed (< ${MAX_SIZE_KB} KB)`);
}

async function main() {
  let server;

  try {
    // Start Vite dev server
    server = await startViteServer();

    // Extract critical CSS from each route
    const extractedCSS = [];
    for (const route of ROUTES) {
      const css = await extractCriticalCSS(route);
      extractedCSS.push(css);
    }

    // Merge and deduplicate
    const mergedCSS = deduplicateCSS(extractedCSS);

    // Validate size
    validateSize(mergedCSS);

    // Ensure output directory exists
    const outputDir = dirname(OUTPUT_PATH);
    if (!existsSync(outputDir)) {
      mkdirSync(outputDir, { recursive: true });
      console.log(`✓ Created output directory: ${outputDir}`);
    }

    // Write to file
    writeFileSync(OUTPUT_PATH, mergedCSS, 'utf-8');
    console.log(`✓ Written to ${OUTPUT_PATH}`);

    console.log('\n✅ Critical CSS extraction complete!');
    console.log(`   Run 'npm run build' to test inlining`);

  } catch (err) {
    console.error('\n❌ Extraction failed:', err.message);
    process.exit(1);
  } finally {
    if (server) {
      await server.close();
      console.log('✓ Vite server stopped');
    }
  }
}

main();
