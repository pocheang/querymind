import { useMemo, useState } from "react";

import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api";
import { validatePassword } from "@/lib/validation";
import { useFormState } from "@/hooks/useFormState";
import { AuthInput } from "@/components/AuthInput";
import { LanguageToggle } from "@/components/LanguageToggle";
import { PasswordRequirements } from "@/components/PasswordRequirements";

/** Validation hint: neutral until the field has been touched. */
function hintClass(valid: boolean, touched: boolean) {
  return cn("text-[10px]", !touched ? "text-ink-muted" : valid ? "text-success" : "text-danger");
}

export function ChangePasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const { status, setStatus, error, setError, loading, setLoading } = useFormState();

  const formValid = useMemo(() => {
    return (
      oldPassword.length > 0 &&
      validatePassword(newPassword) &&
      newPassword === confirmPassword &&
      oldPassword !== newPassword
    );
  }, [oldPassword, newPassword, confirmPassword]);

  const changePassword = async () => {
    if (!formValid) {
      setError(t("pages.changePassword.fixInputs"));
      return;
    }
    setLoading(true);
    setError("");
    setStatus(t("pages.changePassword.changing"));
    try {
      const data = await authApi.changePassword(oldPassword, newPassword);
      setStatus(data.message || t("pages.changePassword.changed"));
      window.setTimeout(() => {
        navigate("/app");
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("pages.changePassword.failed"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root flex min-h-screen items-center justify-center p-4">
      <div className="absolute right-4 top-4 z-10">
        <LanguageToggle />
      </div>

      <main className="glass-panel grid w-full max-w-3xl overflow-hidden rounded-panel shadow-elev-3 md:grid-cols-2">
        <section className="hidden flex-col gap-4 bg-[image:var(--brand-gradient)] p-8 text-white md:flex">
          <Badge variant="solid" size="pill" className="w-fit border-white/30 bg-white/15 uppercase tracking-wider">
            {t("pages.changePassword.badge")}
          </Badge>
          <div className="space-y-2">
            <h1 className="text-xl font-bold tracking-tight">{t("pages.changePassword.title")}</h1>
            <p className="text-xs leading-relaxed text-white/80">{t("pages.changePassword.description")}</p>
          </div>
          <PasswordRequirements password={newPassword} />
        </section>

        <section className="space-y-3 bg-surface p-6 sm:p-8">
          <div className="space-y-1">
            <h2 className="text-lg font-bold tracking-tight text-ink">{t("pages.changePassword.formTitle")}</h2>
            <p className="text-[11px] text-ink-muted">{t("pages.changePassword.formSubtitle")}</p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="old-password">{t("pages.changePassword.currentPassword")}</Label>
            <AuthInput
              id="old-password"
              type="password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              placeholder={t("pages.changePassword.currentPlaceholder")}
              autoComplete="current-password"
              icon="lock"
            />
            <p className={hintClass(oldPassword.length > 0, oldPassword.length > 0)}>
              {oldPassword.length > 0 ? t("pages.changePassword.currentReady") : t("pages.changePassword.currentHint")}
            </p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="new-password">{t("pages.changePassword.newPassword")}</Label>
            <AuthInput
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder={t("pages.changePassword.newPlaceholder")}
              autoComplete="new-password"
              icon="lock"
            />
            <p className={hintClass(validatePassword(newPassword), newPassword.length > 0)}>
              {validatePassword(newPassword)
                ? t("pages.changePassword.newValid")
                : newPassword.length > 0
                  ? t("pages.changePassword.newInvalid")
                  : t("pages.changePassword.newHint")}
            </p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="confirm-password">{t("pages.changePassword.confirmPassword")}</Label>
            <AuthInput
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t("pages.changePassword.confirmPlaceholder")}
              autoComplete="new-password"
              onKeyDown={(e) => {
                if (e.key === "Enter") void changePassword();
              }}
              icon="lock"
            />
            <p className={hintClass(newPassword === confirmPassword, confirmPassword.length > 0)}>
              {confirmPassword.length === 0
                ? t("pages.changePassword.confirmHint")
                : newPassword === confirmPassword
                  ? t("pages.changePassword.confirmMatch")
                  : t("pages.changePassword.confirmMismatch")}
            </p>
          </div>

          {oldPassword === newPassword && newPassword.length > 0 && (
            <p className="rounded-control border border-warning-border bg-warning-surface px-2.5 py-1.5 text-[11px] text-warning">
              {t("pages.changePassword.samePassword")}
            </p>
          )}

          <div className="flex items-center gap-2">
            <Button className="flex-1" disabled={!formValid || loading} onClick={() => void changePassword()}>
              {loading ? t("pages.changePassword.submitting") : t("pages.changePassword.submit")}
            </Button>
            <Button variant="secondary" onClick={() => navigate("/app")}>
              {t("pages.changePassword.cancel")}
            </Button>
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
