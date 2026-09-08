import { useChatStore } from "@/stores/useChatStore";

/**
 * One definition of "toggle the session sidebar".
 *
 * Below the sidebar breakpoint the panel is an off-canvas drawer driven by
 * `sidebarOpen`; above it, an in-flow column driven by `sidebarCollapsed`. One
 * gesture, two mechanisms -- the same split `ChatSidebar` renders against.
 *
 * It lives here rather than inside `TopNav` because the top bar's button, the
 * `Ctrl+B` shortcut and the command palette all mean the same thing by it, and
 * three copies of that `innerWidth` check would be three chances to disagree.
 */
export function useSidebarToggle() {
  const setSidebarOpen = useChatStore((s) => s.setSidebarOpen);
  const setSidebarCollapsed = useChatStore((s) => s.setSidebarCollapsed);

  return () => {
    if (window.innerWidth <= 1080) {
      setSidebarOpen((open) => !open);
    } else {
      setSidebarCollapsed((collapsed) => !collapsed);
    }
  };
}
