import { useState } from "react";
import { Link } from "react-router-dom";

type Props = {
  userBadge: string;
  themeLabel: string;
  sidebarCollapsed: boolean;
  isAdmin: boolean;
  onToggleSidebar: () => void;
  onOpenSettings: () => void;
  onThemeToggle: () => void;
  onLogout: () => Promise<void>;
};

export function ChatTopbar({
  userBadge,
  themeLabel,
  sidebarCollapsed,
  isAdmin,
  onToggleSidebar,
  onOpenSettings,
  onThemeToggle,
  onLogout,
}: Props) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const themeName = themeLabel.replace("主题: ", "").replace("Theme: ", "");

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="secondary mobile-menu-btn topbar-rail-toggle" onClick={onToggleSidebar}>
          {sidebarCollapsed ? "展开" : "收起"}
        </button>
        <div className="topbar-brand">
          <div className="brand-logo" aria-hidden="true">
            <span className="brand-logo-glyph">◫</span>
          </div>
          <div className="brand-info">
            <h2>Local RAG</h2>
            <span className="brand-subtitle">多智能体知识库</span>
          </div>
        </div>
      </div>

      <div className="top-actions">
        <button type="button" className="topbar-btn" onClick={onOpenSettings} title="设置">
          <span className="btn-icon">⌘</span>
          <span className="btn-label">设置</span>
        </button>
        <button type="button" className="topbar-btn" onClick={onThemeToggle} title="主题">
          <span className="btn-icon">◌</span>
          <span className="btn-label">{themeName}</span>
        </button>
        <Link className="topbar-btn" to="/app/architecture">
          <span className="btn-icon">▦</span>
          <span className="btn-label">架构</span>
        </Link>
        {isAdmin && (
          <Link className="topbar-btn admin-btn" to="/app/admin">
            <span className="btn-icon">◇</span>
            <span className="btn-label">管理</span>
          </Link>
        )}
        <div className="topbar-divider"></div>
        <div className="user-menu-container">
          <button
            type="button"
            className="user-badge clickable"
            onClick={() => setUserMenuOpen((open) => !open)}
            title="用户菜单"
          >
            {userBadge}
          </button>
          {userMenuOpen && (
            <div className="user-menu-dropdown">
              <Link className="user-menu-item" to="/app/profile" onClick={() => setUserMenuOpen(false)}>
                <span className="menu-icon">•</span>
                个人资料
              </Link>
              <Link className="user-menu-item" to="/app/change-password" onClick={() => setUserMenuOpen(false)}>
                <span className="menu-icon">•</span>
                修改密码
              </Link>
              <button
                type="button"
                className="user-menu-item logout"
                onClick={() => {
                  setUserMenuOpen(false);
                  void onLogout();
                }}
              >
                <span className="menu-icon">•</span>
                退出登录
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
