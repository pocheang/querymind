import { useTranslation } from "react-i18next";
import { getPasswordRequirements } from "@/lib/validation";

interface PasswordRequirementsProps {
  password: string;
}

export function PasswordRequirements({ password }: PasswordRequirementsProps) {
  const { t } = useTranslation();
  const requirements = getPasswordRequirements(password);
  const complete = "✓";
  const pending = "○";

  return (
    <div className="auth-info-panel">
      <h3>{t("components.passwordRequirements.title")}</h3>
      <ul className="password-requirements">
        <li className={requirements.length ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.length ? complete : pending}</span>
          {t("components.passwordRequirements.length")}
        </li>
        <li className={requirements.lowercase ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.lowercase ? complete : pending}</span>
          {t("components.passwordRequirements.lowercase")}
        </li>
        <li className={requirements.uppercase ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.uppercase ? complete : pending}</span>
          {t("components.passwordRequirements.uppercase")}
        </li>
        <li className={requirements.number ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.number ? complete : pending}</span>
          {t("components.passwordRequirements.number")}
        </li>
        <li className={requirements.special ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.special ? complete : pending}</span>
          {t("components.passwordRequirements.special")}
        </li>
      </ul>
    </div>
  );
}
