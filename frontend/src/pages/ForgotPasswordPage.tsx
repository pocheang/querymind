import { useState } from "react";
import { Link } from "react-router-dom";

// Route-specific CSS (code-split by Vite)
import "@/styles/pages/auth/layout.css";
import "@/styles/pages/auth/forms.css";
import "@/styles/pages/auth/social.css";
import "@/styles/pages/auth/animations.css";
import "@/styles/themes/light/auth.css";
import "@/styles/themes/dark/auth.css";

type Props = {
  themeLabel: string;
  onThemeToggle: () => void;
};

export function ForgotPasswordPage({ themeLabel, onThemeToggle }: Props) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!email.trim()) {
      setError("请输入用户名或邮箱");
      return;
    }

    setLoading(true);
    setError("");
    setStatus("正在处理...");

    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      setSubmitted(true);
      setStatus("如果该账户存在，我们已将密码重置链接发送到您的邮箱。");
    } catch (e) {
      setError(e instanceof Error ? e.message : "请求失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="auth-root">
        <button type="button" className="theme-toggle" onClick={onThemeToggle}>
          {themeLabel}
        </button>

        <main className="auth-card forgot-password-card">
          <section className="auth-intro auth-intro-support">
            <div className="badge badge-success">邮件已发送</div>
            <div className="auth-intro-copy">
              <h1>检查您的邮箱</h1>
              <p>如果账户存在，我们已经向对应邮箱发送了重置链接。请在邮件中继续完成后续验证。</p>
            </div>

            <div className="auth-info-panel">
              <h3>接下来这样做</h3>
              <ol className="steps-list">
                <li>打开收件箱或垃圾邮件文件夹</li>
                <li>点击邮件中的密码重置链接</li>
                <li>设置新的安全密码</li>
                <li>使用新密码重新登录</li>
              </ol>
            </div>
          </section>

          <section className="auth-form">
            <div className="auth-form-header">
              <h2>仍然没有收到?</h2>
              <p className="auth-form-subtitle">您可以重新发送邮件，或联系管理员协助处理。</p>
            </div>

            <div className="help-options">
              <div className="help-option">
                <div className="help-option-copy">
                  <h4>重新发送邮件</h4>
                  <p>如果刚才输错了邮箱，或者邮件稍有延迟，可以重新提交一次找回请求。</p>
                </div>
                <button type="button" className="secondary auth-secondary-btn" onClick={() => setSubmitted(false)}>
                  重新发送
                </button>
              </div>

              <div className="help-option">
                <div className="help-option-copy">
                  <h4>联系系统管理员</h4>
                  <p>如仍无法找回账户，请联系管理员确认账号状态或手动重置登录凭证。</p>
                </div>
                <Link to="/app/login" className="link-button">
                  返回登录页
                </Link>
              </div>
            </div>

            {status && <div className="status success">{status}</div>}

            <div className="auth-footer">
              <Link className="text-link" to="/app/login">
                返回登录
              </Link>
            </div>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="auth-root">
      <button type="button" className="theme-toggle" onClick={onThemeToggle}>
        {themeLabel}
      </button>

      <main className="auth-card forgot-password-card">
        <section className="auth-intro auth-intro-support">
          <div className="badge">密码重置</div>
          <div className="auth-intro-copy">
            <h1>忘记密码?</h1>
            <p>输入您的用户名或邮箱，我们会发送一封安全重置邮件，帮助您快速恢复访问。</p>
          </div>

          <div className="auth-info-panel">
            <h3>安全提示</h3>
            <ul className="security-tips">
              <li>重置链接会在 24 小时后失效</li>
              <li>每个重置链接只能使用一次</li>
              <li>系统不会透露账号是否真实存在</li>
            </ul>
          </div>
        </section>

        <section className="auth-form">
          <div className="auth-form-header">
            <h2>重置密码</h2>
            <p className="auth-form-subtitle">输入注册时使用的用户名或邮箱地址</p>
          </div>

          <div className="input-group">
            <label htmlFor="email">用户名或邮箱</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M4 6h16v12H4V6Zm2 2v.5l6 4l6-4V8l-6 4l-6-4Z" />
                </svg>
              </span>
              <input
                id="email"
                type="text"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="请输入用户名或邮箱地址"
                autoComplete="username"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void handleSubmit();
                }}
              />
            </div>
            <div className={`hint ${email.trim() ? "ok" : ""}`}>
              {email.trim() ? "信息已填写，可发送重置链接" : "请填写您注册时使用的用户名或邮箱"}
            </div>
          </div>

          <div className="action-grid">
            <button
              type="button"
              className="primary-action-btn"
              disabled={!email.trim() || loading}
              onClick={() => void handleSubmit()}
            >
              {loading ? "发送中..." : "发送重置链接"}
            </button>
            <Link to="/app/login" className="secondary link-button">
              取消
            </Link>
          </div>

          {status && <div className="status success">{status}</div>}
          {error && <div className="status error">{error}</div>}

          <div className="auth-footer">
            <p className="footer-text">想起密码了？</p>
            <Link className="text-link" to="/app/login">
              返回登录
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
