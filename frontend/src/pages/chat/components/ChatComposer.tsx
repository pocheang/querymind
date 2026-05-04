import type React from "react";
import { QuickActions } from "@/pages/chat/components/QuickActions";
import { SelectControl } from "@/pages/chat/components/SelectControl";
import { ToggleControl } from "@/pages/chat/components/ToggleControl";

type Props = {
  composerDropActive: boolean;
  question: string;
  questionRef: React.MutableRefObject<HTMLTextAreaElement | null>;
  chatUploadInputRef: React.MutableRefObject<HTMLInputElement | null>;
  isSending: boolean;
  quickPrompts: string[];
  runStatus: string;
  error: string;
  useWeb: boolean;
  useReasoning: boolean;
  agentClassHint: string;
  retrievalStrategy: string;
  onQuestionChange: (value: string) => void;
  onAsk: () => Promise<void>;
  onStop: () => void;
  onClearQuestion: () => void;
  onPromptPick: (prompt: string) => void;
  onUseWebChange: (next: boolean) => void;
  onUseReasoningChange: (next: boolean) => void;
  onAgentClassHintChange: (value: string) => void;
  onRetrievalStrategyChange: (value: string) => void;
  onComposerDragEnter: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragOver: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDragLeave: (evt: React.DragEvent<HTMLElement>) => void;
  onComposerDrop: (evt: React.DragEvent<HTMLElement>) => Promise<void>;
  onChatUploadChange: (evt: React.ChangeEvent<HTMLInputElement>) => Promise<void>;
};

const RETRIEVAL_OPTIONS = [
  { value: "advanced", label: "advanced" },
  { value: "baseline", label: "baseline" },
  { value: "safe", label: "safe" },
];

const AGENT_OPTIONS = [
  { value: "", label: "auto" },
  { value: "cybersecurity", label: "cybersecurity" },
  { value: "artificial_intelligence", label: "artificial_intelligence" },
  { value: "pdf_text", label: "pdf_text" },
  { value: "general", label: "general" },
];

function getModeHint(useWeb: boolean, useReasoning: boolean, retrievalStrategy: string) {
  const strategyLabel = retrievalStrategy === "baseline" ? "基础" : retrievalStrategy === "safe" ? "安全" : "高级";
  if (!useWeb && !useReasoning) {
    return `本地快速模式，${strategyLabel}检索：适合低延迟问答和已入库资料分析。`;
  }
  if (useWeb) {
    return `联网增强已开启，${strategyLabel}检索：适合需要最新资料的问题，响应可能稍慢。`;
  }
  return `推理增强已开启，${strategyLabel}检索：适合复杂分析、审计和多步骤归纳。`;
}

export function ChatComposer({
  composerDropActive,
  question,
  questionRef,
  chatUploadInputRef,
  isSending,
  quickPrompts,
  runStatus,
  error,
  useWeb,
  useReasoning,
  agentClassHint,
  retrievalStrategy,
  onQuestionChange,
  onAsk,
  onStop,
  onClearQuestion,
  onPromptPick,
  onUseWebChange,
  onUseReasoningChange,
  onAgentClassHintChange,
  onRetrievalStrategyChange,
  onComposerDragEnter,
  onComposerDragOver,
  onComposerDragLeave,
  onComposerDrop,
  onChatUploadChange,
}: Props) {
  const modeHint = getModeHint(useWeb, useReasoning, retrievalStrategy);

  return (
    <section
      className={`panel composer-panel ${composerDropActive ? "dragover" : ""}`}
      onDragEnter={onComposerDragEnter}
      onDragOver={onComposerDragOver}
      onDragLeave={onComposerDragLeave}
      onDrop={(event) => void onComposerDrop(event)}
    >
      <div className="composer-main">
        <div className="composer-heading-row">
          <label className="composer-label">输入问题，或拖拽 / 粘贴文档到这里</label>
          <span className="composer-drop-hint">支持 PDF / 图片 / 文本</span>
        </div>

        <div className="composer-input-wrapper">
          <textarea
            ref={questionRef}
            value={question}
            onChange={(event) => onQuestionChange(event.target.value)}
            placeholder="例如：总结最新上传 PDF 的安全风险，并给出证据来源..."
            rows={3}
            aria-label="输入问题"
            aria-describedby="composer-hint"
            onKeyDown={(event) => {
              if (event.key === "Escape" && isSending) {
                event.preventDefault();
                onStop();
                return;
              }
              if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                event.preventDefault();
                void onAsk();
              }
            }}
          />
          <div className="composer-input-actions">
            <label className="composer-upload-btn" title="上传 PDF 或图片">
              <span aria-hidden="true">+</span>
              <input
                ref={chatUploadInputRef}
                type="file"
                multiple
                accept=".pdf,.png,.jpg,.jpeg,.bmp,.tif,.tiff,.webp"
                style={{ display: "none" }}
                onChange={(event) => void onChatUploadChange(event)}
                aria-label="上传 PDF 或图片文件"
              />
            </label>
          </div>
        </div>
      </div>

      <div className="composer-controls">
        <div className="composer-options">
          <ToggleControl
            label="联网检索"
            active={useWeb}
            onChange={onUseWebChange}
            ariaLabel="联网检索开关"
            title="开启后将搜索互联网获取最新信息"
          />
          <ToggleControl
            label="推理增强"
            active={useReasoning}
            onChange={onUseReasoningChange}
            ariaLabel="推理增强开关"
            title="开启后使用深度推理模式"
          />
          <SelectControl
            label="检索策略"
            value={retrievalStrategy}
            options={RETRIEVAL_OPTIONS}
            onChange={onRetrievalStrategyChange}
            ariaLabel="选择检索策略"
          />
          <SelectControl
            label="Agent"
            value={agentClassHint}
            options={AGENT_OPTIONS}
            onChange={onAgentClassHintChange}
            ariaLabel="选择 Agent 类型"
          />
        </div>

        <button
          type="button"
          className="composer-primary-btn"
          onClick={() => void onAsk()}
          disabled={isSending}
          aria-label={isSending ? "正在处理问题" : "开始分析问题"}
        >
          {isSending && <span className="spinner" aria-hidden="true"></span>}
          <span className="btn-text">{isSending ? "分析中..." : "开始分析"}</span>
          {!isSending && <span className="btn-shortcut">Ctrl / Cmd + Enter</span>}
        </button>
      </div>

      <div className="composer-hint" id="composer-hint">
        {modeHint}
      </div>

      <QuickActions
        quickPrompts={quickPrompts}
        question={question}
        isSending={isSending}
        onPromptPick={onPromptPick}
        onStop={onStop}
        onClearQuestion={onClearQuestion}
      />

      {runStatus && <div className="status">{runStatus}</div>}
      {error && <div className="status error">{error}</div>}
    </section>
  );
}
