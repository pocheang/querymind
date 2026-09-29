import { useQuery } from "@tanstack/react-query";
import { appApi } from "@/lib/api";

export const PROMPTS_QUERY_KEY = ["prompts"] as const;

export function fetchPrompts() {
  return appApi.prompts();
}

/** The caller's saved prompt templates. `promptsLoading` is true only until the first answer arrives. */
export function usePrompts() {
  const query = useQuery({ queryKey: PROMPTS_QUERY_KEY, queryFn: fetchPrompts });
  return { prompts: query.data ?? [], promptsLoading: query.isPending };
}
