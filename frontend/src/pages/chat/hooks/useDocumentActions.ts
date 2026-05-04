import type { Dispatch, SetStateAction } from "react";
import { appApi } from "@/lib/api";
import type { IndexedFileSummary } from "@/types/api";

type AgentClassHint = "" | "general" | "cybersecurity" | "artificial_intelligence" | "pdf_text";

interface UseDocumentActionsParams {
  setDocuments: Dispatch<SetStateAction<IndexedFileSummary[]>>;
  setDocsLoading: Dispatch<SetStateAction<boolean>>;
  setUploading: Dispatch<SetStateAction<boolean>>;
  setUploadInfo: Dispatch<SetStateAction<string>>;
  setUploadProgress: Dispatch<SetStateAction<number>>;
  setUploadProgressText: Dispatch<SetStateAction<string>>;
  setAgentClassHint: Dispatch<SetStateAction<AgentClassHint>>;
  setError: Dispatch<SetStateAction<string>>;
  uploadVisibility: "private" | "public";
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  chatUploadInputRef: React.RefObject<HTMLInputElement | null>;
  notify: (text: string, kind?: "info" | "success" | "warn" | "error", ttl?: number) => void;
  handleApiError: (e: unknown, fallback: string) => Promise<void>;
}

export function useDocumentActions(params: UseDocumentActionsParams) {
  const {
    setDocuments,
    setDocsLoading,
    setUploading,
    setUploadInfo,
    setUploadProgress,
    setUploadProgressText,
    setAgentClassHint,
    setError,
    uploadVisibility,
    fileInputRef,
    chatUploadInputRef,
    notify,
    handleApiError,
  } = params;

  const refreshDocuments = async (silent = false) => {
    if (!silent) setDocsLoading(true);
    try {
      const rows = await appApi.documents();
      setDocuments(rows);
      setError("");
    } catch (e) {
      await handleApiError(e, "Failed to load documents");
    } finally {
      if (!silent) setDocsLoading(false);
    }
  };

  const uploadFiles = async (files: File[]) => {
    if (!files.length) return;
    try {
      setUploading(true);
      setUploadProgress(0);
      setUploadProgressText("Preparing upload...");
      setUploadInfo("Uploading...");
      const data = await appApi.upload(
        files,
        (percent) => {
          setUploadProgress(percent);
          setUploadProgressText(`Uploading ${Math.round(percent)}%`);
        },
        uploadVisibility,
      );
      setUploadProgress(100);
      setUploadProgressText("Upload complete");

      const uploadSummary = [];
      uploadSummary.push(`✓ 已上传 ${data.loaded_documents} 个文件`);
      if (data.chunks_indexed > 0) {
        uploadSummary.push(`索引了 ${data.chunks_indexed} 个文本块`);
      }
      if (data.pages_by_source && Object.keys(data.pages_by_source).length > 0) {
        const totalPages = Object.values(data.pages_by_source).reduce((a, b) => a + b, 0);
        uploadSummary.push(`共 ${totalPages} 页`);
      }
      if (data.triplets_written > 0) {
        uploadSummary.push(`提取了 ${data.triplets_written} 个知识三元组`);
      }
      if (data.skipped_files && data.skipped_files.length > 0) {
        uploadSummary.push(`跳过: ${data.skipped_files.join(", ")}`);
      }

      setUploadInfo(uploadSummary.join(" | "));
      const classes = Object.values(data.assigned_agent_classes || {}).filter(Boolean);
      if (classes.length > 0) {
        const unique = Array.from(new Set(classes));
        if (unique.length === 1) setAgentClassHint((unique[0] as AgentClassHint) || "");
      }
      notify(uploadSummary.join(" | "), "success", 4000);
      await refreshDocuments();
    } catch (e) {
      setUploadInfo(`Upload failed: ${e instanceof Error ? e.message : "unknown error"}`);
      await handleApiError(e, "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      if (chatUploadInputRef.current) chatUploadInputRef.current.value = "";
      window.setTimeout(() => {
        setUploadProgress(0);
        setUploadProgressText("");
      }, 900);
    }
  };

  const deleteDocument = async (item: IndexedFileSummary, removeFile: boolean) => {
    const verb = removeFile ? "Delete file and index" : "Delete index";
    if (!window.confirm(`${verb}: ${item.filename} ?`)) return;
    try {
      const res = await appApi.documentDelete(item.filename, item.source, removeFile);
      setUploadInfo(
        `${item.filename}: chunks_removed=${res.chunks_removed}, triplets_removed=${res.triplets_removed}, file_removed=${res.file_removed}`,
      );
      notify(`${item.filename} deleted`, "success");
      await refreshDocuments();
    } catch (e) {
      await handleApiError(e, "Failed to delete document");
    }
  };

  const reindexDocument = async (item: IndexedFileSummary) => {
    try {
      const res = await appApi.documentReindex(item.filename, item.source);

      const reindexSummary = [`✓ ${item.filename} 重新索引完成`];
      if (res.chunks_indexed && res.chunks_indexed > 0) {
        reindexSummary.push(`${res.chunks_indexed} 个文本块`);
      }
      if (res.pages_by_source && Object.keys(res.pages_by_source).length > 0) {
        const totalPages = Object.values(res.pages_by_source).reduce((a, b) => a + b, 0);
        reindexSummary.push(`${totalPages} 页`);
      }
      if (res.triplets_written && res.triplets_written > 0) {
        reindexSummary.push(`${res.triplets_written} 个知识三元组`);
      }

      setUploadInfo(reindexSummary.join(" - "));
      notify(reindexSummary.join(" - "), "success", 3000);
      await refreshDocuments();
    } catch (e) {
      await handleApiError(e, "Failed to reindex document");
    }
  };

  return {
    refreshDocuments,
    uploadFiles,
    deleteDocument,
    reindexDocument,
  };
}
