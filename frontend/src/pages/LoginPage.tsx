import { useMemo, useState } from "react";
import { Boxes, Search, ShieldCheck } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { BrandMark } from "@/components/layout/BrandMark";
import { Link, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { authApi } from "@/lib/api";
import type { AuthUser } from "@/types/api";
import { validateUsername, validatePassword } from "@/lib/validation";
import { useFormState } from "@/hooks/useFormState";
import { AuthInput } from "@/components/AuthInput";
import { LanguageToggle } from "@/components/LanguageToggle";
import {
  forgetRememberedUsername,
  hasRememberedUsername,
  rememberUsername,
  rememberedUsername,
} from "@/lib/rememberedUsername";

// Route-specific CSS (code-split by Vite)

type Props = {
  onLogin: (user: AuthUser) => void;
};

/** Validation hint: neutral until the field has been touched. */
function hintClass(valid: boolean, touched: boolean) {
  return cn("text-[10px]", !touched ? "text-ink-muted" : valid ? "text-success" : "text-danger");
}

export function LoginPage({ onLogin }: Readonly<Props>) {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const mode = searchParams.get("mode") === "register" ? "register" : "login";

  const [username, setUsername] = useState(rememberedUsername());
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(hasRememberedUsername());
  const { status, setStatus, error, setError, loading, setLoading } = useFormState();

  const loginValid = useMemo(() => validateUsername(username) && password.length > 0, [username, password]);
  const registerValid = useMemo(
    () => validateUsername(username) && validatePassword(password) && password === confirmPassword,
    [username, password, confirmPassword]
  );

  const setMode = (newMode: "login" | "register") => {
    setSearchParams({ mode: newMode });
    setError("");
    setStatus("");
    setPassword("");
    setConfirmPassword("");
  };

  const login = async () => {
    if (!loginValid) {
      setError(t("auth.loginFailed"));
      return;
    }
    setLoading(true);
    setError("");
    setStatus(t("query.searching"));
    try {
      const data = await authApi.login(username.trim(), password);
      if (rememberMe) {
        rememberUsername(username.trim());
      } else {
        forgetRememberedUsername();
      }
      onLogin(data.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("auth.loginFailed"));
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  const register = async () => {
    if (!registerValid) {
      setError(t("auth.registerFailed"));
      return;
    }
    setLoading(true);
    setError("");
    setStatus(t("query.searching"));
    try {
      const data = await authApi.register(username.trim(), password);
      setStatus(`${t("auth.registerSuccess")}: ${data.username}`);
      setTimeout(() => {
        setSearchParams({ mode: "login" });
        setPassword("");
        setConfirmPassword("");
        setStatus("");
      }, 1500);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("auth.registerFailed"));
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    // Validate return URL to prevent open redirect attacks
    const returnUrl = new URLSearchParams(window.location.search).get("return") || "/app";
    const allowedOrigins = [window.location.origin];

    // Ensure return URL is relative or same-origin
    if (returnUrl.startsWith("http://") || returnUrl.startsWith("https://") || returnUrl.startsWith("//")) {
      try {
        const parsed = new URL(returnUrl, window.location.origin);
        if (!allowedOrigins.some((origin) => parsed.origin === origin)) {
          setError(t("auth.invalidRedirect"));
          return;
        }
      } catch {
        setError(t("auth.invalidRedirect"));
        return;
      }
    }

    window.location.href = `/auth/google/login?return=${encodeURIComponent(returnUrl)}`;
  };

  const handleGitHubLogin = () => {
    setError("");
    setStatus(t("pages.login.githubUnavailable"));
  };

  return (
    <div className="auth-root flex min-h-screen items-center justify-center p-4">
      <div className="absolute right-4 top-4 z-10">
        <LanguageToggle />
      </div>

      <main className="glass-panel grid w-full max-w-4xl overflow-hidden rounded-panel shadow-elev-3 md:grid-cols-2">
        {/* Left: the pitch. Hidden on phones, where the form is the whole job. */}
        <section className="relative hidden flex-col justify-between gap-6 bg-[image:var(--brand-gradient)] p-8 text-white md:flex">
          <div className="flex items-center gap-2">
            <BrandMark />
            <span className="text-sm font-bold tracking-tight">{t("app.title")}</span>
          </div>

          <div className="space-y-3">
            <h1 className="text-2xl font-bold leading-tight tracking-tight">
              {t("pages.login.headline")
                .split("\n")
                .map((line) => (
                  <span key={line} className="block">
                    {line}
                  </span>
                ))}
            </h1>
            <p className="text-xs leading-relaxed text-white/80">{t("app.subtitle")}</p>
          </div>

          <ul className="space-y-2">
            {[
              { icon: Boxes, label: t("features.multiAgent") },
              { icon: Search, label: t("features.hybridSearch") },
              { icon: ShieldCheck, label: t("features.enterpriseSecurity") },
            ].map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-2 rounded-control bg-white/10 px-3 py-2 text-[11px]">
                <Icon className="size-3.5 shrink-0" aria-hidden="true" />
                {label}
              </li>
            ))}
          </ul>
        </section>

        {/* Right: the form. */}
        <section className="space-y-3 bg-surface p-6 sm:p-8">
          <div className="space-y-1">
            <h2 className="text-lg font-bold tracking-tight text-ink">
              {mode === "register" ? t("auth.register") : t("auth.login")}
            </h2>
            <p className="text-[11px] text-ink-muted">{t("app.subtitle")}</p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="username">{t("auth.username")}</Label>
            <AuthInput
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t("auth.username")}
              autoComplete="username"
              icon="user"
            />
            <p className={hintClass(validateUsername(username), username.length > 0)}>
              {username.length === 0
                ? t("pages.login.usernameHint")
                : validateUsername(username)
                  ? t("pages.login.usernameValid")
                  : t("pages.login.invalidFormat")}
            </p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="password">{t("auth.password")}</Label>
            <AuthInput
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t("auth.password")}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  if (mode === "register") void register();
                  else void login();
                }
              }}
              icon="lock"
            />
            <p className={hintClass(validatePassword(password), password.length > 0)}>
              {password.length === 0
                ? t("pages.login.passwordHint")
                : validatePassword(password)
                  ? t("pages.login.passwordValid")
                  : t("pages.login.weakPassword")}
            </p>
          </div>

          {mode === "register" && (
            <div className="space-y-1">
              <Label htmlFor="confirmPassword">{t("auth.confirmPassword")}</Label>
              <AuthInput
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t("auth.confirmPassword")}
                autoComplete="new-password"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void register();
                }}
                icon="lock"
              />
              {confirmPassword.length > 0 && (
                <p className={hintClass(password === confirmPassword, true)}>
                  {password === confirmPassword
                    ? t("pages.changePassword.confirmMatch")
                    : t("pages.changePassword.confirmMismatch")}
                </p>
              )}
            </div>
          )}

          {mode === "login" && (
            <label className="flex items-center gap-2 text-[11px] text-ink-muted">
              <input
                type="checkbox"
                checked={rememberMe}
                onChange={(e) => setRememberMe(e.target.checked)}
                className="size-3.5 accent-[var(--brand)]"
              />
              {t("pages.login.rememberMe")}
            </label>
          )}

          <Button
            size="lg"
            className="w-full"
            disabled={mode === "login" ? !loginValid || loading : !registerValid || loading}
            onClick={() => (mode === "login" ? void login() : void register())}
          >
            {loading ? t("query.searching") : mode === "login" ? t("auth.loginButton") : t("auth.registerButton")}
          </Button>

          <div className="text-center">
            <Button variant="link" size="sm" onClick={() => setMode(mode === "login" ? "register" : "login")}>
              {mode === "login" ? t("auth.switchToRegister") : t("auth.switchToLogin")}
            </Button>
          </div>

          {mode === "login" && (
            <>
              <div className="flex items-center gap-2">
                <span className="h-px flex-1 bg-line" />
                <span className="text-[10px] text-ink-muted">{t("pages.login.socialDivider")}</span>
                <span className="h-px flex-1 bg-line" />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button variant="outline" onClick={handleGoogleLogin}>
                  <span className="font-bold text-brand-accent" aria-hidden="true">
                    G
                  </span>
                  Google
                </Button>
                <Button variant="outline" onClick={handleGitHubLogin}>
                  <svg className="size-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.1.68-.21.68-.48v-1.68c-2.77.6-3.35-1.18-3.35-1.18c-.45-1.15-1.1-1.46-1.1-1.46c-.9-.61.07-.6.07-.6c1 .07 1.52 1.02 1.52 1.02c.88 1.5 2.3 1.07 2.86.82c.09-.64.35-1.08.64-1.32c-2.21-.25-4.54-1.11-4.54-4.93c0-1.09.39-1.98 1.03-2.67c-.11-.25-.45-1.27.1-2.64c0 0 .84-.27 2.75 1.02A9.53 9.53 0 0 1 12 6.84a9.5 9.5 0 0 1 2.5.34c1.9-1.29 2.74-1.02 2.74-1.02c.56 1.37.22 2.39.11 2.64c.64.69 1.03 1.58 1.03 2.67c0 3.83-2.33 4.67-4.55 4.92c.36.31.68.92.68 1.86v2.76c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" />
                  </svg>
                  GitHub
                </Button>
              </div>
            </>
          )}

          <div className="text-center">
            <Link className="text-[11px] text-brand-text hover:underline" to="/app/architecture">
              {t("dataFlow.title")}
            </Link>
          </div>

          {status && (
            <p
              className="rounded-control border border-success-border bg-success-surface px-2.5 py-1.5 text-[11px] text-success"
              role="status"
            >
              {status}
            </p>
          )}
          {error && (
            <p
              className="rounded-control border border-danger-border bg-danger-surface px-2.5 py-1.5 text-[11px] text-danger"
              role="alert"
            >
              {error}
            </p>
          )}
        </section>
      </main>
    </div>
  );
}
