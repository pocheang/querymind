/**
 * SessionMetadataEditor Component
 *
 * Allows users to edit session metadata including tags, category, and description.
 * Supports automatic tag extraction from messages.
 */

import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import {
  sessionManagementApi,
  SessionMetadata,
  SessionCategory,
  UpdateMetadataRequest,
} from "../../services/sessionManagement";
import { ApiError } from "@/services/http/client";
import { TagInput } from "./TagInput";
import { Loader2, Tag } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface SessionMetadataEditorProps {
  sessionId: string;
  messages?: Array<{ role: string; content: string }>;
  onSave?: (metadata: SessionMetadata) => void;
  onCancel?: () => void;
}

export const SessionMetadataEditor: React.FC<SessionMetadataEditorProps> = ({
  sessionId,
  messages = [],
  onSave,
  onCancel,
}) => {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [extracting, setExtracting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [tags, setTags] = useState<string[]>([]);
  const [category, setCategory] = useState<SessionCategory | null>(null);
  const [description, setDescription] = useState("");
  const [autoTags, setAutoTags] = useState<string[]>([]);

  // Category options
  const categories: SessionCategory[] = ["research", "development", "debugging", "learning", "other"];

  // Load existing metadata on mount
  useEffect(() => {
    loadMetadata();
  }, [sessionId]);

  const loadMetadata = async () => {
    setLoading(true);
    setError(null);

    try {
      const metadata = await sessionManagementApi.getMetadata(sessionId);
      setTags(metadata.tags);
      setCategory(metadata.category);
      setDescription(metadata.description || "");
      setAutoTags(metadata.auto_tags);
    } catch (err: unknown) {
      // Metadata may not exist yet, which is fine
      if (!(err instanceof ApiError && err.status === 404)) {
        console.error("Failed to load metadata:", err);
        setError(t("sessionManagement.errorLoadingMetadata"));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleExtractTags = async () => {
    if (messages.length === 0) {
      setError(t("sessionManagement.noMessagesToExtract"));
      return;
    }

    setExtracting(true);
    setError(null);

    try {
      const metadata = await sessionManagementApi.extractAutoTags(sessionId, messages);
      setAutoTags(metadata.auto_tags);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to extract tags:", err);
      setError(t("sessionManagement.errorExtractingTags"));
    } finally {
      setExtracting(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const request: UpdateMetadataRequest = {
        tags,
        category,
        description: description.trim() || null,
      };

      const metadata = await sessionManagementApi.updateMetadata(sessionId, request);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);

      if (onSave) {
        onSave(metadata);
      }
    } catch (err) {
      console.error("Failed to save metadata:", err);
      setError(t("sessionManagement.errorSavingMetadata"));
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    } else {
      // Reset to original values
      loadMetadata();
    }
  };

  if (loading) {
    return <p className="py-10 text-center text-xs text-ink-muted">{t("sessionManagement.loadingMetadata")}...</p>;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-bold text-ink">{t("sessionManagement.editMetadata")}</h3>

      {error && (
        <p
          role="alert"
          className="rounded-control border border-danger-border bg-danger-surface px-2.5 py-1.5 text-xs font-medium text-danger"
        >
          {error}
        </p>
      )}
      {success && (
        <output className="block rounded-control border border-success-border bg-success-surface px-2.5 py-1.5 text-xs font-medium text-success">
          {t("sessionManagement.savedSuccessfully")}
        </output>
      )}

      <form
        className="space-y-3"
        onSubmit={(e) => {
          e.preventDefault();
          handleSave();
        }}
      >
        <div className="space-y-1.5">
          <Label>{t("sessionManagement.tags")}</Label>
          <TagInput
            value={tags}
            onChange={setTags}
            placeholder={t("sessionManagement.tagsPlaceholder")}
            maxTags={10}
            disabled={saving}
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="category">{t("sessionManagement.category")}</Label>
          <select
            id="category"
            value={category || ""}
            onChange={(e) => setCategory((e.target.value || null) as SessionCategory | null)}
            disabled={saving}
            className="h-8 w-full rounded-control border border-brand-border bg-surface px-2 text-xs sm:text-sm text-ink transition-colors focus-visible:border-brand-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)] disabled:opacity-60"
          >
            <option value="">{t("sessionManagement.selectCategory")}</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {t(`sessionManagement.categories.${cat}`)}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="description">{t("sessionManagement.description")}</Label>
          <Textarea
            id="description"
            rows={4}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("sessionManagement.descriptionPlaceholder")}
            maxLength={500}
            disabled={saving}
          />
          <p className="text-right font-mono text-xs font-medium text-ink/80">{description.length} / 500</p>
        </div>

        <div className="space-y-2 rounded-card border border-line bg-surface-inset p-2.5">
          <p className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-ink/80">
            <Tag className="size-3.5 text-brand-accent" aria-hidden="true" />
            {t("sessionManagement.autoTags")}
          </p>

          {autoTags.length > 0 ? (
            <div className="flex flex-wrap gap-1">
              {autoTags.map((tag) => (
                <Badge key={tag} variant="neutral" size="pill">
                  {tag}
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-xs font-medium text-ink/80">{t("sessionManagement.noAutoTags")}</p>
          )}

          <Button
            variant="secondary"
            size="xs"
            onClick={handleExtractTags}
            disabled={extracting || messages.length === 0}
          >
            {extracting && <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />}
            {t("sessionManagement.extractTags")}
          </Button>
        </div>

        <div className="flex items-center justify-end gap-2">
          <Button variant="secondary" size="sm" onClick={handleCancel} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" size="sm" disabled={saving}>
            {saving && <Loader2 className="size-3 animate-spin" aria-hidden="true" />}
            {t("common.save")}
          </Button>
        </div>
      </form>
    </div>
  );
};
