import { cn } from "@/lib/utils";

/**
 * The three states a form field's validation hint can be in.
 *
 * `LoginPage` and `ChangePasswordPage` each carried their own `hintClass` --
 * byte-identical, including the comment above it -- and then wrote the same
 * three-way choice again inline for every field's message, as a nested ternary.
 * Five of the eight `typescript:S3358` findings were that one pattern.
 *
 * A state plus a lookup says it once. It is deliberately NOT a component: the
 * message for each state is a literal `t("...")` call at the call site, because
 * `i18n/locales.test.ts` scans for exactly that form and a key assembled any
 * other way is invisible to it -- which is how thirteen keys once went missing
 * from both locales at the same time.
 */
export type FieldHintState = "untouched" | "valid" | "invalid";

export function fieldHintState(touched: boolean, valid: boolean): FieldHintState {
  if (!touched) return "untouched";
  return valid ? "valid" : "invalid";
}

const TONE: Record<FieldHintState, string> = {
  untouched: "text-ink-muted",
  valid: "text-success",
  invalid: "text-danger",
};

export function fieldHintClass(state: FieldHintState): string {
  return cn("text-xs font-medium", TONE[state]);
}
