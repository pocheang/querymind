import { useState } from 'react';
import '../styles/components/code-block.css';

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
}

export function CodeBlock({ code, language, filename }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div className="code-block-wrapper">
      <div className="code-block-header">
        {filename && <span className="code-block-filename">{filename}</span>}
        {language && !filename && (
          <span className="code-block-language">{language}</span>
        )}
        <button
          type="button"
          className="code-block-copy"
          onClick={handleCopy}
          aria-label={copied ? '已复制' : '复制代码'}
          title={copied ? '已复制到剪贴板' : '复制到剪贴板'}
        >
          {copied ? (
            <>
              <span className="copy-icon">✓</span>
              <span className="copy-text">已复制</span>
            </>
          ) : (
            <>
              <span className="copy-icon">⎘</span>
              <span className="copy-text">复制</span>
            </>
          )}
        </button>
      </div>
      <pre className="code-block-content">
        <code className={language ? `language-${language}` : undefined}>
          {code}
        </code>
      </pre>
    </div>
  );
}
