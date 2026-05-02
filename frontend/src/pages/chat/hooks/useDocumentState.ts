import { useState } from "react";
import type { IndexedFileSummary } from "@/types/api";

export function useDocumentState() {
  const [documents, setDocuments] = useState<IndexedFileSummary[]>([]);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadInfo, setUploadInfo] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadProgressText, setUploadProgressText] = useState("");
  const [uploadVisibility, setUploadVisibility] = useState<"private" | "public">("private");
  const [docDropActive, setDocDropActive] = useState(false);

  return {
    documents,
    setDocuments,
    docsLoading,
    setDocsLoading,
    uploading,
    setUploading,
    uploadInfo,
    setUploadInfo,
    uploadProgress,
    setUploadProgress,
    uploadProgressText,
    setUploadProgressText,
    uploadVisibility,
    setUploadVisibility,
    docDropActive,
    setDocDropActive,
  };
}

export type DocumentState = ReturnType<typeof useDocumentState>;
