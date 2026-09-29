import { useQuery } from "@tanstack/react-query";
import { appApi } from "@/lib/api";

export const DOCUMENTS_QUERY_KEY = ["documents"] as const;

export function fetchDocuments() {
  return appApi.documents();
}

/** The documents the caller may see. `docsLoading` is true only until the first answer. */
export function useDocuments() {
  const query = useQuery({ queryKey: DOCUMENTS_QUERY_KEY, queryFn: fetchDocuments });
  return { documents: query.data ?? [], docsLoading: query.isPending };
}
