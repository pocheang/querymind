import type React from "react";
import { useTranslation } from "react-i18next";

import { CHAT_ACCEPT_RE, UPLOAD_ACCEPT_RE, partitionUploads } from "@/lib/uploadFormats";

interface UseFileUploadProps {
  canUploadAndManageDocs: boolean;
  setDocDropActive: (active: boolean) => void;
  setComposerDropActive: (active: boolean) => void;
  notify: (message: string, type: "success" | "warn" | "error") => void;
  uploadFiles: (files: File[]) => Promise<void>;
}

export function useFileUpload({
  canUploadAndManageDocs,
  setDocDropActive,
  setComposerDropActive,
  notify,
  uploadFiles,
}: UseFileUploadProps) {
  const { t } = useTranslation();

  /**
   * Upload what is accepted and SAY what was not.
   *
   * Each caller used to warn only when every file had been rejected
   * (`if (!files.length)`), so a `.docx` dropped beside two PDFs uploaded the
   * PDFs and lost the third without a word. And the three messages were
   * hardcoded English in a bilingual application.
   */
  const uploadAccepted = async (files: File[], pattern: RegExp, hintKey: string) => {
    const { accepted, rejected } = partitionUploads(files, pattern);
    if (rejected.length) {
      notify(t(hintKey, { files: rejected.join("、") }), "warn");
    }
    if (!accepted.length) return;
    await handleUploadFiles(accepted);
  };

  const handleUploadFiles = async (files: File[]) => {
    if (!files.length) return;
    if (!canUploadAndManageDocs) {
      notify(t("chat.upload.permissionDenied"), "warn");
      return;
    }
    await uploadFiles(files);
  };

  const onMainUploadChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
    await handleUploadFiles(Array.from(evt.target.files || []));
  };

  const onChatUploadChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
    await uploadAccepted(Array.from(evt.target.files || []), CHAT_ACCEPT_RE, "chat.upload.chatOnly");
  };

  const onDocsDrop = async (evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    evt.stopPropagation();
    setDocDropActive(false);
    await uploadAccepted(Array.from(evt.dataTransfer.files || []), UPLOAD_ACCEPT_RE, "chat.upload.docsOnly");
  };

  const onComposerDrop = async (evt: React.DragEvent<HTMLElement>) => {
    evt.preventDefault();
    evt.stopPropagation();
    setComposerDropActive(false);
    await uploadAccepted(Array.from(evt.dataTransfer.files || []), CHAT_ACCEPT_RE, "chat.upload.chatOnly");
  };

  return {
    onMainUploadChange,
    onChatUploadChange,
    onDocsDrop,
    onComposerDrop,
  };
}
