# QueryMind Frontend Security Architecture & Policy

> **Version**: 0.7.0  
> **Status**: Active / Production Ready  
> **Scope**: QueryMind Multi-Agent RAG Frontend Architecture (`/frontend`)

---

## 🔒 1. Core Security Architecture & Measures

QueryMind Frontend implements a **defense-in-depth** model across client state, transport layers, API interactions, and storage mechanisms.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Client Browser (UI)                           │
│  • React 18 Escaped DOM        • Strict No dangerouslySetInnerHTML     │
│  • Client Input Sanitization   • Password Policy Live Evaluation       │
│  • Open-Redirect Whitelist     • Zustand Memory Isolation on Logout   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS + WSS / SSE (TLS 1.3)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Ingress & Headers                             │
│  • CSP: nosniff, frame-ancestors 'self', strict-transport-security     │
│  • Nginx Rate Limiting: /auth/login (5 req/min), /api/ (100 req/min)   │
│  • Anti-Clickjacking (X-Frame-Options: SAMEORIGIN)                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Bearer Token + X-CSRF-Token
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Application Gateway / API                        │
│  • RBAC Access Control (User / Admin Role Isolation)                  │
│  • PBKDF2 Password Hashing (Salt + 100k rounds)                        │
│  • CSRF Token Session Verification                                     │
│  • Single-Use Ephemeral Tokens for Sensitive ReAct Tool Approvals      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 2. Authentication & Session Security

### 2.1 Token Lifecycle & Storage
- **Bearer Token Authentication**: JWT authentication tokens are handled through centralized API client wrappers (`src/lib/api.ts`).
- **Automatic Request Injection**: Authenticated endpoints automatically receive `Authorization: Bearer <token>` and `X-CSRF-Token` headers.
- **Session Recovery & Resilience**: Handled via `src/lib/sessionRecovery.ts`. The client carefully inspects network error status codes to avoid clearing tokens prematurely during transient server restarts or system sleep wakes, while strictly invalidating credentials on verified 401 unauthorized responses.
- **Complete In-Memory State Clearance**: On logout or session invalidation, `clearUserState()` completely purges `useChatStore` and `useAdminStore` Zustand state slices to prevent sensitive session data, indexed documents, and configuration state from leaking to subsequent users on shared workstations.

### 2.2 Password Security & Input Policy
- **Client-Side Verification**: Real-time evaluation of password criteria (length ≥ 8, uppercase, lowercase, numbers, and special symbols) via `src/lib/validation.ts` and `src/components/PasswordRequirements.tsx`.
- **Backend Hashing**: Passwords are never stored in plaintext and are hashed using **PBKDF2 with SHA-256 and unique cryptographic salt** on the backend.

---

## 🔐 3. CSRF (Cross-Site Request Forgery) Defense

### 3.1 Cryptographic CSRF Implementation
- **Token Generation**: Cryptographically secure pseudo-random tokens generated via `window.crypto.getRandomValues()`.
- **Storage Scope**: Stored in `sessionStorage`, isolating tokens to the active browser tab and discarding them upon tab close.
- **Automatic Header Injection**: Injected on all mutation requests (`POST`, `PUT`, `PATCH`, `DELETE`).
- **Rotation**: A fresh CSRF token is negotiated and renewed upon each successful authentication handshake.
- **Reference**: `src/lib/csrf.ts`.

### 3.2 Backend Verification Contract
```python
@app.middleware("http")
async def validate_csrf(request: Request, call_next):
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        csrf_token = request.headers.get("X-CSRF-Token")
        session_csrf = request.session.get("csrf_token")
        if not csrf_token or csrf_token != session_csrf:
            return JSONResponse({"detail": "CSRF validation failed"}, status_code=403)
    return await call_next(request)
```

---

## 🗄️ 4. Data Protection & Storage Registry

### 4.1 Storage Inventory
| Key | Storage Engine | Purpose | Sensitivity | Protection Level |
| :--- | :--- | :--- | :--- | :--- |
| `auth_token` | `localStorage` | JWT Access Token | High | Bearer Header Only |
| `csrf_token` | `sessionStorage` | Anti-CSRF Token | High | Ephemeral (Tab Lifetime) |
| `sec_remembered_username` | `localStorage` | Login pre-fill | Medium | XOR Masking / Obfuscation |
| `language` | `localStorage` | Locale preference (`zh` / `en`) | Low | Plaintext |
| `chatSectionsHidden` | `localStorage` | Workspace layout preferences | Low | Plaintext |

### 4.2 Credential Obfuscation
Username remembrance uses bidirectional XOR byte scrambling (`src/lib/rememberedUsername.ts`) to prevent trivial cleartext inspection from browser storage viewers.

---

## 🛑 5. XSS (Cross-Site Scripting) & Content Sanitization

1. **Zero `dangerouslySetInnerHTML` Policy**:
   - The codebase strictly prohibits `dangerouslySetInnerHTML`. Verified via automated AST lint sweeps.
2. **Safe Markdown Rendering**:
   - AI responses and rich-text explanations are rendered via `react-markdown` with `remark-gfm` in text-mode without arbitrary HTML parsing.
3. **Strict Input Sanitization**:
   - Prompts, filenames, and session titles pass through `sanitizeString()` (`src/lib/validation.ts`) to strip script tags, dangerous entities, and control characters before transmission.
4. **Output DLP & Hallucination Guardrails**:
   - Streaming SSE responses implement real-time output data-leak prevention (DLP) token masking and NLI factuality grounding checks before display.

---

## 🔗 6. Open Redirect Protection

### 6.1 OAuth & Redirection Whitelisting
- Return URLs following login or authentication redirects are validated strictly against the current origin `window.location.origin`.
- Traversal attempts (e.g. `//evil.com`, `https://attacker.org`, `javascript:`) are rejected and safely fall back to the default dashboard `/app`.
- **Implementation**: `src/pages/login/LoginFormPanel.tsx` & `src/pages/LoginPage.tsx`.

```typescript
const allowedOrigins = [window.location.origin];
if (returnUrl.startsWith("http://") || returnUrl.startsWith("https://") || returnUrl.startsWith("//")) {
  const parsed = new URL(returnUrl, window.location.origin);
  if (!allowedOrigins.some((origin) => parsed.origin === origin)) {
    setError(t("auth.invalidRedirect"));
    return;
  }
}
```

---

## 🚦 7. Rate Limiting & Gateway Hardening

Nginx and gateway reverse proxies are configured with burst-limited request queues:

```nginx
# Authentication Endpoints
location /auth/login {
    limit_req zone=login_limit burst=3 nodelay;  # 5 req/min threshold
}

# General API Endpoints
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;   # 100 req/min threshold
}

# SSE Streaming Stream Connections
location /query/stream {
    proxy_buffering off;
    proxy_read_timeout 600s;
    limit_req zone=stream_limit burst=10 nodelay;
}
```

---

## 🌐 8. Security Headers Specification

Production servers must deliver the following security headers:

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https: wss:; object-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self';
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=(), microphone=(), payment=(), usb=()
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
```

---

## 🛠️ 9. CI/CD Quality Gates & Security Verification

All code merged to `main` must pass the following automated gate checks:

```bash
# 1. Dependency Vulnerability Audit
npm audit

# 2. Static Code Analysis & Syntax Gate
npm run lint

# 3. TypeScript Strict Compilation (Zero-Error Gate)
npm run type-check

# 4. Design & Class Hygiene Verification
npm run lint:design
npm run lint:classes

# 5. Dual-Language & Unit Test Suite (23 suites, 154 tests)
npm test -- --run

# 6. Production Bundle Build
npm run build
```

---

## 🚀 10. Pre-Production Deployment Checklist

- [ ] **HTTPS Enforced**: All HTTP requests 301-redirected to HTTPS.
- [ ] **HSTS Enabled**: `Strict-Transport-Security` header active.
- [ ] **Cookies Hardened**: `HttpOnly`, `Secure`, and `SameSite=Lax/Strict` attributes verified.
- [ ] **Environment Segregation**: Production secrets and `VITE_API_BASE_URL` defined via secure vault/CI variables.
- [ ] **CSRF Middleware Active**: Server actively validates `X-CSRF-Token` headers.
- [ ] **Rate Limiting Active**: Ingress gateway enforces rate capping on auth and AI streaming routes.
- [ ] **Sensitive Content Gate**: Verified zero hardcoded credentials, tokens, or internal IP addresses committed.
- [ ] **Dependency Audit**: `npm audit` reviewed with zero production vulnerabilities.

---

## 📞 11. Security Contacts & Vulnerability Disclosure

If you discover a security vulnerability or potential exposure in QueryMind, please report it responsibly:
- **Email**: `security@querymind.local` / internal security team channel.
- **Policy**: Please do not file public GitHub issues for unpatched security vulnerabilities.
