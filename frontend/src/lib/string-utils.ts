/**
 * Normalize user input by trimming whitespace
 */
export function normalizeInput(value: string): string {
  return value.trim();
}

/**
 * Normalize filter input (trim and lowercase for case-insensitive matching)
 */
export function normalizeFilter(value: string): string {
  return value.trim().toLowerCase();
}

/**
 * Check if a string is empty after normalization
 */
export function isEmptyInput(value: string): boolean {
  return value.trim() === "";
}

/**
 * Normalize and validate non-empty input
 * Returns normalized value or undefined if empty
 */
export function normalizeNonEmpty(value: string): string | undefined {
  const normalized = value.trim();
  return normalized === "" ? undefined : normalized;
}
