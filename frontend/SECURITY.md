# QueryMind Frontend Security Architecture & Policy

> **Version**: 0.7.2  
> **Status**: Active / Production Ready  
> **Scope**: QueryMind Multi-Agent RAG Frontend Architecture (`/frontend`)

---

## 🔒 1. Core Security Architecture & Measures

QueryMind Frontend implements a **defense-in-depth** model across client state, transport layers, API interactions, and storage mechanisms.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Client Browser (UI)                           │
│  • React 18 Escaped DOM        • Strict No dangerouslySetInnerHTML     │
│  • React-escaped text, no HTML • Password Policy Live Evaluation       │
│  • Open-Redirect Whitelist     • Zustand Memory Isolation on Logout   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTPS + WSS / SSE (TLS 1.3)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                          Ingress & Headers                             │
│  • CSP (script/img 'self'), nosniff, frame-ancestors 'self'            │
│  • Application rate limits per route, shared across workers            │
│  • Anti-Clickjacking (X-Frame-Options: SAMEORIGIN)                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Bearer Token + X-CSRF-Token
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       Application Gateway / API                        │
│  • RBAC Access Control (User / Admin Role Isolation)                  │
│  • PBKDF2-SHA256 Password Hashing (salt + 600k rounds)                 │
│  • CSRF Token Session Verification                                     │
│  • Single-Use Ephemeral Tokens for Sensitive ReAct Tool Approvals      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛡️ 2. Authentication & Session Security

### 2.1 Token Lifecycle & Storage
- **Bearer Token Authentication**: session tokens are opaque random values (`secrets.token_urlsafe(40)`), handled through the centralized API client (`src/lib/api.ts`). The server stores only their SHA-256 digest, so a copy of the database does not contain a usable token.
- **Automatic Request Injection**: Authenticated endpoints automatically receive `Authorization: Bearer <token>` and `X-CSRF-Token` headers.
- **Session Recovery & Resilience**: Handled via `src/lib/sessionRecovery.ts`. The client carefully inspects network error status codes to avoid clearing tokens prematurely during transient server restarts or system sleep wakes, while strictly invalidating credentials on verified 401 unauthorized responses.
- **Complete In-Memory State Clearance**: On logout or session invalidation, `clearUserState()` completely purges `useChatStore` and `useAdminStore` Zustand state slices to prevent sensitive session data, indexed documents, and configuration state from leaking to subsequent users on shared workstations.

### 2.2 Password Security & Input Policy
- **Client-Side Verification**: Real-time evaluation of password criteria (length ≥ 8, uppercase, lowercase, numbers, and special symbols) via `src/lib/validation.ts` and `src/components/PasswordRequirements.tsx`.
- **Backend Hashing**: Passwords are never stored in plaintext and are hashed using **PBKDF2 with SHA-256 (600,000 iterations) and a unique salt** on the backend. A failed sign-in costs the same hashing work whether or not the username exists, so response time does not reveal which usernames are registered.

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
| `auth_token` | `localStorage` | Session token (opaque) | High | Bearer Header Only |
| `csrf_token` | `sessionStorage` | Anti-CSRF Token | High | Ephemeral (Tab Lifetime) |
| `remembered_username` | `localStorage` | Login pre-fill | Low | Plaintext (a convenience, not a secret) |
| `language` | `localStorage` | Locale preference (`zh` / `en`) | Low | Plaintext |
| `chatSectionsHidden` | `localStorage` | Workspace layout preferences | Low | Plaintext |

### 4.2 Remembered Username
"Remember me" stores the username as plain text (`src/lib/rememberedUsername.ts`). A username is not a secret, so obfuscating it bought nothing, and the XOR + base64 scheme that used to do so threw on non-Latin-1 usernames inside the login handler, turning a successful sign-in into an error. Every storage access is wrapped so a private window that refuses storage cannot fail a login. Passwords and tokens are never stored this way. The old `sec_remembered_username` key is never read; it is removed whenever the username is remembered or forgotten.

---

## 🛑 5. XSS (Cross-Site Scripting) & Content Sanitization

1. **Zero `dangerouslySetInnerHTML` Policy**:
   - The codebase strictly prohibits `dangerouslySetInnerHTML`. Verified via automated AST lint sweeps.
2. **Safe Markdown Rendering**:
   - AI responses and rich-text explanations are rendered via `react-markdown` with `remark-gfm` in text-mode without arbitrary HTML parsing.
3. **No HTML blacklist**:
   - Prompts, filenames and session titles are rendered as React text, which React escapes. The former `sanitizeString()` blacklist was removed: it added no safety on top of that and cut words out of ordinary prompts.
4. **Images in Markdown load only from this origin**:
   - Markdown shown in the app (answers, the streaming draft, citation excerpts from retrieved documents, the model's reasoning) is not written by the reader, and an image there would be fetched as soon as it renders. `MarkdownBlock` loads an image only from the same origin, `data:` or `blob:` (`src/lib/imageSource.ts`); any other image is shown as plain text naming its host, not as a link. The CSP's `img-src` enforces the same rule (section 8).
5. **Output DLP & Hallucination Guardrails**:
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

Rate limits are enforced by the application, not by nginx: `app/api/middleware/rate_limit.py` applies per-route rules (sign-in, registration, uploads, administrative actions); with `STATE_BACKEND=shared` the counts live in Redis, so every worker shares one count. nginx (`nginx.conf`) only serves the frontend and proxies `/api/`; it overwrites `X-Forwarded-For` with the connecting address, so a client cannot choose the address its limits are counted against.

The execution event stream is proxied without buffering, so events arrive as they happen:

```nginx
location ~ ^/api/v1/orchestration/executions/[^/]+/events {
    proxy_pass http://backend:8000;
    proxy_buffering off;
    proxy_read_timeout 3600s;
}
```

---

## 🌐 8. Security Headers Specification

The frontend image sends these headers on the application page and its static assets. They are defined once in `nginx-security-headers.conf` and included by every nginx location that serves a file; `/api/` responses carry the backend's own headers (`app/api/transport/middleware.py`), whose policy also limits `img-src` to `'self' data: blob:` and runs no inline script or `eval`.

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()
```

- `style-src` allows inline styles because React style attributes, ReactFlow, Recharts and the inlined critical CSS need them; scripts are never inline.
- `Strict-Transport-Security` is added by the backend on HTTPS requests; set it on the TLS-terminating proxy in front of the frontend image as well.
- CI checks these headers on real responses from the built image (`images` job), and the browser smoke test (`npm run smoke`) fails on any CSP violation.

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
