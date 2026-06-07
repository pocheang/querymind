# test: Add i18n E2E tests and coverage checks

## 📋 Description

Add comprehensive automated tests for the i18n implementation to ensure language switching works correctly across all pages and that translation coverage is maintained over time.

## 🎯 Goal

Establish a robust testing infrastructure for i18n functionality to prevent regressions and ensure consistent bilingual support.

## ✅ Tasks

### E2E Tests (Playwright)
- [ ] Set up Playwright test suite for i18n
- [ ] Test language toggle functionality
- [ ] Test language persistence across page navigation
- [ ] Test language persistence after browser refresh
- [ ] Test all pages render correctly in English
- [ ] Test all pages render correctly in Chinese
- [ ] Test dynamic content (errors, notifications) in both languages
- [ ] Test that no missing translations appear

### Unit Tests
- [ ] Test `useTranslation` hook integration
- [ ] Test i18n configuration initialization
- [ ] Test language change events
- [ ] Test localStorage persistence
- [ ] Test fallback language behavior

### Translation Coverage Checks
- [ ] Create script to detect missing translations
- [ ] Create script to detect unused translation keys
- [ ] Add translation coverage report to CI
- [ ] Implement pre-commit hook for translation validation

### Visual Regression Tests
- [ ] Test layout with English text (shorter)
- [ ] Test layout with Chinese text (potentially longer/shorter)
- [ ] Ensure no text overflow or truncation issues
- [ ] Test responsive behavior with both languages

## 📦 Test Structure

### E2E Tests
```typescript
// tests/e2e/i18n.spec.ts
import { test, expect } from '@playwright/test';

test.describe('i18n Language Toggle', () => {
  test('should toggle language from English to Chinese', async ({ page }) => {
    await page.goto('http://localhost:5173/app');
    
    // Check initial language (English)
    await expect(page.locator('.language-toggle')).toContainText('EN');
    await expect(page.locator('.auth-intro .badge')).toContainText('Multi-Agent RAG System');
    
    // Toggle to Chinese
    await page.click('.language-toggle');
    await expect(page.locator('.language-toggle')).toContainText('ZH');
    await expect(page.locator('.auth-intro .badge')).toContainText('多智能体RAG系统');
    
    // Verify persistence
    await page.reload();
    await expect(page.locator('.language-toggle')).toContainText('ZH');
  });

  test('should persist language across page navigation', async ({ page }) => {
    await page.goto('http://localhost:5173/app');
    
    // Switch to Chinese
    await page.click('.language-toggle');
    
    // Navigate to another page (after login)
    // ... login logic ...
    await page.goto('http://localhost:5173/app/chat');
    
    // Verify language is still Chinese
    await expect(page.locator('.language-toggle')).toContainText('ZH');
  });

  test('should not show missing translation warnings', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error' || msg.type() === 'warning') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('http://localhost:5173/app');
    await page.click('.language-toggle');
    
    // Check for i18n missing translation warnings
    const missingTranslations = consoleErrors.filter(err => 
      err.includes('missing translation') || err.includes('i18next')
    );
    expect(missingTranslations).toHaveLength(0);
  });
});

test.describe('i18n All Pages', () => {
  test('LoginPage should render in both languages', async ({ page }) => {
    await page.goto('http://localhost:5173/app');
    
    // English
    await expect(page.locator('input[placeholder*="sername"]')).toBeVisible();
    
    // Chinese
    await page.click('.language-toggle');
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible();
  });
  
  // ... tests for other pages
});
```

### Translation Coverage Script
```typescript
// scripts/check-i18n-coverage.ts
import * as fs from 'fs';
import * as path from 'path';
import { glob } from 'glob';

interface TranslationKeys {
  [key: string]: string | TranslationKeys;
}

function flattenKeys(obj: TranslationKeys, prefix = ''): string[] {
  let keys: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'string') {
      keys.push(fullKey);
    } else {
      keys = keys.concat(flattenKeys(value, fullKey));
    }
  }
  return keys;
}

async function checkCoverage() {
  // Load translation files
  const enKeys = flattenKeys(
    JSON.parse(fs.readFileSync('frontend/src/i18n/locales/en.json', 'utf-8'))
  );
  const zhKeys = flattenKeys(
    JSON.parse(fs.readFileSync('frontend/src/i18n/locales/zh.json', 'utf-8'))
  );
  
  // Find missing translations
  const missingInZh = enKeys.filter(key => !zhKeys.includes(key));
  const missingInEn = zhKeys.filter(key => !enKeys.includes(key));
  
  // Find used translation keys in code
  const files = await glob('frontend/src/**/*.{ts,tsx}');
  const usedKeys = new Set<string>();
  
  for (const file of files) {
    const content = fs.readFileSync(file, 'utf-8');
    const matches = content.matchAll(/t\(['"`]([^'"`]+)['"`]\)/g);
    for (const match of matches) {
      usedKeys.add(match[1]);
    }
  }
  
  // Find unused keys
  const unusedKeys = enKeys.filter(key => !usedKeys.has(key));
  
  // Report
  console.log('=== i18n Translation Coverage Report ===\n');
  console.log(`Total keys: ${enKeys.length}`);
  console.log(`Used keys: ${usedKeys.size}`);
  console.log(`Coverage: ${((usedKeys.size / enKeys.length) * 100).toFixed(2)}%\n`);
  
  if (missingInZh.length > 0) {
    console.log('❌ Missing in Chinese:');
    missingInZh.forEach(key => console.log(`  - ${key}`));
    console.log();
  }
  
  if (missingInEn.length > 0) {
    console.log('❌ Missing in English:');
    missingInEn.forEach(key => console.log(`  - ${key}`));
    console.log();
  }
  
  if (unusedKeys.length > 0) {
    console.log('⚠️  Unused keys:');
    unusedKeys.forEach(key => console.log(`  - ${key}`));
    console.log();
  }
  
  if (missingInZh.length === 0 && missingInEn.length === 0) {
    console.log('✅ All translations are in sync!');
  }
  
  // Exit with error if there are missing translations
  if (missingInZh.length > 0 || missingInEn.length > 0) {
    process.exit(1);
  }
}

checkCoverage();
```

### CI Integration
```yaml
# .github/workflows/i18n-tests.yml
name: i18n Tests

on:
  pull_request:
    paths:
      - 'frontend/src/**/*.tsx'
      - 'frontend/src/**/*.ts'
      - 'frontend/src/i18n/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: cd frontend && npm ci
      
      - name: Check translation coverage
        run: npm run check-i18n-coverage
      
      - name: Run E2E tests
        run: npm run test:e2e:i18n
```

## 🧪 Testing Checklist

- [ ] Language toggle E2E test passes
- [ ] Language persistence test passes
- [ ] All pages render test passes in both languages
- [ ] No missing translation warnings test passes
- [ ] Translation coverage check passes
- [ ] Visual regression tests pass
- [ ] CI integration works correctly

## 📊 Acceptance Criteria

1. E2E tests cover all critical i18n scenarios
2. Translation coverage script detects missing translations
3. Translation coverage script detects unused keys
4. CI fails if translations are out of sync
5. Visual regression tests catch layout issues
6. Test coverage is at least 80% for i18n functionality
7. All tests pass consistently

## ⏱️ Estimated Effort

**3-4 hours**

- E2E test setup: 1 hour
- Test case implementation: 1.5 hours
- Coverage script: 30 minutes
- CI integration: 30 minutes
- Documentation: 30 minutes

## 🔗 Related

- Initial i18n implementation: commits `22e119d`, `65afba9`
- Issue #1: Translate remaining pages
- Issue #2: Internationalize dynamic content
- Playwright documentation: https://playwright.dev/

## 💡 Notes

- Use Playwright for E2E tests (already in devDependencies)
- Run tests in both English and Chinese locales
- Consider adding screenshot comparison for visual regression
- Pre-commit hook should be optional (not block commits)
- CI check should be required for PRs touching i18n files
- Coverage script should run in CI but also be available locally

## 📝 Package.json Scripts

Add these scripts to `frontend/package.json`:
```json
{
  "scripts": {
    "check-i18n-coverage": "tsx scripts/check-i18n-coverage.ts",
    "test:e2e:i18n": "playwright test tests/e2e/i18n.spec.ts",
    "test:i18n": "npm run check-i18n-coverage && npm run test:e2e:i18n"
  }
}
```

---

**Priority**: Low  
**Labels**: `testing`, `i18n`, `frontend`, `automation`  
**Milestone**: v0.4.6
