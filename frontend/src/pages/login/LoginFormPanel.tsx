import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Label } from "@/components/ui/label";
import { AuthInput } from "@/components/AuthInput";
import { cn } from "@/lib/utils";
import { LoginSocialButtons } from "./LoginSocialButtons";

interface LoginFormPanelProps {
  mode: "login" | "register";
  setMode: (mode: "login" | "register") => void;
  username: string;
  setUsername: (value: string) => void;
  password: string;
  setPassword: (value: string) => void;
  confirmPassword: string;
  setConfirmPassword: (value: string) => void;
  rememberMe: boolean;
  setRememberMe: (value: boolean) => void;
  passwordScore: number;
  isUsernameValid: boolean;
  isPasswordValid: boolean;
  loginValid: boolean;
  registerValid: boolean;
  loading: boolean;
  status: string;
  error: string;
  onSubmit: () => void;
  onGoogleLogin: () => void;
  onGitHubLogin: () => void;
}

export function LoginFormPanel({
  mode,
  setMode,
  username,
  setUsername,
  password,
  setPassword,
  confirmPassword,
  setConfirmPassword,
  rememberMe,
  setRememberMe,
  passwordScore,
  isUsernameValid,
  isPasswordValid,
  loginValid,
  registerValid,
  loading,
  status,
  error,
  onSubmit,
  onGoogleLogin,
  onGitHubLogin,
}: Readonly<LoginFormPanelProps>) {
  const { t } = useTranslation();
  const submitLabel = mode === "login" ? t("auth.loginButton") : t("auth.registerButton");

  return (
    <section className="md:col-span-6 bg-white p-6 lg:p-7 xl:p-8 flex flex-col justify-between space-y-3">
      <div>
        {/* Header & Subtitle */}
        <div className="space-y-1">
          <h2 className="text-xl sm:text-2xl font-black tracking-tight text-stone-900">
            {mode === "register" ? t("auth.register") : t("auth.login")}
          </h2>
          <p className="text-xs sm:text-sm text-stone-600 font-normal">
            {mode === "register"
              ? t("pages.login.registerSubtitle")
              : t("pages.login.loginSubtitle")}
          </p>
        </div>

        {/* Underline Tabs */}
        <div className="flex items-center gap-6 border-b-2 border-stone-200 mt-3 mb-4">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={cn(
              "pb-2 text-sm sm:text-base font-bold transition-all relative cursor-pointer",
              mode === "login"
                ? "text-amber-700 border-b-2 border-amber-600 -mb-[2px]"
                : "text-stone-400 hover:text-stone-900"
            )}
          >
            {t("auth.login")}
          </button>
          <button
            type="button"
            onClick={() => setMode("register")}
            className={cn(
              "pb-2 text-sm sm:text-base font-bold transition-all relative cursor-pointer",
              mode === "register"
                ? "text-amber-700 border-b-2 border-amber-600 -mb-[2px]"
                : "text-stone-400 hover:text-stone-900"
            )}
          >
            {t("auth.register")}
          </button>
        </div>

        {/* Form Inputs Container */}
        <div className="space-y-2.5 sm:space-y-3">
          {/* Username Input */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <Label htmlFor="username" className="text-xs sm:text-sm font-bold text-stone-800">
                {t("auth.username")}
              </Label>
              {username.length > 0 && (
                <span className="text-xs font-mono font-bold text-stone-400">
                  {username.length}/32
                </span>
              )}
            </div>
            <AuthInput
              id="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              onClear={() => setUsername("")}
              placeholder={t("auth.username")}
              autoComplete="username"
              icon="user"
              isValid={username.length > 0 ? isUsernameValid : null}
            />
            <div className="flex items-center justify-between pt-0.5 text-xs">
              {username.length > 0 && !isUsernameValid ? (
                <p className="font-bold text-rose-600">
                  {t("pages.login.invalidFormat")}
                </p>
              ) : (
                <p className="text-stone-500 font-normal">
                  {t("pages.login.usernameHint")}
                </p>
              )}
              {mode === "login" && !username && (
                <button
                  type="button"
                  onClick={() => setUsername("admin")}
                  className="font-bold text-amber-700 hover:text-amber-800 hover:underline cursor-pointer"
                >
                  {t("pages.login.fillAdmin")}
                </button>
              )}
            </div>
          </div>

          {/* Password Input */}
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <Label htmlFor="password" className="text-xs sm:text-sm font-bold text-stone-800">
                {t("auth.password")}
              </Label>
              {mode === "register" && password.length > 0 && (
                <span
                  className={cn(
                    "text-xs font-bold",
                    isPasswordValid ? "text-emerald-700" : "text-amber-700"
                  )}
                >
                  {isPasswordValid ? t("pages.login.passwordValid") : t("pages.login.weakPassword")}
                </span>
              )}
            </div>
            <AuthInput
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={t("auth.password")}
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  onSubmit();
                }
              }}
              icon="lock"
              isValid={password.length > 0 ? (mode === "register" ? isPasswordValid : true) : null}
            />
            {mode === "register" && password.length > 0 && (
              <div className="flex items-center gap-1.5 pt-0.5">
                {[1, 2, 3, 4, 5].map((step) => (
                  <div
                    key={step}
                    className={cn(
                      "h-1.5 flex-1 rounded-full transition-all duration-300",
                      passwordScore >= step
                        ? passwordScore <= 2
                          ? "bg-rose-500"
                          : passwordScore <= 4
                            ? "bg-amber-500"
                            : "bg-emerald-500"
                        : "bg-stone-200"
                    )}
                  />
                ))}
              </div>
            )}
            {password.length > 0 && mode === "register" && !isPasswordValid ? (
              <p className="text-xs font-bold text-rose-600">
                {t("pages.login.weakPassword")}
              </p>
            ) : (
              <p className="text-xs text-stone-500 font-normal">
                {t("pages.login.passwordHint")}
              </p>
            )}
          </div>

          {/* Confirm Password (Register mode only) */}
          {mode === "register" && (
            <div className="space-y-1">
              <Label htmlFor="confirmPassword" className="text-xs sm:text-sm font-bold text-stone-800">
                {t("auth.confirmPassword")}
              </Label>
              <AuthInput
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder={t("auth.confirmPassword")}
                autoComplete="new-password"
                onKeyDown={(e) => {
                  if (e.key === "Enter") onSubmit();
                }}
                icon="lock"
                isValid={confirmPassword.length > 0 ? password === confirmPassword : null}
              />
              {confirmPassword.length > 0 && (
                <p
                  className={cn(
                    "text-xs font-bold",
                    password === confirmPassword ? "text-emerald-700" : "text-rose-600"
                  )}
                >
                  {password === confirmPassword
                    ? t("pages.changePassword.confirmMatch")
                    : t("pages.changePassword.confirmMismatch")}
                </p>
              )}
            </div>
          )}

          {/* Remember Me Checkbox (Login mode only) */}
          {mode === "login" && (
            <div className="flex items-center justify-between py-0.5">
              <label className="flex items-center gap-2 text-xs sm:text-sm font-medium text-stone-700 hover:text-stone-900 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="size-4 rounded border-stone-300 text-amber-600 accent-amber-600 cursor-pointer"
                />
                <span>{t("pages.login.rememberMe")}</span>
              </label>
              <span className="text-xs text-stone-500 font-normal">
                {t("pages.login.secureStorage")}
              </span>
            </div>
          )}

          {/* Primary Golden Amber Action Button */}
          <button
            type="submit"
            disabled={mode === "login" ? !loginValid || loading : !registerValid || loading}
            onClick={onSubmit}
            className={cn(
              "w-full h-11 rounded-xl text-base font-bold transition-all duration-150 flex items-center justify-center gap-2",
              "bg-gradient-to-r from-amber-600 via-amber-700 to-amber-800 hover:from-amber-500 hover:to-amber-700 text-white shadow-md shadow-amber-900/15 active:scale-[0.99] cursor-pointer",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500 focus-visible:ring-offset-2",
              "disabled:pointer-events-none disabled:bg-stone-100 disabled:text-stone-400 disabled:border disabled:border-stone-200 disabled:shadow-none"
            )}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="size-4.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                {t("query.searching")}
              </span>
            ) : (
              submitLabel
            )}
          </button>

          {/* Mode Switch Helper Link */}
          <div className="text-center pt-0.5">
            <button
              type="button"
              className="text-xs sm:text-sm font-bold text-stone-600 hover:text-amber-700 transition-colors cursor-pointer"
              onClick={() => setMode(mode === "login" ? "register" : "login")}
            >
              {mode === "login" ? t("auth.switchToRegister") : t("auth.switchToLogin")}
            </button>
          </div>
        </div>

        {/* Social Logins / SSO (Login mode) */}
        {mode === "login" && (
          <LoginSocialButtons
            onGoogleLogin={onGoogleLogin}
            onGitHubLogin={onGitHubLogin}
          />
        )}
      </div>

      {/* Toast / Alert Status Outputs */}
      {status && (
        <output className="block rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-2 text-xs sm:text-sm font-bold text-emerald-800">
          {status}
        </output>
      )}
      {error && (
        <p
          className="rounded-xl border border-rose-200 bg-rose-50 px-3.5 py-2 text-xs sm:text-sm font-bold text-rose-700"
          role="alert"
        >
          {error}
        </p>
      )}

      {/* Bottom Agreement & System Architecture Navigation Link */}
      <div className="pt-2.5 border-t border-stone-100 flex flex-wrap items-center justify-between gap-2 text-xs text-stone-500">
        <span>{t("pages.login.termsNotice")}</span>
        <Link
          className="inline-flex items-center gap-1 font-bold text-amber-700 hover:text-amber-800 transition-colors"
          to="/app/architecture"
        >
          <span>{t("dataFlow.title")}</span>
          <span>→</span>
        </Link>
      </div>
    </section>
  );
}
