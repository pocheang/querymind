import { authRequest, buildQueryString } from "./api-client";

export function encodePathParam(value: string): string {
  return encodeURIComponent(value);
}

export function buildPatchRequest<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<T> {
  return authRequest<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function buildPostRequest<T>(
  path: string,
  body: Record<string, unknown>,
): Promise<T> {
  return authRequest<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function buildGetRequest<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
): Promise<T> {
  const qs = params ? buildQueryString(params) : "";
  const fullPath = qs ? `${path}?${qs}` : path;
  return authRequest<T>(fullPath);
}

export { buildQueryString };
