import { isValidElement } from "react";
import { useTranslation } from "react-i18next";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, Copy } from "lucide-react";

import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";

/** Recognise the language from remark's `language-xxx` class, for the header tag. */
function languageOf(className: string) {
  const match = /language-([\w+-]+)/.exec(className);
  return (match?.[1] || "code").toUpperCase();
}

/**
 * The macOS-window code block from the design: dark chrome, three dots, a
 * language tag and a copy button.
 *
 * Deliberately dark against the warm page. It is the one surface in the app
 * that inverts, and that is what makes a code sample read as a quoted
 * artefact rather than as prose.
 */
function CodeBlock({ code, className = "" }: Readonly<{ code: string; className?: string }>) {
  const { t } = useTranslation();
  const { copied, copy } = useCopyToClipboard(1200);

  return (
    <div className="my-3 overflow-hidden rounded-card border border-slate-700/60 bg-[#090d16] shadow-elev-2">
      <div className="flex h-[34px] items-center justify-between gap-2 border-b border-slate-600/40 bg-[#111827] px-3 select-none">
        <span className="flex items-center gap-1.5" aria-hidden="true">
          <span className="size-2.5 rounded-pill bg-[#ef4444]" />
          <span className="size-2.5 rounded-pill bg-[#f59e0b]" />
          <span className="size-2.5 rounded-pill bg-[#10b981]" />
        </span>
        <span className="rounded border border-sky-400/30 bg-sky-400/10 px-2 py-px font-mono text-[10px] font-bold uppercase tracking-wider text-sky-400">
          {languageOf(className)}
        </span>
        <button
          type="button"
          className="inline-flex h-6 items-center gap-1.5 rounded border border-white/15 bg-white/5 px-2 text-[11px] text-slate-300 transition-colors hover:border-white/25 hover:bg-white/15 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
          onClick={() => void copy(code)}
        >
          {copied ? <Check className="size-3" aria-hidden="true" /> : <Copy className="size-3" aria-hidden="true" />}
          {copied ? t("components.codeBlock.copied") : t("components.codeBlock.copy")}
        </button>
      </div>
      <pre className="m-0 overflow-x-auto bg-transparent p-3 font-mono text-[11px] leading-relaxed text-slate-200 select-text">
        <code className={className}>{code}</code>
      </pre>
    </div>
  );
}

/**
 * Rendered answer prose.
 *
 * Tables use the cool slate register on purpose -- the design pairs warm amber
 * chrome with cool-bordered data tables, and the contrast between the two is
 * part of the look, not an oversight.
 */
export function MarkdownBlock({ text }: Readonly<{ text: string }>) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        pre({ children }) {
          const child = Array.isArray(children) ? children[0] : children;
          if (!isValidElement(child)) return <pre>{children}</pre>;
          const className = String((child.props as { className?: string })?.className || "");
          const code = String((child.props as { children?: unknown })?.children || "").replace(/\n$/, "");
          return <CodeBlock className={className} code={code} />;
        },
        p: ({ children }) => <p className="mb-2.5 leading-relaxed text-ink last:mb-0">{children}</p>,
        h1: ({ children }) => <h1 className="mb-2 mt-3 text-base font-bold text-brand-text-strong">{children}</h1>,
        h2: ({ children }) => <h2 className="mb-2 mt-3 text-sm font-bold text-brand-text-strong">{children}</h2>,
        h3: ({ children }) => (
          <h3 className="mb-1.5 mt-3 border-l-[3px] border-brand-accent pl-2 text-sm font-bold text-brand-text-strong">
            {children}
          </h3>
        ),
        h4: ({ children }) => <h4 className="mb-1 mt-2.5 text-xs font-semibold text-brand-text">{children}</h4>,
        ul: ({ children }) => <ul className="mb-2.5 ml-5 list-disc space-y-1">{children}</ul>,
        ol: ({ children }) => <ol className="mb-2.5 ml-5 list-decimal space-y-1">{children}</ol>,
        li: ({ children }) => <li className="leading-relaxed text-ink">{children}</li>,
        a: ({ children, href }) => (
          <a href={href} target="_blank" rel="noreferrer" className="text-brand-text underline underline-offset-2">
            {children}
          </a>
        ),
        strong: ({ children }) => <strong className="font-semibold text-ink">{children}</strong>,
        blockquote: ({ children }) => (
          <blockquote className="my-2.5 rounded-r-card border-l-[3px] border-brand-accent bg-surface-muted px-3 py-2 text-ink-muted">
            {children}
          </blockquote>
        ),
        code: ({ className, children }) => (
          <code
            className={
              className ||
              "rounded border border-brand-border bg-brand-surface px-1 py-px font-mono text-[0.9em] text-brand-text"
            }
          >
            {children}
          </code>
        ),
        table: ({ children }) => (
          <div className="my-3 overflow-x-auto">
            <table className="w-full border-separate border-spacing-0 overflow-hidden rounded-card border border-slate-300 bg-white text-[11px] shadow-elev-1">
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th className="border-b-2 border-slate-400 border-r border-r-slate-300 bg-slate-100 px-3 py-2 text-left text-[10px] font-bold uppercase tracking-wider text-slate-700 last:border-r-0">
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className="border-b border-r border-slate-300 px-3 py-2 text-slate-800 last:border-r-0">{children}</td>
        ),
        tr: ({ children }) => <tr className="even:bg-slate-50 hover:bg-slate-100">{children}</tr>,
        hr: () => <hr className="my-3 border-line" />,
      }}
    >
      {text || ""}
    </ReactMarkdown>
  );
}
