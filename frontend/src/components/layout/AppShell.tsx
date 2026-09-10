import { useCallback, useState, type ReactNode } from "react";

import { cn } from "@/lib/utils";
import { CommandPalette } from "@/components/CommandPalette";
import { KeyboardHelp } from "@/components/KeyboardHelp";
import { useAppShortcuts } from "@/hooks/useAppShortcuts";
import { TopNav, type TopNavProps } from "./TopNav";

export type { UserIdentity } from "@/types/auth";

export type AppShellProps = TopNavProps & {
  children: ReactNode;
  /** Let a route opt out of the shell's own scrolling (the chat view scrolls internally). */
  scroll?: boolean;
  className?: string;
  /** Chat supplies this; the palette and Ctrl+N offer it only when it exists. */
  onNewSession?: () => void;
};

/**
 * The one frame every signed-in view renders inside: aurora ground, glass top
 * bar, then the route's own content.
 *
 * The design prototype switched between five views by toggling a `hidden`
 * class on five sibling divs; here those are five routes under this shell, so
 * the nav pills are `NavLink`s and browser history keeps working. The mapping
 * is one to one -- deck/`/app`, analytics, admin, architecture, landing.
 *
 * `overflow-hidden` on the frame with `min-h-0` on the content is what lets a
 * child scroll instead of the document. An unbounded box cannot scroll, which
 * is the box-model error that previously made the whole page scroll behind a
 * fixed sidebar.
 */
export function AppShell({
  children,
  scroll = false,
  className,
  onNewSession,
  ...nav
}: Readonly<AppShellProps>) {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);

  // Stable identities: `useAppShortcuts` re-binds its listener when these
  // change, and an inline arrow would re-bind on every render.
  const openPalette = useCallback(() => setPaletteOpen(true), []);
  const openShortcuts = useCallback(() => {
    setPaletteOpen(false);
    setShortcutsOpen(true);
  }, []);

  useAppShortcuts({
    onCommandPalette: openPalette,
    onShortcutHelp: openShortcuts,
    onNewSession,
  });

  return (
    <div className="flex h-screen flex-col overflow-hidden text-ink">
      <TopNav {...nav} onOpenCommandPalette={openPalette} onOpenShortcuts={openShortcuts} />
      <main className={cn("flex min-h-0 flex-1 flex-col", scroll ? "overflow-y-auto" : "overflow-hidden", className)}>
        {children}
      </main>

      <CommandPalette
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        user={nav.user}
        onLogout={nav.onLogout}
        onOpenSettings={nav.onOpenSettings}
        onOpenSessionManagement={nav.onOpenSessionManagement}
        onOpenShortcuts={openShortcuts}
        onNewSession={onNewSession}
      />
      <KeyboardHelp open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />
    </div>
  );
}

/**
 * A conventional page header for the routes that are just content: analytics,
 * architecture, profile. The chat view does not use it -- it has its own
 * stream header.
 */
export function PageHeader({
  title,
  description,
  actions,
}: Readonly<{ title: ReactNode; description?: ReactNode; actions?: ReactNode }>) {
  return (
    <div className="glass-panel flex shrink-0 flex-wrap items-center justify-between gap-3 border-x-0 border-t-0 px-4 py-3">
      <div className="min-w-0">
        <h1 className="text-sm font-bold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-0.5 text-[11px] text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-1.5">{actions}</div>}
    </div>
  );
}
