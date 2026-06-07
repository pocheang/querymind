# i18n: Internationalize API errors and form validations

## 📋 Description

Extend i18n support to cover dynamic content including API error messages, form validation messages, and other runtime-generated text. Currently, the i18n infrastructure handles static UI text, but dynamic messages are still hardcoded.

## 🎯 Goal

Provide fully internationalized error messages and validation feedback to improve user experience for non-English speakers.

## ✅ Tasks

### API Error Message Mapping
- [ ] Create error code to i18n key mapping in `src/lib/api.ts`
- [ ] Extract all API error messages from backend responses
- [ ] Add error message keys to translation files
- [ ] Implement error message translation in API response handlers
- [ ] Handle generic vs specific error messages

### Form Validation Messages
- [ ] Translate validation messages in `src/lib/validation.ts`
- [ ] Update `validateUsername()` error messages
- [ ] Update `validatePassword()` error messages
- [ ] Add validation keys to translation files
- [ ] Ensure validation works with both languages

### Toast/Notification Messages
- [ ] Identify all toast/notification locations
- [ ] Translate success messages
- [ ] Translate warning messages
- [ ] Translate info messages
- [ ] Add notification keys to translation files

### Error Boundary i18n Support
- [ ] Add error boundary fallback text translation
- [ ] Translate "Something went wrong" messages
- [ ] Add error boundary keys to translation files

### Translation Files
- [ ] Update `src/i18n/locales/en.json` with error/validation keys
- [ ] Update `src/i18n/locales/zh.json` with error/validation keys
- [ ] Organize keys by category (api.errors, validation, notifications)

## 📦 Expected Translation Keys

### API Errors
```json
{
  "api": {
    "errors": {
      "network": "Network error. Please check your connection.",
      "unauthorized": "Unauthorized. Please log in again.",
      "forbidden": "You don't have permission to perform this action.",
      "notFound": "Resource not found.",
      "serverError": "Server error. Please try again later.",
      "timeout": "Request timed out. Please try again.",
      "unknown": "An unexpected error occurred."
    }
  }
}
```

### Form Validations
```json
{
  "validation": {
    "username": {
      "required": "Username is required",
      "minLength": "Username must be at least 3 characters",
      "maxLength": "Username must not exceed 32 characters",
      "pattern": "Username can only contain letters, numbers, and underscores"
    },
    "password": {
      "required": "Password is required",
      "minLength": "Password must be at least 12 characters",
      "maxLength": "Password must not exceed 128 characters",
      "requiresSpecial": "Password must contain at least one special character"
    }
  }
}
```

### Notifications
```json
{
  "notifications": {
    "success": {
      "saved": "Changes saved successfully",
      "deleted": "Deleted successfully",
      "copied": "Copied to clipboard"
    },
    "warning": {
      "unsavedChanges": "You have unsaved changes",
      "lowStorage": "Storage space is running low"
    },
    "info": {
      "processing": "Processing your request...",
      "loading": "Loading..."
    }
  }
}
```

## 🔧 Implementation Approach

### 1. Error Code Mapping
```typescript
// src/lib/errorMapping.ts
import { useTranslation } from 'react-i18next';

export const ERROR_CODE_MAP: Record<string, string> = {
  'INVALID_CREDENTIALS': 'api.errors.invalidCredentials',
  'USER_NOT_FOUND': 'api.errors.userNotFound',
  'SESSION_EXPIRED': 'api.errors.sessionExpired',
  // ... more mappings
};

export function useErrorTranslation() {
  const { t } = useTranslation();
  
  return (error: Error | string) => {
    if (typeof error === 'string') {
      return ERROR_CODE_MAP[error] 
        ? t(ERROR_CODE_MAP[error]) 
        : t('api.errors.unknown');
    }
    // Handle Error objects
    const errorCode = (error as any).code;
    return errorCode && ERROR_CODE_MAP[errorCode]
      ? t(ERROR_CODE_MAP[errorCode])
      : error.message || t('api.errors.unknown');
  };
}
```

### 2. Validation Function Updates
```typescript
// src/lib/validation.ts
import i18n from '@/i18n/config';

export function validateUsername(username: string): string | null {
  if (!username) {
    return i18n.t('validation.username.required');
  }
  if (username.length < 3) {
    return i18n.t('validation.username.minLength');
  }
  // ... more validations
  return null;
}
```

## 🧪 Testing Checklist

- [ ] API errors display in current language
- [ ] Form validation messages display in current language
- [ ] Toast notifications display in current language
- [ ] Error boundaries display in current language
- [ ] Language switching updates all error messages
- [ ] No English text appears when Chinese is selected
- [ ] No Chinese text appears when English is selected

## 📊 Acceptance Criteria

1. All API error messages are translatable
2. All form validation messages are translatable
3. All toast/notification messages are translatable
4. Error code mapping is comprehensive
5. Error messages maintain context and clarity in both languages
6. No hardcoded error strings remain in the codebase
7. Build and type-check pass

## ⏱️ Estimated Effort

**2-3 hours**

- Error mapping implementation: 1 hour
- Validation message translation: 30 minutes
- Notification translation: 30 minutes
- Testing and validation: 1 hour

## 🔗 Related

- Initial i18n implementation: commits `22e119d`, `65afba9`
- Issue #1: Translate remaining pages
- I18N documentation: `frontend/I18N_README.md`

## 💡 Notes

- Backend API error messages may need standardization (use error codes)
- Consider creating a dedicated error handling utility
- Some error messages may need to include dynamic data (e.g., "Username 'john' already exists")
- Use interpolation for dynamic values: `t('error.userExists', { username })`
- Ensure error messages are user-friendly and actionable in both languages

---

**Priority**: Medium  
**Labels**: `enhancement`, `i18n`, `frontend`, `ux`  
**Milestone**: v0.4.5
