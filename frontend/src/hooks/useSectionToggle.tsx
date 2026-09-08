import { useEffect, useState } from "react";

/**
 * Whether the chat page's auxiliary sections (runtime panels and the composer)
 * are hidden.
 *
 * This used to reach into the document itself -- `querySelectorAll(
 * ".execution-trace-panel, .tool-approval-panel, .composer-panel")` followed by
 * `classList.add("hidden")` -- so React never owned those class names and
 * renaming any of them broke the feature with no compile error and no test.
 * It returns state now, and `ChatPage` decides what to render.
 *
 * The companion `useTopbarToggle` went with the zero-height `ChatTopbar` it
 * was written for; the shell's top bar is not hideable.
 */
export function useSectionToggle() {
  const [sectionsHidden, setSectionsHidden] = useState(() => {
    try {
      return localStorage.getItem("chatSectionsHidden") === "true";
    } catch {
      // Private windows throw on read, not only on write.
      return false;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("chatSectionsHidden", String(sectionsHidden));
    } catch {
      // A remembered layout preference is a convenience; losing it must not
      // take the page down with it.
    }
  }, [sectionsHidden]);

  const toggleSections = () => setSectionsHidden((previous) => !previous);

  return { sectionsHidden, toggleSections };
}
