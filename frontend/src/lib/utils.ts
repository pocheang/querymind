import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge class names, letting a later Tailwind utility win over an earlier one
 * in the same group.
 *
 * `clsx` flattens the conditional forms; `twMerge` is what makes a component's
 * default overridable from its call site -- `<Button className="rounded-none">`
 * has to drop the variant's `rounded-control`, and plain concatenation would
 * leave both and let source order decide.
 *
 * This is why the Tailwind prefix was dropped in the same commit that added
 * this file: `twMerge` parses class names against Tailwind's own group table
 * and does not recognise a `tw:` prefix, so with one configured every merge
 * here would have silently degraded to concatenation.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
