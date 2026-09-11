import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Command } from "cmdk";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  Globe,
  KeyRound,
  Keyboard,
  LogOut,
  MessageSquare,
  MessagesSquare,
  PanelLeft,
  Plus,
  Settings,
  Settings2,
  User as UserIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { getPermissionCheck } from "@/hooks/usePermissions";
import { useChatStore } from "@/stores/useChatStore";
import { useSidebarToggle } from "@/hooks/useSidebarToggle";
import { useDismissable } from "@/hooks/useDismissable";
import type { UserIdentity } from "@/types/auth";

export interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  user: UserIdentity | null;
  onLogout?: () => void;
  onOpenSettings?: () => void;
  onOpenSessionManagement?: () => void;
  onOpenShortcuts?: () => void;
  onNewSession?: () => void;
}

/**
 * The command palette the design prototype opens with its ⌘K button.
 *
 * Every entry is an action the app already has -- the five routes, the session
 * list, the settings and session-management drawers, the shortcut sheet, the
 * language toggle, sign out. Nothing here is new capability; what was missing
 * was a way to reach any of it from the keyboard, and a way to reach the
 * chat-only drawers from the other four views at all.
 *
 * Sessions are listed only when the app has loaded some. A palette that offers
 * "jump to session" against an empty list is the kind of control that looks
 * broken rather than empty.
 */
export function CommandPalette({
  open,
  onOpenChange,
  user,
  onLogout,
  onOpenSettings,
  onOpenSessionManagement,
  onOpenShortcuts,
  onNewSession,
}: Readonly<CommandPaletteProps>) {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const toggleSidebar = useSidebarToggle();
  const sessions = useChatStore((s) => s.sessions);
  const setCurrentSessionId = useChatStore((s) => s.setCurrentSessionId);
  const [search, setSearch] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const permissions = getPermissionCheck(user);
  const onChat = location.pathname === "/app";

  // Reopening should not resume someone else's half-typed filter.
  useEffect(() => {
    if (!open) setSearch("");
  }, [open]);

  const dismiss = useCallback(() => onOpenChange(false), [onOpenChange]);
  useDismissable(open, dismiss);

  // After useDismissable, so it has already recorded what to restore to.
  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const run = (action: () => void) => () => {
    onOpenChange(false);
    action();
  };

  const views = useMemo(
    () =>
      [
        { icon: MessageSquare, label: t("nav.deck", "Operations Deck"), to: "/app", show: !!user },
        { icon: BarChart3, label: t("nav.analytics", "Analytics"), to: "/app/analytics", show: permissions.canViewAnalytics },
        { icon: Settings2, label: t("nav.admin", "Admin Console"), to: "/app/admin", show: permissions.canAccessAdmin },
        { icon: Boxes, label: t("nav.architecture", "Architecture"), to: "/app/architecture", show: true },
        { icon: Globe, label: t("nav.landing", "Showcase"), to: "/", show: true },
      ].filter((v) => v.show),
    [t, user, permissions.canViewAnalytics, permissions.canAccessAdmin]
  );

  if (!open) return null;

  const item = "flex cursor-pointer items-center gap-2.5 rounded-control px-2.5 py-2 text-xs sm:text-sm font-medium text-ink data-[selected=true]:bg-brand-surface data-[selected=true]:text-brand-text-strong";
  const group = "[&_[cmdk-group-heading]]:px-2.5 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-xs [&_[cmdk-group-heading]]:font-bold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wider [&_[cmdk-group-heading]]:text-ink/80";

  return (
    <>
      <button
        type="button"
        aria-label={t("common.close", "Close")}
        className="fixed inset-0 z-50 cursor-default bg-stone-900/30 backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
      />
      <div className="fixed left-1/2 top-[15vh] z-50 w-[min(38rem,calc(100vw-2rem))] -translate-x-1/2">
        <Command
          label={t("components.commandPalette.title", "Command palette")}
          className="glass-panel overflow-hidden rounded-panel shadow-elev-3 animate-in fade-in-0 zoom-in-95"
          loop
        >
          <div className="flex items-center gap-2.5 border-b border-line px-3">
            <Command.Input
              ref={inputRef}
              value={search}
              onValueChange={setSearch}
              placeholder={t("components.commandPalette.placeholder", "Type a command or search…")}
              className="h-11 w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
            />
            <kbd className="shrink-0 rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-xs font-semibold text-ink/80">
              Esc
            </kbd>
          </div>

          <Command.List className="max-h-[min(24rem,60vh)] overflow-y-auto p-1.5">
            <Command.Empty className="px-2.5 py-6 text-center text-xs sm:text-sm text-ink/80">
              {t("components.commandPalette.empty", "No matching command")}
            </Command.Empty>

            <Command.Group heading={t("components.commandPalette.navigate", "Go to")} className={group}>
              {views.map(({ icon: Icon, label, to }) => (
                <Command.Item key={to} value={`go ${label}`} onSelect={run(() => navigate(to))} className={item}>
                  <Icon className="size-4 shrink-0 text-brand-accent" aria-hidden="true" />
                  {label}
                </Command.Item>
              ))}
            </Command.Group>

            {user && (
              <Command.Group heading={t("components.commandPalette.actions", "Actions")} className={group}>
                {onNewSession && (
                  <Command.Item value="new session 新建会话" onSelect={run(onNewSession)} className={item}>
                    <Plus className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                    {t("components.chat.newSession", "New session")}
                    <Shortcut keys="Ctrl N" />
                  </Command.Item>
                )}
                {onChat && (
                  <Command.Item value="toggle sidebar 侧栏" onSelect={run(toggleSidebar)} className={item}>
                    <PanelLeft className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                    {t("components.chat.toggleSidebar", "Sessions and tools")}
                    <Shortcut keys="Ctrl B" />
                  </Command.Item>
                )}
                {onOpenSettings && (
                  // `value` is what cmdk matches against, so the drawer's
                  // sections are searchable by name from here. Deliberately
                  // not separate items: they are one destination, and a second
                  // name for a place the app already has is the reason the
                  // prototype's Integrations button was not built.
                  <Command.Item
                    value="settings 设置 api integrations 集成 long-term memory 长期记忆 privacy 隐私"
                    onSelect={run(onOpenSettings)}
                    className={item}
                  >
                    <Settings className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                    {t("components.chat.settings", "Settings")}
                  </Command.Item>
                )}
                {onOpenSessionManagement && (
                  <Command.Item value="session management 会话管理" onSelect={run(onOpenSessionManagement)} className={item}>
                    <MessagesSquare className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                    {t("sessionManagement.title", "Session management")}
                  </Command.Item>
                )}
                {onOpenShortcuts && (
                  <Command.Item value="keyboard shortcuts 快捷键" onSelect={run(onOpenShortcuts)} className={item}>
                    <Keyboard className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                    {t("components.keyboard.title", "Keyboard shortcuts")}
                    <Shortcut keys="?" />
                  </Command.Item>
                )}
                <Command.Item
                  value="language 语言 english 中文"
                  onSelect={run(() => void i18n.changeLanguage(i18n.language === "zh" ? "en" : "zh"))}
                  className={item}
                >
                  <Globe className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                  {t("components.commandPalette.switchLanguage", "Switch language")}
                  <span className="ml-auto font-mono text-xs font-semibold text-ink/80">
                    {i18n.language === "zh" ? "EN" : "ZH"}
                  </span>
                </Command.Item>
              </Command.Group>
            )}

            {user && sessions.length > 0 && (
              <Command.Group heading={t("components.commandPalette.sessions", "Sessions")} className={group}>
                {sessions.slice(0, 20).map((session) => (
                  <Command.Item
                    key={session.session_id}
                    value={`session ${session.title || session.session_id}`}
                    onSelect={run(() => {
                      navigate("/app");
                      setCurrentSessionId(session.session_id);
                    })}
                    className={item}
                  >
                    <MessageSquare className="size-3.5 shrink-0 text-ink-muted" aria-hidden="true" />
                    <span className="truncate">{session.title || session.session_id}</span>
                  </Command.Item>
                ))}
              </Command.Group>
            )}

            {user && (
              <Command.Group heading={t("components.commandPalette.account", "Account")} className={group}>
                <Command.Item value="profile 资料" onSelect={run(() => navigate("/app/profile"))} className={item}>
                  <UserIcon className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                  {t("pages.profile.title", "Profile")}
                </Command.Item>
                <Command.Item
                  value="change password 修改密码"
                  onSelect={run(() => navigate("/app/change-password"))}
                  className={item}
                >
                  <KeyRound className="size-3.5 shrink-0 text-brand-accent" aria-hidden="true" />
                  {t("pages.changePassword.title", "Change password")}
                </Command.Item>
                {onLogout && (
                  <Command.Item
                    value="sign out 退出"
                    onSelect={run(onLogout)}
                    className={cn(item, "text-danger data-[selected=true]:bg-danger-surface data-[selected=true]:text-danger")}
                  >
                    <LogOut className="size-3.5 shrink-0" aria-hidden="true" />
                    {t("common.logout", "Sign out")}
                  </Command.Item>
                )}
              </Command.Group>
            )}
          </Command.List>
        </Command>
      </div>
    </>
  );
}

/** The key hint on the right of a row. Space-separated, one `<kbd>` each. */
function Shortcut({ keys }: Readonly<{ keys: string }>) {
  return (
    <span className="ml-auto flex shrink-0 items-center gap-1">
      {keys.split(" ").map((k) => (
        <kbd key={k} className="rounded border border-line bg-surface-muted px-1.5 py-0.5 font-mono text-xs font-semibold text-ink/80">
          {k}
        </kbd>
      ))}
    </span>
  );
}
