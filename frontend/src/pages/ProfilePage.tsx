import { useEffect, useState } from "react";
import { ArrowLeft } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { LanguageToggle } from "@/components/LanguageToggle";
import type { AuthUser } from "@/types/api";
import { authApi } from "@/lib/auth-api";

type Props = {
  user: AuthUser | null;
  onUserUpdated: (user: AuthUser) => void;
};

export function ProfilePage({ user, onUserUpdated }: Readonly<Props>) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user) {
      setDisplayName(user.display_name || user.username);
      setEmail(user.username);
    }
  }, [user]);

  const handleSave = async () => {
    setLoading(true);
    setError("");
    setStatus(t("pages.profile.saving"));

    try {
      const updatedUser = await authApi.updateProfile(displayName);
      onUserUpdated(updatedUser);
      setStatus(t("pages.profile.saved"));
      window.setTimeout(() => setStatus(""), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("pages.profile.saveFailed"));
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <Card className="p-6">
          <p className="text-xs text-ink-muted">{t("pages.profile.loginRequired")}</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-4 p-4 sm:p-6">
      <div className="flex items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={() => navigate("/app")}>
          <ArrowLeft className="size-3.5" aria-hidden="true" />
          {t("pages.profile.back")}
        </Button>
        <h1 className="text-sm font-bold tracking-tight text-ink">{t("pages.profile.title")}</h1>
        <LanguageToggle />
      </div>

      <Card className="space-y-4 p-5">
        <div className="flex items-center gap-3">
          <span className="flex size-14 shrink-0 items-center justify-center rounded-panel bg-[image:var(--brand-gradient)] text-lg font-bold text-white shadow-elev-2">
            {user.username.charAt(0).toUpperCase()}
          </span>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold text-ink">{user.username}</h2>
            <p className="truncate font-mono text-[11px] text-ink-muted">@{user.username}</p>
            <Badge variant="brand" size="pill" className="mt-1 uppercase tracking-wider">
              {user.role === "admin" ? t("pages.profile.admin") : t("pages.profile.user")}
            </Badge>
          </div>
        </div>

        <div className="space-y-3 border-t border-line-subtle pt-4">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
            {t("pages.profile.basicInfo")}
          </h3>

          <div className="space-y-1">
            <Label htmlFor="username">{t("pages.profile.username")}</Label>
            <Input id="username" type="text" value={email} disabled />
            <p className="text-[10px] text-ink-muted">{t("pages.profile.usernameHint")}</p>
          </div>

          <div className="space-y-1">
            <Label htmlFor="display-name">{t("pages.profile.displayName")}</Label>
            <Input
              id="display-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder={t("pages.profile.displayNamePlaceholder")}
            />
            <p className="text-[10px] text-ink-muted">{t("pages.profile.displayNameHint")}</p>
          </div>
        </div>

        <div className="space-y-2 border-t border-line-subtle pt-4">
          <h3 className="text-[10px] font-bold uppercase tracking-wider text-ink-muted">
            {t("pages.profile.accountInfo")}
          </h3>

          <dl className="grid grid-cols-2 gap-2">
            {[
              { label: t("pages.profile.userId"), value: user.user_id },
              { label: t("pages.profile.role"), value: user.role },
              { label: t("pages.profile.status"), value: user.status },
              {
                label: t("pages.profile.credits"),
                value: user.role.toLowerCase() === "admin" ? t("pages.profile.unlimitedCredits") : user.credit_balance,
              },
            ].map(({ label, value }) => (
              <div key={label} className="rounded-control border border-line bg-surface p-2">
                <dt className="text-[10px] uppercase tracking-wider text-ink-muted">{label}</dt>
                <dd className="mt-0.5 truncate font-mono text-[11px] font-semibold text-ink">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="flex items-center gap-2 border-t border-line-subtle pt-4">
          <Button onClick={handleSave} disabled={loading}>
            {loading ? t("pages.profile.saving") : t("pages.profile.saveChanges")}
          </Button>
          <Button variant="secondary" onClick={() => navigate("/app/change-password")}>
            {t("pages.profile.changePassword")}
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
      </Card>
    </div>
  );
}
