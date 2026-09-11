import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { authApi } from "@/lib/api";
import type { AuthUser } from "@/types/api";
import { validateUsername, validatePassword, getPasswordRequirements } from "@/lib/validation";
import { useFormState } from "@/hooks/useFormState";
import {
  forgetRememberedUsername,
  hasRememberedUsername,
  rememberUsername,
  rememberedUsername,
} from "@/lib/rememberedUsername";

import { LoginHeader } from "./login/LoginHeader";
import { LoginShowcasePanel } from "./login/LoginShowcasePanel";
import { LoginFormPanel } from "./login/LoginFormPanel";
import { LoginFooter } from "./login/LoginFooter";

type Props = {
  onLogin: (user: AuthUser) => void;
};

export function LoginPage({ onLogin }: Readonly<Props>) {
  const { t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const mode = searchParams.get("mode") === "register" ? "register" : "login";

  const [username, setUsername] = useState(rememberedUsername());
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(hasRememberedUsername());
  const { status, setStatus, error, setError, loading, setLoading } = useFormState();

  const isUsernameValid = validateUsername(username);
  const isPasswordValid = validatePassword(password);

  const loginValid = useMemo(() => isUsernameValid && password.length > 0, [isUsernameValid, password]);
  const registerValid = useMemo(
    () => isUsernameValid && isPasswordValid && password === confirmPassword,
    [isUsernameValid, isPasswordValid, password, confirmPassword]
  );

  const passwordRequirements = useMemo(() => getPasswordRequirements(password), [password]);
  const passwordScore = useMemo(() => {
    if (!password) return 0;
    return Object.values(passwordRequirements).filter(Boolean).length;
  }, [password, passwordRequirements]);

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
    const returnUrl = new URLSearchParams(window.location.search).get("return") || "/app";
    const allowedOrigins = [window.location.origin];

    if (returnUrl.startsWith("http://") || returnUrl.startsWith("https://") || returnUrl.startsWith("//")) {
      try {
        const parsed = new URL(returnUrl, window.location.origin);
        if (!allowedOrigins.includes(parsed.origin)) {
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
    <div className="auth-root relative flex min-h-screen lg:h-screen lg:max-h-screen flex-col justify-between bg-[#fbf9f4] p-2.5 sm:p-4 lg:p-5 font-sans text-stone-900 antialiased overflow-x-hidden">
      {/* Warm Golden Ambient Background Glow */}
      <div className="pointer-events-none absolute -left-40 -top-40 size-[36rem] rounded-full bg-gradient-to-br from-amber-400/20 via-amber-500/10 to-transparent blur-3xl" />
      <div className="pointer-events-none absolute -right-40 -bottom-40 size-[36rem] rounded-full bg-gradient-to-tl from-amber-500/20 via-orange-400/10 to-transparent blur-3xl" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(#d6d3d1_1.2px,transparent_1.2px)] [background-size:28px_28px] opacity-40" />

      {/* Top Header Bar */}
      <LoginHeader />

      {/* Split-Screen Card (Single-Screen Fit, Balanced 1220px Width) */}
      <main className="relative z-10 mx-auto my-auto w-full max-w-[1220px] overflow-hidden rounded-2xl sm:rounded-3xl border border-amber-200/90 bg-white shadow-2xl shadow-amber-950/5 grid md:grid-cols-12">
        <LoginShowcasePanel />
        <LoginFormPanel
          mode={mode}
          setMode={setMode}
          username={username}
          setUsername={setUsername}
          password={password}
          setPassword={setPassword}
          confirmPassword={confirmPassword}
          setConfirmPassword={setConfirmPassword}
          rememberMe={rememberMe}
          setRememberMe={setRememberMe}
          passwordScore={passwordScore}
          isUsernameValid={isUsernameValid}
          isPasswordValid={isPasswordValid}
          loginValid={loginValid}
          registerValid={registerValid}
          loading={loading}
          status={status}
          error={error}
          onSubmit={() => (mode === "login" ? void login() : void register())}
          onGoogleLogin={handleGoogleLogin}
          onGitHubLogin={handleGitHubLogin}
        />
      </main>

      {/* Corporate Enterprise Footer */}
      <LoginFooter />
    </div>
  );
}
