/**
 * TagInput Component
 *
 * Multi-select tag input with autocomplete support.
 * Displays tags as chips with remove functionality.
 */

import React, { useState, useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { sessionManagementApi } from "../../services/sessionManagement";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  maxTags?: number;
  disabled?: boolean;
}

export const TagInput: React.FC<TagInputProps> = ({ value, onChange, placeholder, maxTags = 10, disabled = false }) => {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [allTags, setAllTags] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load all available tags on mount
  useEffect(() => {
    loadAllTags();
  }, []);

  // Click outside handler
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const loadAllTags = async () => {
    try {
      const tags = await sessionManagementApi.getAllTags();
      setAllTags(tags);
    } catch (error) {
      console.error("Failed to load tags:", error);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newInput = e.target.value;
    setInput(newInput);

    if (newInput.trim()) {
      // Filter suggestions: exclude already selected tags, match input
      const filtered = allTags
        .filter((tag) => !value.includes(tag))
        .filter((tag) => tag.toLowerCase().includes(newInput.toLowerCase()))
        .slice(0, 5);

      setSuggestions(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && input.trim()) {
      e.preventDefault();
      addTag(input.trim());
    } else if (e.key === "Backspace" && !input && value.length > 0) {
      // Remove last tag on backspace when input is empty
      removeTag(value[value.length - 1]);
    }
  };

  const addTag = (tag: string) => {
    if (value.length >= maxTags) {
      return;
    }

    const normalizedTag = tag.toLowerCase().trim();
    if (normalizedTag && !value.includes(normalizedTag)) {
      onChange([...value, normalizedTag]);
      setInput("");
      setShowSuggestions(false);

      // Add to allTags if new
      if (!allTags.includes(normalizedTag)) {
        setAllTags([...allTags, normalizedTag]);
      }
    }
  };

  const removeTag = (tag: string) => {
    onChange(value.filter((t) => t !== tag));
  };

  const handleSuggestionClick = (tag: string) => {
    addTag(tag);
    inputRef.current?.focus();
  };

  return (
    <div className="relative" ref={containerRef}>
      <div
        className={cn(
          "flex flex-wrap items-center gap-1.5 rounded-control border border-brand-border bg-surface p-1.5 transition-all",
          "field-shell focus-within:border-brand-accent focus-within:ring-2 focus-within:ring-[var(--brand-ring)]",
          disabled && "cursor-not-allowed opacity-60"
        )}
      >
        {value.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1.5 rounded-pill border border-brand-border bg-brand-surface px-2.5 py-0.5 text-xs font-semibold text-brand-text"
          >
            {tag}
            {!disabled && (
              <button
                type="button"
                className="rounded-pill text-brand-accent transition-colors hover:text-danger focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--brand-ring)]"
                onClick={() => removeTag(tag)}
                aria-label={t("sessionManagement.removeTag")}
              >
                <X className="size-3.5" aria-hidden="true" />
              </button>
            )}
          </span>
        ))}

        {!disabled && value.length < maxTags && (
          <input
            ref={inputRef}
            type="text"
            className="min-w-24 flex-1 bg-transparent px-1 text-xs sm:text-sm text-ink placeholder:text-ink-faint focus-visible:outline-none"
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleInputKeyDown}
            onFocus={() => input.trim() && setShowSuggestions(suggestions.length > 0)}
            placeholder={value.length === 0 ? placeholder : ""}
            disabled={disabled}
          />
        )}
      </div>

      {value.length > 0 && (
        <p className="mt-1 font-mono text-xs font-medium text-ink/80">
          {value.length} / {maxTags} {t("sessionManagement.tags")}
        </p>
      )}

      {showSuggestions && suggestions.length > 0 && (
        <div className="glass-panel absolute inset-x-0 top-full z-30 mt-1 overflow-hidden rounded-card p-1 shadow-elev-3">
          {suggestions.map((tag) => (
            <button
              key={tag}
              type="button"
              className="block w-full rounded-control px-2.5 py-1.5 text-left text-xs sm:text-sm font-medium text-ink transition-colors hover:bg-brand-surface hover:text-brand-text focus-visible:outline-none focus-visible:bg-brand-surface"
              onClick={() => handleSuggestionClick(tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
