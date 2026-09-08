import { useTranslation } from "react-i18next";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  Globe,
  KeyRound,
  Keyboard,
  LogOut,
  MessageSquare,
  PanelLeft,
  Search,
  Settings,
  Settings2,
  User as UserIcon,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { LanguageToggle } from "@/components/LanguageToggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { getPermissionCheck, RoleBadge } from "@/hooks/usePermissions";
import { useSidebarToggle } from "@/hooks/useSidebarToggle";
import type { UserIdentity } from "@/types/auth";
import { BrandMark } from "./BrandMark";
import { TopNavMetrics } from "./TopNavMetrics";

export type TopNavProps = {
  user: UserIdentity | null;
  onLogout?: () => void;
  onOpenSettings?: () => void;
  onOpenSessionManagement?: () => void;
  /** Supplied by AppShell, which owns the palette and the shortcut sheet. */
  onOpenCommandPalette?: () => void;
  onOpenShortcuts?: () => void;
};

/**
 * The 56px glass bar the whole app hangs from.
 *
 * It replaces `ChatTopbar`, which was a `height: 0`, `pointer-events: none`
 * fixed layer at `z-index: 10000` holding two absolutely-positioned islands
 * of buttons. Its own comment recorded the consequence: below 1080px nothing
 * rendered a control to reopen the sidebar, so the session list, history and
 * document tools were simply unreachable. The toggle here is a real button in
 * normal flow, visible at every width.
 *
 * The z-index ladder is the design prototype's: backdrop 20, sidebar 30,
 * this bar 40, modals and toasts 50.
 */
export function TopNav({
  user,
  onLogout,
  onOpenSettings,
  onOpenSessionManagement,
  onOpenCommandPalette,
  onOpenShortcuts,
}: Readonly<TopNavProps>) {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const permissions = getPermissionCheck(user);

  // The sidebar belongs to the chat view; on every other route the toggle
  // would control nothing.
  const onChat = location.pathname === "/app";
  const toggleSidebar = useSidebarToggle();

  const views = [
    { to: "/app", icon: MessageSquare, label: t("nav.deck", "Operations Deck"), show: !!user },
    {
      to: "/app/analytics",
      icon: BarChart3,
      label: t("nav.analytics", "Analytics"),
      show: permissions.canViewAnalytics,
    },
    { to: "/app/admin", icon: Settings2, label: t("nav.admin", "Admin Console"), show: permissions.canAccessAdmin },
    { to: "/app/architecture", icon: Boxes, label: t("nav.architecture", "Architecture"), show: true },
    { to: "/", icon: Globe, label: t("nav.landing", "Showcase"), show: true },
  ].filter((v) => v.show);

  return (
    <header className="glass-panel z-40 flex h-14 shrink-0 select-none items-center justify-between gap-3 border-x-0 border-t-0 px-3 shadow-elev-1">
      <div className="flex min-w-0 items-center gap-2">
        {onChat && (
          <Button variant="ghost" size="icon" onClick={toggleSidebar} title={t("components.chat.toggleSidebar")}>
            <PanelLeft aria-hidden="true" />
            <span className="sr-only">{t("components.chat.toggleSidebar")}</span>
          </Button>
        )}

        <button
          type="button"
          onClick={() => navigate(user ? "/app" : "/")}
          className="flex items-center gap-2.5 rounded-control p-0.5 text-left transition-colors hover:bg-brand-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
        >
          <BrandMark />
          <span className="hidden min-w-0 sm:block">
            <span className="flex items-center gap-1.5">
              <span className="text-sm font-bold tracking-tight text-ink">QueryMind</span>
              <Badge variant="brand" size="xs" className="uppercase tracking-wider">
                NextGen
              </Badge>
            </span>
            <span className="mt-0.5 block text-[10px] leading-none text-ink-muted">
              {t("app.tagline", "Multi-Agent RAG Operations Deck")}
            </span>
          </span>
        </button>

        <nav className="ml-2 hidden items-center gap-0.5 rounded-control border border-line bg-surface-muted p-1 md:flex">
          {views.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-1.5 rounded-control px-2.5 py-1 text-[11px] font-medium transition-all",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]",
                  isActive
                    ? "bg-[image:var(--brand-gradient)] font-semibold text-white shadow-elev-1"
                    : "text-ink-muted hover:text-brand-text"
                )
              }
            >
              <Icon className="size-3.5" aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {permissions.canViewAnalytics && <TopNavMetrics />}
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {/* The prototype's ⌘K and shortcut-help triggers. Both were missing:
            the palette did not exist and the sheet could only be reached by a
            key nothing told the reader about. */}
        {onOpenCommandPalette && (
          <Button
            variant="ghost"
            size="sm"
            className="gap-1.5 px-2"
            onClick={onOpenCommandPalette}
            title={t("components.commandPalette.open", "Command palette (Ctrl+K)")}
          >
            <Search className="size-3.5" aria-hidden="true" />
            <kbd className="hidden rounded border border-line bg-surface-muted px-1 py-0.5 font-mono text-[10px] text-ink-muted sm:inline">
              ⌘K
            </kbd>
            <span className="sr-only">{t("components.commandPalette.open", "Command palette")}</span>
          </Button>
        )}
        {onOpenShortcuts && (
          <Button
            variant="ghost"
            size="icon"
            onClick={onOpenShortcuts}
            title={t("components.keyboard.title", "Keyboard shortcuts")}
          >
            <Keyboard className="size-3.5" aria-hidden="true" />
            <span className="sr-only">{t("components.keyboard.title", "Keyboard shortcuts")}</span>
          </Button>
        )}

        <LanguageToggle />

        {user ? (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex items-center gap-2 rounded-control p-0.5 transition-colors hover:bg-brand-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
              >
                <Avatar className="size-7">
                  <AvatarFallback>{user.username.slice(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>
                <span className="hidden text-[11px] font-semibold text-ink md:inline">{user.username}</span>
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-52">
              <DropdownMenuLabel className="flex items-center gap-2 normal-case">
                <span className="text-xs font-bold tracking-normal text-ink">{user.username}</span>
                <RoleBadge role={user.role} />
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate("/app/profile")}>
                <UserIcon aria-hidden="true" />
                {t("pages.profile.title", "Profile")}
              </DropdownMenuItem>
              {onOpenSettings && (
                <DropdownMenuItem onSelect={onOpenSettings}>
                  <Settings aria-hidden="true" />
                  {t("components.chat.settings", "Settings")}
                </DropdownMenuItem>
              )}
              {onOpenSessionManagement && (
                <DropdownMenuItem onSelect={onOpenSessionManagement}>
                  <Boxes aria-hidden="true" />
                  {t("sessionManagement.title", "Session management")}
                </DropdownMenuItem>
              )}
              <DropdownMenuItem onSelect={() => navigate("/app/change-password")}>
                <KeyRound aria-hidden="true" />
                {t("pages.changePassword.title", "Change password")}
              </DropdownMenuItem>
              {onLogout && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem destructive onSelect={onLogout}>
                    <LogOut aria-hidden="true" />
                    {t("common.logout", "Sign out")}
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <Button size="sm" onClick={() => navigate("/app/login")}>
            {t("auth.signIn", "Sign in")}
          </Button>
        )}
      </div>
    </header>
  );
}
