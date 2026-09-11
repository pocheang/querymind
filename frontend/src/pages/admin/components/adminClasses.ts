/**
 * The console's shared class strings.
 *
 * A separate module from `AdminPrimitives.tsx` for the reason recorded in
 * CLAUDE.md: `react-refresh/only-export-components` allows a component file to
 * export literal constants and nothing else, and both of the table strings are
 * built by a `.join()` -- a call expression, which warns. The repository
 * already splits `cva()` tables out this way (`animatedButtonVariants.ts`,
 * `effectiveComponentVariants.ts`); this is the same rule applied to plain
 * class strings.
 */

/**
 * The console's field styling, as one string rather than pasted into every
 * control. Native `<select>`/`<input>` stay native here: these forms carry
 * long option lists that the platform control handles better on a phone.
 */
export const ADMIN_FIELD =
  "h-8 w-full rounded-control border border-brand-border bg-surface px-2.5 text-xs text-ink " +
  "placeholder:text-ink-faint transition-colors focus-visible:border-brand-accent focus-visible:outline-none " +
  "focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:cursor-not-allowed disabled:opacity-60";

/** The taller variant the filter grids use, where a field owns its own row. */
export const ADMIN_FIELD_TALL = ADMIN_FIELD.replace("h-8", "min-h-10 py-2");

/**
 * The console's data table.
 *
 * Table styling is descendant styling by nature -- a component per cell would
 * mean touching several hundred `<td>`s across five tables -- so this is one
 * class string of arbitrary variants rather than a wrapper per element. It
 * still lands in the `utilities` layer and still merges through `cn()`.
 */
export const ADMIN_TABLE = [
  "w-full border-separate border-spacing-0 overflow-hidden rounded-card text-left",
  "[&_thead_th]:border-b-2 [&_thead_th]:border-brand-border [&_thead_th]:bg-brand-surface",
  "[&_thead_th]:font-mono [&_thead_th]:text-xs [&_thead_th]:font-extrabold",
  "[&_thead_th]:uppercase [&_thead_th]:tracking-wider [&_thead_th]:text-ink/80 [&_thead_th]:text-left",
  "[&_td]:border-b [&_td]:border-line [&_td]:px-3 [&_td]:py-2.5 [&_td]:text-xs [&_td]:text-ink",
  "[&_th]:px-3 [&_th]:py-2.5 [&_th]:text-xs",
  "[&_tbody_tr]:transition-colors [&_tbody_tr:hover]:bg-brand-surface/70",
  "[&_tbody_tr:last-child>td]:border-b-0",
].join(" ");

/** The horizontally scrolling frame a wide table sits in. */
export const ADMIN_TABLE_WRAP = "glass-card w-full overflow-x-auto overflow-y-hidden rounded-card";

/**
 * A wide table inside that frame: fixed layout so the header row decides the
 * column widths, zebra rows, and a header that stays put while it scrolls.
 */
export const ADMIN_TABLE_WIDE = [
  "table-fixed",
  "[&_thead_th]:sticky [&_thead_th]:top-0 [&_thead_th]:z-[2]",
  "[&_tbody_tr:nth-child(2n)]:bg-brand-surface/35",
  "[&_th]:whitespace-nowrap [&_td]:overflow-hidden [&_td]:text-ellipsis [&_td]:whitespace-nowrap",
].join(" ");

/** A monospace chip for an id, an action name or a resource type. */
export const ADMIN_CODE =
  "inline-block max-w-full overflow-hidden text-ellipsis whitespace-nowrap rounded border " +
  "border-line-strong bg-brand-surface-hover px-2.5 py-0.5 align-middle font-mono text-xs font-medium text-ink";

/**
 * recharts writes its chrome as SVG attributes and inline styles, so its
 * colours are props rather than classes and have to name the CSS variables
 * directly. One definition, because five dashboards were repeating it.
 */
export const CHART_TOOLTIP = {
  background: "var(--surface)",
  border: "1px solid var(--border-medium)",
  borderRadius: "var(--shape-control)",
};

export const CHART_GRID = "var(--border-light)";
export const CHART_AXIS = "var(--text-tertiary)";
