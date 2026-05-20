/**
 * Downloads content as a file in the browser
 * @param content - The file content (string or Blob)
 * @param filename - The filename to save as
 * @param mimeType - MIME type (e.g., 'text/csv', 'text/markdown')
 */
export function downloadFile(content: string | Blob, filename: string, mimeType: string): void {
  const blob = content instanceof Blob ? content : new Blob([content], { type: `${mimeType};charset=utf-8;` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

/**
 * Generates a timestamped filename
 * @param prefix - Filename prefix
 * @param extension - File extension (without dot)
 * @returns Filename with ISO timestamp
 */
export function generateTimestampedFilename(prefix: string, extension: string): string {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `${prefix}_${timestamp}.${extension}`;
}
