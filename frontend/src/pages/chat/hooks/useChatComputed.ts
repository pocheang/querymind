import { useMemo } from "react";
import type { IndexedFileSummary } from "@/types/api";
import { PDF_FILE_RE } from "@/pages/chat/constants";

interface UseChatComputedParams {
  documents: IndexedFileSummary[];
  user: { username: string; role: string } | null;
}

export function useChatComputed({ documents, user }: UseChatComputedParams) {
  const role = (user?.role || "viewer").toLowerCase();
  const isAdmin = role === "admin";
  const canUploadAndManageDocs = true;
  const userBadge = user ? `${user.username} (${role})` : "unknown";

  const pdfDocuments = useMemo(
    () => documents.filter((doc) => PDF_FILE_RE.test(doc.filename || "")),
    [documents]
  );

  const pdfNeedingReindex = useMemo(
    () => pdfDocuments.filter((doc) => (doc.chunks || 0) <= 0),
    [pdfDocuments]
  );

  const agentDistribution = useMemo(() => {
    const counts = new Map<string, number>();
    for (const doc of documents) {
      const key = (doc.agent_class || "general").trim() || "general";
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    return Array.from(counts.entries())
      .map(([agent, count]) => ({ agent, count }))
      .sort((a, b) => b.count - a.count);
  }, [documents]);

  return {
    role,
    isAdmin,
    canUploadAndManageDocs,
    userBadge,
    pdfDocuments,
    pdfNeedingReindex,
    agentDistribution,
  };
}
