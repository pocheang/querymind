import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import type { AuthUser } from "@/types/api";
import { authApi } from "@/lib/auth-api";

// Route-specific CSS (code-split by Vite)
import "@/styles/pages/profile.css";

type Props = {
  user: AuthUser | null;
};

export function ProfilePage({ user }: Props) {
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
    setStatus("保存中...");

    try {
      await authApi.updateProfile(displayName);
      setStatus("个人资料已保存");
      setTimeout(() => setStatus(""), 3000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
    } finally {
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="profile-page">
        <div className="profile-card">
          <p>请先登录</p>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="profile-header">
        <button type="button" className="back-btn" onClick={() => navigate("/app")}>
          ← 返回
        </button>
        <h1>个人资料</h1>
      </div>

      <div className="profile-card">
        <div className="profile-avatar-section">
          <div className="profile-avatar">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div className="profile-info">
            <h2>{user.username}</h2>
            <p className="profile-username">@{user.username}</p>
            <span className="profile-badge">{user.role === "admin" ? "管理员" : "用户"}</span>
          </div>
        </div>

        <div className="profile-section">
          <h3>基本信息</h3>

          <div className="form-group">
            <label htmlFor="username">用户名</label>
            <input
              id="username"
              type="text"
              value={email}
              disabled
              className="disabled-input"
            />
            <div className="hint">用户名不可更改</div>
          </div>

          <div className="form-group">
            <label htmlFor="display-name">显示名称</label>
            <input
              id="display-name"
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="输入显示名称"
            />
            <div className="hint">此名称将在系统中显示</div>
          </div>
        </div>

        <div className="profile-section">
          <h3>账户信息</h3>

          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">用户 ID</span>
              <span className="info-value">{user.user_id}</span>
            </div>
            <div className="info-item">
              <span className="info-label">角色</span>
              <span className="info-value">{user.role}</span>
            </div>
            <div className="info-item">
              <span className="info-label">账户状态</span>
              <span className="info-value status-active">{user.status}</span>
            </div>
          </div>
        </div>

        <div className="profile-actions">
          <button
            type="button"
            onClick={handleSave}
            disabled={loading}
            className="primary-btn"
          >
            {loading ? "保存中..." : "保存更改"}
          </button>
          <button
            type="button"
            onClick={() => navigate("/app/change-password")}
            className="secondary-btn"
          >
            更改密码
          </button>
        </div>

        {status && <div className="status success">{status}</div>}
        {error && <div className="status error">{error}</div>}
      </div>
    </div>
  );
}
