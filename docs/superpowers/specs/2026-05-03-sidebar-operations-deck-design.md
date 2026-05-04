# Sidebar Operations Deck Design

## Goal

Refresh the chat page left sidebar so it visually matches the provided dark operations deck reference while preserving the current chat, session, workbench, and account behavior.

## Scope

- Keep the current React data flow and handlers unchanged.
- Refine the expanded sidebar only; the compact rail remains compatible with the same brand and account controls.
- Update sidebar styling in the existing sidebar CSS modules instead of introducing a new design system.
- Improve session rows with a compact action-row feel, stronger active state, subtle icons, metadata chips, and clearer destructive actions.
- Align the workbench modules and footer with the same glassy blue-violet control-surface language.

## Design Direction

The sidebar should feel like a dense command deck: dark layered panels, thin borders, soft inner highlights, restrained blue and violet accents, and small uppercase section labels. The reference image is compact and practical, so the implementation should prioritize scanability over decorative weight.

## Components

- `ChatSidebar.tsx`: add small visual affordances around the brand and user action controls without changing props.
- `SessionList.tsx`: add a new-session command row and per-session icon/time metadata structure.
- `modern-layout.css`, `modern-sessions.css`, `modules.css`, `footer.css`, `actions.css`: tune surface colors, spacing, borders, hover states, active glow, and responsive behavior.

## Verification

- Run the frontend build to catch TypeScript and CSS import regressions.
- If possible, start Vite and inspect the chat page manually at desktop and mobile widths.
