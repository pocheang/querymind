import fs from 'fs';
import path from 'path';

const stylesDir = 'src/styles';
const files = [
  'pages.css',
  'components.css',
  'chat-workbench.css',
  'modern-ui-enhancements.css',
  'final-polish.css',
  'ui-polish.css',
  'precision-adjustments.css'
];

let darkModeStyles = `/* ============================================
   Dark Theme - All Dark Mode Styles
   Modern Design System - 2026
   ============================================ */

/* ============================================
   Dark Mode Variables (from base.css)
   ============================================ */

:root[data-theme="dark"] {
  /* Colors - Dark Mode */
  --bg: #08111d;
  --bg-secondary: #0f1b2d;
  --bg-tertiary: #17263a;

  --surface: #101c30;
  --surface-hover: #17253a;
  --surface-active: #22314a;

  --text-primary: #ecf3fb;
  --text-secondary: #c3d0e0;
  --text-tertiary: #8fa0b5;
  --text-inverse: #08111d;

  --border-light: #22324b;
  --border-medium: #334766;
  --border-strong: #506889;

  --accent: #6cb6ff;
  --accent-hover: #91c8ff;
  --accent-light: #12365c;
  --accent-soft: rgba(108, 182, 255, 0.16);

  --success: #44d39c;
  --success-light: #123f34;
  --warning: #f2be5c;
  --warning-light: #4c3412;
  --danger: #ff8b8b;
  --danger-light: #4f1f29;
  --info: #47c7e8;
  --info-light: #143d4e;

  --border: var(--border-light);
  --muted: var(--text-tertiary);
  --text: var(--text-primary);
  --ok: var(--success);
  --panel: rgba(16, 28, 48, 0.96);
  --panel-strong: rgba(11, 20, 34, 0.98);
  --bg-soft: rgba(23, 37, 58, 0.92);

  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.38);
  --shadow-md: 0 8px 20px -12px rgba(0, 0, 0, 0.58), 0 4px 10px -6px rgba(0, 0, 0, 0.36);
  --shadow-lg: 0 16px 30px -16px rgba(0, 0, 0, 0.62), 0 8px 18px -10px rgba(0, 0, 0, 0.4);
  --shadow-xl: 0 28px 52px -24px rgba(0, 0, 0, 0.68), 0 16px 26px -18px rgba(0, 0, 0, 0.44);
  --shadow-2xl: 0 38px 70px -28px rgba(0, 0, 0, 0.74);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #08111d;
    --bg-secondary: #0f1b2d;
    --bg-tertiary: #17263a;

    --surface: #101c30;
    --surface-hover: #17253a;
    --surface-active: #22314a;

    --text-primary: #ecf3fb;
    --text-secondary: #c3d0e0;
    --text-tertiary: #8fa0b5;
    --text-inverse: #08111d;

    --border-light: #22324b;
    --border-medium: #334766;
    --border-strong: #506889;

    --accent: #6cb6ff;
    --accent-hover: #91c8ff;
    --accent-light: #12365c;
    --accent-soft: rgba(108, 182, 255, 0.16);

    --success: #44d39c;
    --success-light: #123f34;
    --warning: #f2be5c;
    --warning-light: #4c3412;
    --danger: #ff8b8b;
    --danger-light: #4f1f29;
    --info: #47c7e8;
    --info-light: #143d4e;

    --border: var(--border-light);
    --muted: var(--text-tertiary);
    --text: var(--text-primary);
    --ok: var(--success);
    --panel: rgba(16, 28, 48, 0.96);
    --panel-strong: rgba(11, 20, 34, 0.98);
    --bg-soft: rgba(23, 37, 58, 0.92);

    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.38);
    --shadow-md: 0 8px 20px -12px rgba(0, 0, 0, 0.58), 0 4px 10px -6px rgba(0, 0, 0, 0.36);
    --shadow-lg: 0 16px 30px -16px rgba(0, 0, 0, 0.62), 0 8px 18px -10px rgba(0, 0, 0, 0.4);
    --shadow-xl: 0 28px 52px -24px rgba(0, 0, 0, 0.68), 0 16px 26px -18px rgba(0, 0, 0, 0.44);
    --shadow-2xl: 0 38px 70px -28px rgba(0, 0, 0, 0.74);
  }
}

`;

function extractDarkModeRules(content) {
  // Match all :root[data-theme="dark"] rules with their complete content
  const regex = /:root\[data-theme="dark"\][^{]*\{[^}]*\}/g;
  const matches = content.match(regex) || [];
  return matches;
}

console.log('🔍 Extracting dark mode styles from CSS files...\n');

for (const file of files) {
  const filePath = path.join(stylesDir, file);

  if (!fs.existsSync(filePath)) {
    console.log(`⚠️  Skipping ${file} (not found)`);
    continue;
  }

  const content = fs.readFileSync(filePath, 'utf-8');
  const darkRules = extractDarkModeRules(content);

  if (darkRules.length > 0) {
    console.log(`✓ ${file}: Found ${darkRules.length} dark mode rules`);
    darkModeStyles += `\n/* ============================================\n   From ${file}\n   ============================================ */\n\n`;
    darkModeStyles += darkRules.join('\n\n') + '\n';
  } else {
    console.log(`  ${file}: No dark mode styles`);
  }
}

// Write the consolidated dark theme file
fs.writeFileSync('src/styles/themes/dark.css', darkModeStyles);

console.log('\n✅ Dark theme file created: src/styles/themes/dark.css');
console.log(`📊 Total size: ${(darkModeStyles.length / 1024).toFixed(2)} KB`);
console.log(`📝 Total rules extracted`);
