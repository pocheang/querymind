import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { authApi } from "@/lib/api";
import type { AuthUser } from "@/types/api";

type Props = {
  onLogin: (user: AuthUser) => void;
  themeLabel: string;
  onThemeToggle: () => void;
};

function validateUsername(value: string) {
  return /^[A-Za-z0-9._-]{3,32}$/.test(value.trim());
}

function validatePassword(value: string) {
  return (
    value.length >= 12 &&
    /[a-z]/.test(value) &&
    /[A-Z]/.test(value) &&
    /[0-9]/.test(value) &&
    /[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(value)
  );
}

export function LoginPage({ onLogin, themeLabel, onThemeToggle }: Props) {
  const [username, setUsername] = useState(localStorage.getItem("remembered_username") || "");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(!!localStorage.getItem("remembered_username"));
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const loginValid = useMemo(() => validateUsername(username) && password.length > 0, [username, password]);
  const registerValid = useMemo(
    () => validateUsername(username) && validatePassword(password),
    [username, password],
  );

  const login = async () => {
    if (!loginValid) {
      setError("请输入有效用户名和密码");
      return;
    }
    setLoading(true);
    setError("");
    setStatus("登录中...");
    try {
      const data = await authApi.login(username.trim(), password);
      if (rememberMe) localStorage.setItem("remembered_username", username.trim());
      else localStorage.removeItem("remembered_username");
      onLogin(data.user);
    } catch (e) {
      setError(e instanceof Error ? e.message : "登录失败");
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  const register = async () => {
    if (!registerValid) {
      setError("请先修正输入内容");
      return;
    }
    setLoading(true);
    setError("");
    setStatus("注册中...");
    try {
      const data = await authApi.register(username.trim(), password);
      setStatus(`注册成功：${data.username}，请登录`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "注册失败");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = "/api/auth/google/login";
  };

  const handleGitHubLogin = () => {
    setError("");
    setStatus("GitHub OAuth 待后端接入后启用");
  };

  return (
    <div className="auth-root">
      <button type="button" className="theme-toggle" onClick={onThemeToggle}>
        {themeLabel}
      </button>

      <main className="auth-card">
        <section className="auth-intro auth-intro-primary">
          <div className="badge">多智能体 RAG 系统</div>
          <div className="auth-intro-copy">
            <h1>
              Local RAG
              <br />
              Platform
            </h1>
            <p>企业级本地知识库问答系统。支持多智能体协作、混合检索、知识图谱增强和流式对话。</p>
          </div>

          <div className="auth-feature-stack">
            <div className="auth-feature-card">
              <span className="auth-feature-icon auth-feature-icon-purple" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M9 3h6v3h3v4h-2V8H8v2H6V6h3V3Zm-1 9h8v7H8v-7Zm4-4a2 2 0 1 0 0 4a2 2 0 0 0 0-4Z" />
                </svg>
              </span>
              <span>多智能体编排</span>
            </div>
            <div className="auth-feature-card">
              <span className="auth-feature-icon auth-feature-icon-blue" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M10.5 4a6.5 6.5 0 1 1-4.03 11.6L3 19l1.4 1.4l3.4-3.47A6.5 6.5 0 1 1 10.5 4Zm0 2a4.5 4.5 0 1 0 0 9a4.5 4.5 0 0 0 0-9Z" />
                </svg>
              </span>
              <span>混合检索引擎</span>
            </div>
            <div className="auth-feature-card">
              <span className="auth-feature-icon auth-feature-icon-amber" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
                </svg>
              </span>
              <span>企业级安全</span>
            </div>
          </div>

          <div className="auth-intro-orb auth-intro-orb-large" aria-hidden="true" />
          <div className="auth-intro-orb auth-intro-orb-small" aria-hidden="true" />
        </section>

        <section className="auth-form">
          <div className="auth-form-header">
            <h2>欢迎回来</h2>
            <p className="auth-form-subtitle">登录以访问您的知识库控制台</p>
          </div>

          <div className="input-group">
            <label htmlFor="username">用户名</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M12 12a4 4 0 1 0-4-4a4 4 0 0 0 4 4Zm0 2c-3.33 0-6 2.02-6 4.5V20h12v-1.5c0-2.48-2.67-4.5-6-4.5Z" />
                </svg>
              </span>
              <input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="请输入用户名"
                autoComplete="username"
              />
            </div>
            <div className={`hint ${validateUsername(username) ? "ok" : username.length > 0 ? "error" : ""}`}>
              {username.length === 0
                ? "3-32位字母、数字或._-"
                : validateUsername(username)
                  ? "用户名格式可用"
                  : "用户名格式不正确"}
            </div>
          </div>

          <div className="input-group">
            <label htmlFor="password">密码</label>
            <div className="auth-input-shell">
              <span className="auth-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M17 9h-1V7a4 4 0 1 0-8 0v2H7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7a2 2 0 0 0-2-2Zm-7-2a2 2 0 1 1 4 0v2h-4V7Z" />
                </svg>
              </span>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="请输入密码"
                autoComplete="current-password"
                onKeyDown={(e) => {
                  if (e.key === "Enter") void login();
                }}
              />
            </div>
            <div className={`hint ${validatePassword(password) ? "ok" : password.length > 0 ? "error" : ""}`}>
              {password.length === 0
                ? "注册需 12 位以上，含大小写、数字和特殊字符"
                : validatePassword(password)
                  ? "密码强度达标"
                  : "密码强度不足"}
            </div>
          </div>

          <div className="row-actions auth-extra-row">
            <label className="checkline auth-checkline">
              <input type="checkbox" checked={rememberMe} onChange={(e) => setRememberMe(e.target.checked)} />
              记住用户名
            </label>
            <Link to="/app/forgot-password" className="text-link-btn">
              忘记密码?
            </Link>
          </div>

          <div className="action-grid">
            <button
              type="button"
              className="primary-action-btn"
              disabled={!loginValid || loading}
              onClick={() => void login()}
            >
              {loading ? "登录中..." : "登录系统"}
            </button>
            <button
              type="button"
              className="secondary auth-secondary-btn"
              disabled={!registerValid || loading}
              onClick={() => void register()}
            >
              {loading ? "注册中..." : "注册新账号"}
            </button>
          </div>

          <div className="divider">
            <span>或使用第三方登录</span>
          </div>

          <div className="social-grid">
            <button type="button" className="social-btn google-btn" onClick={handleGoogleLogin}>
              <span className="social-icon social-icon-google" aria-hidden="true">
                G
              </span>
              Google
            </button>
            <button type="button" className="social-btn github-btn" onClick={handleGitHubLogin}>
              <span className="social-icon social-icon-github" aria-hidden="true">
                <svg viewBox="0 0 24 24" focusable="false">
                  <path d="M12 2a10 10 0 0 0-3.16 19.49c.5.1.68-.21.68-.48v-1.68c-2.77.6-3.35-1.18-3.35-1.18c-.45-1.15-1.1-1.46-1.1-1.46c-.9-.61.07-.6.07-.6c1 .07 1.52 1.02 1.52 1.02c.88 1.5 2.3 1.07 2.86.82c.09-.64.35-1.08.64-1.32c-2.21-.25-4.54-1.11-4.54-4.93c0-1.09.39-1.98 1.03-2.67c-.11-.25-.45-1.27.1-2.64c0 0 .84-.27 2.75 1.02A9.53 9.53 0 0 1 12 6.84a9.5 9.5 0 0 1 2.5.34c1.9-1.29 2.74-1.02 2.74-1.02c.56 1.37.22 2.39.11 2.64c.64.69 1.03 1.58 1.03 2.67c0 3.83-2.33 4.67-4.55 4.92c.36.31.68.92.68 1.86v2.76c0 .27.18.58.69.48A10 10 0 0 0 12 2Z" />
                </svg>
              </span>
              GitHub
            </button>
          </div>

          <div className="auth-footer">
            <Link className="text-link" to="/app/architecture">
              查看系统架构
            </Link>
          </div>

          {status && <div className="status success">{status}</div>}
          {error && <div className="status error">{error}</div>}
        </section>
      </main>
    </div>
  );
}
