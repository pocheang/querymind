import { PurgeCSS } from 'purgecss';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function analyzeCSSUsage() {
  console.log('🔍 Starting CSS audit...\n');

  const purgeCSSResults = await new PurgeCSS().purge({
    content: [
      'src/**/*.{js,jsx,ts,tsx}',
      'index.html'
    ],
    css: [
      'src/styles/**/*.css'
    ],
    safelist: {
      standard: [/^data-theme/, /^theme-/, /dark/, /light/],
      deep: [],
      greedy: [/active$/, /disabled$/, /hover$/, /focus$/]
    }
  });

  let totalOriginalSize = 0;
  let totalPurgedSize = 0;
  const fileAnalysis = [];

  for (const result of purgeCSSResults) {
    const originalSize = result.css.length;
    const purgedSize = result.rejected ? result.rejected.join('').length : 0;
    totalOriginalSize += originalSize;
    totalPurgedSize += purgedSize;

    const filename = path.basename(result.file || 'unknown');
    const unusedPercentage = ((purgedSize / originalSize) * 100).toFixed(2);

    fileAnalysis.push({
      file: filename,
      originalSize,
      purgedSize,
      unusedPercentage,
      rejectedCount: result.rejected ? result.rejected.length : 0
    });
  }

  return {
    fileAnalysis,
    totalOriginalSize,
    totalPurgedSize,
    totalUnusedPercentage: ((totalPurgedSize / totalOriginalSize) * 100).toFixed(2)
  };
}

async function analyzeCSSDuplicates() {
  console.log('🔍 Analyzing CSS duplicates...\n');

  const cssFiles = fs.readdirSync('src/styles')
    .filter(f => f.endsWith('.css'))
    .map(f => path.join('src/styles', f));

  const allRules = new Map();
  const duplicates = [];

  for (const file of cssFiles) {
    const content = fs.readFileSync(file, 'utf-8');
    const rules = content.match(/[^{}]+\{[^{}]*\}/g) || [];

    for (const rule of rules) {
      const normalized = rule.trim().replace(/\s+/g, ' ');
      if (allRules.has(normalized)) {
        duplicates.push({
          rule: normalized.substring(0, 100) + '...',
          files: [allRules.get(normalized), path.basename(file)]
        });
      } else {
        allRules.set(normalized, path.basename(file));
      }
    }
  }

  return duplicates;
}

async function analyzeSpecificity() {
  console.log('🔍 Analyzing CSS specificity...\n');

  const cssFiles = fs.readdirSync('src/styles')
    .filter(f => f.endsWith('.css'))
    .map(f => path.join('src/styles', f));

  const highSpecificity = [];
  const importantUsage = [];

  for (const file of cssFiles) {
    const content = fs.readFileSync(file, 'utf-8');

    // Find !important usage
    const importantMatches = content.match(/!important/g);
    if (importantMatches) {
      importantUsage.push({
        file: path.basename(file),
        count: importantMatches.length
      });
    }

    // Find high specificity selectors (3+ classes/IDs)
    const selectors = content.match(/[^{}]+(?=\{)/g) || [];
    for (const selector of selectors) {
      const idCount = (selector.match(/#/g) || []).length;
      const classCount = (selector.match(/\./g) || []).length;
      const specificity = idCount * 100 + classCount * 10;

      if (specificity > 30 || idCount > 1) {
        highSpecificity.push({
          file: path.basename(file),
          selector: selector.trim().substring(0, 80),
          specificity
        });
      }
    }
  }

  return { highSpecificity, importantUsage };
}

async function measurePerformance() {
  console.log('📊 Measuring performance baseline...\n');

  const cssFiles = fs.readdirSync('src/styles')
    .filter(f => f.endsWith('.css'));

  let totalSize = 0;
  const fileSizes = [];

  for (const file of cssFiles) {
    const filePath = path.join('src/styles', file);
    const stats = fs.statSync(filePath);
    const sizeKB = (stats.size / 1024).toFixed(2);
    totalSize += stats.size;

    fileSizes.push({
      file,
      sizeKB,
      lines: fs.readFileSync(filePath, 'utf-8').split('\n').length
    });
  }

  return {
    totalSizeKB: (totalSize / 1024).toFixed(2),
    fileSizes: fileSizes.sort((a, b) => parseFloat(b.sizeKB) - parseFloat(a.sizeKB))
  };
}

// Run all analyses
async function runFullAudit() {
  try {
    const usageAnalysis = await analyzeCSSUsage();
    const duplicates = await analyzeCSSDuplicates();
    const specificity = await analyzeSpecificity();
    const performance = await measurePerformance();

    const report = {
      timestamp: new Date().toISOString(),
      summary: {
        totalFiles: usageAnalysis.fileAnalysis.length,
        totalSizeKB: performance.totalSizeKB,
        unusedCSSPercentage: usageAnalysis.totalUnusedPercentage,
        duplicateRules: duplicates.length,
        highSpecificitySelectors: specificity.highSpecificity.length,
        importantCount: specificity.importantUsage.reduce((sum, f) => sum + f.count, 0)
      },
      usageAnalysis,
      duplicates: duplicates.slice(0, 50), // Top 50 duplicates
      specificity,
      performance
    };

    // Save report
    fs.writeFileSync('css-audit-report.json', JSON.stringify(report, null, 2));

    // Generate markdown report
    const markdown = generateMarkdownReport(report);
    fs.writeFileSync('css-audit-report.md', markdown);

    console.log('✅ Audit complete!');
    console.log(`📄 Reports saved:`);
    console.log(`   - css-audit-report.json`);
    console.log(`   - css-audit-report.md`);
    console.log(`\n📊 Summary:`);
    console.log(`   Total CSS size: ${performance.totalSizeKB} KB`);
    console.log(`   Unused CSS: ${usageAnalysis.totalUnusedPercentage}%`);
    console.log(`   Duplicate rules: ${duplicates.length}`);
    console.log(`   !important usage: ${report.summary.importantCount}`);

  } catch (error) {
    console.error('❌ Error during audit:', error);
    process.exit(1);
  }
}

function generateMarkdownReport(report) {
  return `# CSS Audit Report

**Generated:** ${new Date(report.timestamp).toLocaleString()}

## 📊 Summary

- **Total CSS Files:** ${report.summary.totalFiles}
- **Total Size:** ${report.summary.totalSizeKB} KB
- **Unused CSS:** ${report.summary.unusedCSSPercentage}%
- **Duplicate Rules:** ${report.summary.duplicateRules}
- **High Specificity Selectors:** ${report.summary.highSpecificitySelectors}
- **!important Usage:** ${report.summary.importantCount}

## 📁 File Sizes

| File | Size (KB) | Lines |
|------|-----------|-------|
${report.performance.fileSizes.map(f => `| ${f.file} | ${f.sizeKB} | ${f.lines} |`).join('\n')}

## 🗑️ Unused CSS Analysis

| File | Original Size | Unused % | Rejected Rules |
|------|---------------|----------|----------------|
${report.usageAnalysis.fileAnalysis.map(f =>
  `| ${f.file} | ${(f.originalSize / 1024).toFixed(2)} KB | ${f.unusedPercentage}% | ${f.rejectedCount} |`
).join('\n')}

## 🔁 Top Duplicate Rules

${report.duplicates.slice(0, 20).map((d, i) =>
  `${i + 1}. Found in: ${d.files.join(', ')}\n   \`${d.rule}\``
).join('\n\n')}

## ⚠️ !important Usage

| File | Count |
|------|-------|
${report.specificity.importantUsage.map(f => `| ${f.file} | ${f.count} |`).join('\n')}

## 🎯 High Specificity Selectors (Top 20)

| File | Selector | Specificity |
|------|----------|-------------|
${report.specificity.highSpecificity.slice(0, 20).map(s =>
  `| ${s.file} | \`${s.selector}\` | ${s.specificity} |`
).join('\n')}

## 💡 Recommendations

1. **Remove unused CSS:** ${report.summary.unusedCSSPercentage}% of CSS is unused
2. **Deduplicate rules:** ${report.summary.duplicateRules} duplicate rules found
3. **Reduce !important:** ${report.summary.importantCount} instances found
4. **Lower specificity:** ${report.summary.highSpecificitySelectors} high-specificity selectors

---

**Next Steps:** Proceed to Phase 1 of the CSS refactoring plan.
`;
}

runFullAudit();
