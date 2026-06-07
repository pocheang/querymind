# i18n: Translate remaining pages (Chat, Settings, Admin, Architecture)

## 📋 Description

Continue the i18n implementation by translating the remaining pages that were not covered in the initial i18n rollout. The core i18n infrastructure is already in place with `i18next` and `react-i18next`.

## 🎯 Goal

Complete the internationalization of all user-facing pages to provide a fully bilingual (English/Chinese) experience across the entire application.

## ✅ Tasks

### ChatPage and Chat Components
- [ ] Translate `src/pages/chat/ChatPage.tsx`
- [ ] Translate `src/pages/chat/components/ChatInput.tsx`
- [ ] Translate `src/pages/chat/components/ChatMessage.tsx`
- [ ] Translate `src/pages/chat/components/ChatSidebar.tsx`
- [ ] Translate `src/pages/chat/components/SessionList.tsx`
- [ ] Add chat-related keys to `locales/en.json` and `locales/zh.json`

### SettingsPage
- [ ] Translate `src/pages/SettingsPage.tsx`
- [ ] Translate model settings section
- [ ] Translate retrieval settings section
- [ ] Translate user preferences section
- [ ] Add settings-related keys to translation files

### AdminPage and Admin Components
- [ ] Translate `src/pages/admin/AdminPage.tsx`
- [ ] Translate `src/pages/admin/components/UserManagement.tsx`
- [ ] Translate `src/pages/admin/components/SystemStats.tsx`
- [ ] Translate `src/pages/admin/components/OperationsPanel.tsx`
- [ ] Add admin-related keys to translation files

### ArchitecturePage
- [ ] Translate `src/pages/ArchitecturePage.tsx`
- [ ] Translate architecture diagram labels
- [ ] Translate component descriptions
- [ ] Add architecture-related keys to translation files

### Translation Files
- [ ] Update `src/i18n/locales/en.json` with new keys
- [ ] Update `src/i18n/locales/zh.json` with new keys
- [ ] Ensure translation consistency across all pages

## 📦 Expected Translation Keys

### Chat
```json
{
  "chat": {
    "title": "Chat Interface",
    "newSession": "New Session",
    "inputPlaceholder": "Type your message...",
    "send": "Send",
    "stop": "Stop",
    "regenerate": "Regenerate",
    "copy": "Copy",
    "delete": "Delete",
    "streaming": "Generating...",
    "error": "An error occurred",
    "noSessions": "No chat sessions",
    "createFirst": "Create your first session"
  }
}
```

### Settings
```json
{
  "settings": {
    "title": "Settings",
    "model": "Model Settings",
    "retrieval": "Retrieval Settings",
    "preferences": "User Preferences",
    "save": "Save Changes",
    "cancel": "Cancel",
    "reset": "Reset to Defaults"
  }
}
```

### Admin
```json
{
  "admin": {
    "title": "Administration",
    "users": "User Management",
    "stats": "System Statistics",
    "operations": "Operations",
    "profiles": "Retrieval Profiles",
    "audit": "Audit Logs"
  }
}
```

## 🧪 Testing Checklist

- [ ] All pages display correctly in English
- [ ] All pages display correctly in Chinese
- [ ] Language toggle works on all pages
- [ ] Language preference persists across page navigation
- [ ] No missing translation warnings in console
- [ ] Build passes without errors

## 📊 Acceptance Criteria

1. All user-facing text on ChatPage, SettingsPage, AdminPage, and ArchitecturePage is translatable
2. Both English and Chinese translations are complete and accurate
3. No hardcoded strings remain in the components
4. Language switching works seamlessly on all pages
5. Translation keys follow consistent naming convention
6. Build and type-check pass

## ⏱️ Estimated Effort

**4-6 hours**

- Translation file updates: 1-2 hours
- Component refactoring: 2-3 hours
- Testing and validation: 1 hour

## 🔗 Related

- Initial i18n implementation: commits `22e119d`, `65afba9`
- I18N documentation: `frontend/I18N_README.md`
- Frontend changes analysis: `docs/project/FRONTEND_CHANGES_ANALYSIS.md`

## 💡 Notes

- Follow the pattern established in `LoginPage.tsx` for component translation
- Use the `useTranslation` hook from `react-i18next`
- Extract all user-facing strings, including button labels, placeholders, tooltips, and error messages
- Ensure translation keys are descriptive and follow the existing naming convention
- Test with both languages to catch any layout issues due to text length differences

---

**Priority**: Medium  
**Labels**: `enhancement`, `i18n`, `frontend`  
**Milestone**: v0.4.5
