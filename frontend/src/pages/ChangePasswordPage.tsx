import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api";

// Route-specific CSS (code-split by Vite)
import "@/styles/pages/auth/layout.css";
import "@/styles/pages/auth/forms.css";
import "@/styles/themes/light/auth.css";
import "@/styles/themes/dark/auth.css";

type Props = {
  themeLabel: string;
  onThemeToggle: () => void;
};

function validatePassword(value: string) {
  return (
    value.length >= 12 &&
    /[a-z]/.test(value) &&
    /[A-Z]/.test(value) &&
    /[0-9]/.test(value) &&
    /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value)
  );
}

export function ChangePasswordPage({ themeLabel, onThemeToggle }: Props) {
  const navigate = useNavigate();
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

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
      setError("请先修正输入内容");
      return;
    }
    setLoading(true);
    setError("");
    setStatus("正在更改密码...");
    try {
      const data = await authApi.changePassword(oldPassword, newPassword);
      setStatus(data.message || "密码已成功更改");
      setTimeout(() => {
        navigate("/app");
      }, 2000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "密码更改失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-root">
      <button type="button" className="theme-toggle" onClick={onThemeToggle}>
        {themeLabel}
      </button>

      <main className="auth-card change-password-card">
        <section className="auth-intro auth-intro-security">
          <div className="badge">安全设置</div>
          <div className="auth-intro-copy">
            <h1>更改密码</h1>
            <p>为了保护账号安全，请定期更新密码，并确保新密码与旧密码不同。</p>
          </div>

          <div className="auth-info-panel">
            <h3>新密码要求</h3>
            <ul className="password-requirements">
              <li className={newPassword.length >= 12 ? "requirement-met" : ""}>
                <span className="requirement-icon">{newPassword.length >= 12 ? "✓" : "○"}</span>
                至少 12 个字符
              </li>
              <li className={/[a-z]/.test(newPassword) ? "requirement-met" : ""}>
                <span className="requirement-icon">{/[a-z]/.test(newPassword) ? "✓" : "○"}</span>
                包含小写字母
              </li>
              <li className={/[A-Z]/.test(newPassword) ? "requirement-met" : ""}>
                <span className="requirement-icon">{/[A-Z]/.test(newPassword) ? "✓" : "○"}</span>
                包含大写字母
              </li>
              <li className={/[0-9]/.test(newPassword) ? "requirement-met" : ""}>
                <span className="requirement-icon">{/[0-9]/.test(newPassword) ? "✓" : "○"}</span>
                包含数字
              </li>
              <li className={/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(newPassword) ? "requirement-met" : ""}>
                <span className="requirement-icon">
                  {/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(newPassword) ? "✓" : "○"}
                </span>
                包含特殊字符
              </li>
            </ul>
          </div>
        </section>

        <section className="auth-form">
          <div className="auth-form-header">
            <h2>密码设置</h2>
            <p className="auth-form-subtitle">更新后，后续登录将使用新的密码凭证。</p>
          </div>

          <div className="input-group">
            <label htmlFor="old-password">当前密码</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
                </svg>
              </span>
              <input
                id="old-password"
                type="password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                placeholder="请输入当前密码"
                autoComplete="current-password"
              />
            </div>
            <div className={`hint ${oldPassword.length > 0 ? "ok" : ""}`}>
              {oldPassword.length > 0 ? "已输入当前密码" : "请输入当前密码以验证身份"}
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="new-password">新密码</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
                </svg>
              </span>
              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="请输入新密码"
                autoComplete="new-password"
              />
            </div>
            <div className={`hint ${validatePassword(newPassword) ? "ok" : newPassword.length > 0 ? "error" : ""}`}>
              {validatePassword(newPassword)
                ? "密码强度达标"
                : newPassword.length > 0
                  ? "密码不符合要求"
                  : "请设置符合要求的新密码"}
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="confirm-password">确认新密码</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
                </svg>
              </span>
              <input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="请再次输入新密码"
                autoComplete="new-password"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void changePassword();
                }}
              />
            </div>
            <div
              className={`hint ${
                confirmPassword.length > 0 ? (newPassword === confirmPassword ? "ok" : "error") : ""
              }`}
            >
              {confirmPassword.length === 0
                ? "请再次输入新密码"
                : newPassword === confirmPassword
                  ? "两次输入的密码一致"
                  : "两次输入的密码不一致"}
            </div>
          </div>

          {oldPassword === newPassword && newPassword.length > 0 && (
            <div className="alert alert-warning">新密码不能与旧密码相同</div>
          )}

          <div className="action-grid">
            <button
              type="button"
              className="primary-action-btn"
              disabled={!formValid || loading}
              onClick={() => void changePassword()}
            >
              {loading ? "更改中..." : "更改密码"}
            </button>
            <button type="button" className="secondary auth-secondary-btn" onClick={() => navigate("/app")}>
              取消
            </button>
          </div>

          {status && <div className="status success">{status}</div>}
          {error && <div className="status error">{error}</div>}
        </section>
      </main>
    </div>
  );
}
