/**
 * What each upload surface may offer, in one place.
 *
 * There were FOUR lists and they disagreed with each other and with the server:
 * two `accept` attributes (`ChatComposer`, `DocumentsPanel`) and two regexes in
 * `useFileUpload` that silently filter what the pickers hand over. The endpoint
 * accepts `.txt`, `.md`, `.pdf`, eight image types and four Office formats; no
 * picker offered a `.docx`, and the composer's hint read "Supports PDF / images
 * / text" over a picker that greyed out `.md`.
 *
 * There are legitimately TWO sets, and collapsing them was the first attempt's
 * mistake: widening the composer's `accept` to everything the server takes made
 * it offer files that `SUPPORTED_CHAT_RE` then discarded without a word.
 *
 *   KNOWLEDGE_BASE  everything the server will index
 *   CHAT_ATTACHMENT the subset a question can be asked *about* -- documents you
 *                   read visually, which is what the composer is for
 *
 * An `accept` list is never a safety measure: `store_uploaded_files` validates
 * the suffix server-side regardless. It is a promise to whoever is choosing a
 * file, and a wrong one silently costs them the file.
 *
 * `tests/api/test_upload_formats_agree.py` compares both against the endpoint's
 * set and asserts the subset relation, because four lists that must agree with
 * nothing checking them is how the first two came apart.
 */

/** Everything `POST /documents/upload` will accept. */
export const ACCEPTED_UPLOAD_EXTENSIONS = [
  ".txt",
  ".md",
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".bmp",
  ".tif",
  ".tiff",
  ".webp",
  ".gif",
  ".docx",
  ".pptx",
  ".xlsx",
  ".xls",
] as const;

/**
 * What may be attached to a question. A strict subset: the composer is for
 * documents a reader looks at, and the Knowledge Base is the place for a corpus.
 */
export const CHAT_ATTACHMENT_EXTENSIONS = [
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".bmp",
  ".tif",
  ".tiff",
  ".webp",
  ".gif",
] as const;

const acceptAttribute = (extensions: readonly string[]) => extensions.join(",");

/** Turn a list into the matcher `useFileUpload` filters with, so the picker and
 *  the handler cannot disagree about one file. */
const matcher = (extensions: readonly string[]) =>
  new RegExp(`(${extensions.map((e) => e.replace(".", String.raw`\.`)).join("|")})$`, "i");

export const UPLOAD_ACCEPT_ATTRIBUTE = acceptAttribute(ACCEPTED_UPLOAD_EXTENSIONS);
export const CHAT_ACCEPT_ATTRIBUTE = acceptAttribute(CHAT_ATTACHMENT_EXTENSIONS);

export const UPLOAD_ACCEPT_RE = matcher(ACCEPTED_UPLOAD_EXTENSIONS);
export const CHAT_ACCEPT_RE = matcher(CHAT_ATTACHMENT_EXTENSIONS);

/**
 * Split a drop or a picker selection into what will be uploaded and what will
 * not.
 *
 * The callers used to test `if (!files.length)` and warn only when *every* file
 * was rejected -- so dropping a `.docx` beside two PDFs uploaded the PDFs and
 * lost the third silently. Returning the rejected names lets the notice say
 * which ones, which is the difference between a warning and an explanation.
 */
export function partitionUploads(
  files: readonly File[],
  pattern: RegExp
): { accepted: File[]; rejected: string[] } {
  const accepted: File[] = [];
  const rejected: string[] = [];
  for (const file of files) {
    if (pattern.test(file.name)) accepted.push(file);
    else rejected.push(file.name);
  }
  return { accepted, rejected };
}
