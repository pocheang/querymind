import type React from "react";
import { SUPPORTED_CHAT_RE, SUPPORTED_DOC_RE } from "@/pages/chat/constants";

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
  const handleUploadFiles = async (files: File[]) => {
    if (!files.length) return;
    if (!canUploadAndManageDocs) {
      notify("Upload permission denied", "warn");
      return;
    }
    await uploadFiles(files);
  };

  const onMainUploadChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
    await handleUploadFiles(Array.from(evt.target.files || []));
  };

  const onChatUploadChange = async (evt: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(evt.target.files || []).filter((f) => SUPPORTED_CHAT_RE.test(f.name));
    if (!files.length) {
      notify("This area supports PDF/image files only", "warn");
      return;
    }
    await handleUploadFiles(files);
  };

  const onDocsDrop = async (evt: React.DragEvent<HTMLDivElement>) => {
    evt.preventDefault();
    evt.stopPropagation();
    setDocDropActive(false);
    const files = Array.from(evt.dataTransfer.files || []).filter((f) => SUPPORTED_DOC_RE.test(f.name));
    if (!files.length) {
      notify("Only .md / .txt / .pdf / image files are supported", "warn");
      return;
    }
    await handleUploadFiles(files);
  };

  const onComposerDrop = async (evt: React.DragEvent<HTMLElement>) => {
    evt.preventDefault();
    evt.stopPropagation();
    setComposerDropActive(false);
    const files = Array.from(evt.dataTransfer.files || []).filter((f) => SUPPORTED_CHAT_RE.test(f.name));
    if (!files.length) {
      notify("This area supports PDF/image files only", "warn");
      return;
    }
    await handleUploadFiles(files);
  };

  return {
    onMainUploadChange,
    onChatUploadChange,
    onDocsDrop,
    onComposerDrop,
  };
}
