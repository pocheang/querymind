import { Link } from "react-router-dom";
import { getThemeIcon } from "@/lib/theme";

type Props = {
  themeLabel: string;
  sidebarCollapsed: boolean;
  onToggleSidebar: () => void;
  onOpenSettings: () => void;
  onThemeToggle: () => void;
};

export function ChatTopbar({
  themeLabel,
  sidebarCollapsed,
  onToggleSidebar,
  onOpenSettings,
  onThemeToggle,
}: Props) {
  const themeIcon = getThemeIcon(themeLabel);

  return (
    <header className="topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="secondary mobile-menu-btn topbar-rail-toggle"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? "展开侧边栏" : "打开侧边栏"}
          aria-expanded={!sidebarCollapsed}
        >
          菜单
        </button>
        <div className="topbar-brand">
          <div className="brand-logo" aria-hidden="true">
            <span className="brand-logo-glyph">▶</span>
          </div>
          <div className="brand-info">
            <h2>Local RAG</h2>
            <span className="brand-subtitle">AI Knowledge Operations</span>
          </div>
        </div>
      </div>

      <div className="top-actions">
        <button type="button" className="topbar-btn" onClick={onOpenSettings} aria-label="打开设置">
          <span className="btn-icon" aria-hidden="true">⚙</span>
          <span className="btn-label">设置</span>
        </button>
        <button type="button" className="topbar-btn" onClick={onThemeToggle} aria-label={`切换主题，当前：${themeLabel}`}>
          <span className="btn-icon" aria-hidden="true">{themeIcon}</span>
          <span className="btn-label">{themeLabel}</span>
        </button>
        <Link className="topbar-btn" to="/app/architecture" aria-label="查看系统架构">
          <span className="btn-icon" aria-hidden="true">▦</span>
          <span className="btn-label">架构</span>
        </Link>
      </div>
    </header>
  );
}
