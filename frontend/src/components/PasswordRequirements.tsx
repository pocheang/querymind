import { useTranslation } from "react-i18next";
import { Check, Circle } from "lucide-react";

import { cn } from "@/lib/utils";
import { getPasswordRequirements } from "@/lib/validation";

interface PasswordRequirementsProps {
  password: string;
}

/**
 * Live password-policy checklist.
 *
 * Rendered on the amber gradient panel of the auth pages, so met/unmet is
 * carried by an icon as well as by opacity -- colour alone would not survive
 * that background.
 */
export function PasswordRequirements({ password }: Readonly<PasswordRequirementsProps>) {
  const { t } = useTranslation();
  const requirements = getPasswordRequirements(password);

  const rows = [
    { met: requirements.length, label: t("components.passwordRequirements.length") },
    { met: requirements.lowercase, label: t("components.passwordRequirements.lowercase") },
    { met: requirements.uppercase, label: t("components.passwordRequirements.uppercase") },
    { met: requirements.number, label: t("components.passwordRequirements.number") },
    { met: requirements.special, label: t("components.passwordRequirements.special") },
  ];

  return (
    <div className="rounded-card bg-white/10 p-3">
      <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider">
        {t("components.passwordRequirements.title")}
      </h3>
      <ul className="space-y-1.5">
        {rows.map(({ met, label }) => (
          <li key={label} className={cn("flex items-center gap-1.5 text-xs sm:text-sm", met ? "font-medium" : "opacity-75")}>
            {met ? (
              <Check className="size-3.5 shrink-0" strokeWidth={3} aria-hidden="true" />
            ) : (
              <Circle className="size-3.5 shrink-0" aria-hidden="true" />
            )}
            {label}
          </li>
        ))}
      </ul>
    </div>
  );
}
