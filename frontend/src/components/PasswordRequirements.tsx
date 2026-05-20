import { getPasswordRequirements } from "@/lib/validation";

interface PasswordRequirementsProps {
  password: string;
}

export function PasswordRequirements({ password }: PasswordRequirementsProps) {
  const requirements = getPasswordRequirements(password);

  return (
    <div className="auth-info-panel">
      <h3>新密码要求</h3>
      <ul className="password-requirements">
        <li className={requirements.length ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.length ? "✓" : "○"}</span>
          至少 12 个字符
        </li>
        <li className={requirements.lowercase ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.lowercase ? "✓" : "○"}</span>
          包含小写字母
        </li>
        <li className={requirements.uppercase ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.uppercase ? "✓" : "○"}</span>
          包含大写字母
        </li>
        <li className={requirements.number ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.number ? "✓" : "○"}</span>
          包含数字
        </li>
        <li className={requirements.special ? "requirement-met" : ""}>
          <span className="requirement-icon">{requirements.special ? "✓" : "○"}</span>
          包含特殊字符
        </li>
      </ul>
    </div>
  );
}
