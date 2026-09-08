import { Component, type ReactNode, type ErrorInfo } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary specifically for the Chat page
 * Provides chat-specific error recovery
 */
export class ChatErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ChatPage Error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    // Clear local storage cache that might be corrupted
    try {
      const keysToPreserve = ["auth_token", "theme"];
      const allKeys = Object.keys(localStorage);
      allKeys.forEach((key) => {
        if (!keysToPreserve.includes(key) && key.startsWith("chat_")) {
          localStorage.removeItem(key);
        }
      });
    } catch (e) {
      console.warn("Failed to clear cache:", e);
    }

    this.setState({ hasError: false, error: null });
    window.location.href = "/app";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="aurora-bg flex min-h-screen flex-col items-center justify-center p-8">
          <div className="glass-card w-full max-w-lg rounded-panel p-8 text-center">
            <div className="mb-4 text-5xl" aria-hidden="true">
              💬
            </div>
            <h2 className="mb-4 text-sm font-bold text-ink">Chat Error</h2>
            <p className="mb-6 text-xs text-ink-muted">
              The chat encountered an error. Your conversation data is safe.
            </p>
            {this.state.error && (
              <details className="mb-6 text-left">
                <summary className="mb-2 cursor-pointer text-[11px] text-ink-muted">Error details</summary>
                <pre className="overflow-auto rounded-control bg-surface-muted p-2 font-mono text-[11px] text-ink">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <Button size="sm" onClick={this.handleReset}>
              Return to Chat
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// HOC for functional components
export function withChatErrorBoundary<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function ChatErrorBoundaryWrapper(props: P) {
    return (
      <ChatErrorBoundary>
        <Component {...props} />
      </ChatErrorBoundary>
    );
  };
}
