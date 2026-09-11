import type React from "react";
import type { ReactNode, ErrorInfo } from "react";

import { Button } from "@/components/ui/button";
import { ErrorBoundary, ErrorFallbackCard } from "@/components/ErrorBoundary";

interface Props {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/**
 * Error boundary specifically for the Chat page
 * Provides chat-specific error recovery
 */
export function ChatErrorBoundary({ children, onError }: Readonly<Props>) {
  const handleReset = (reset: () => void) => {
    // Clear local storage cache that might be corrupted
    try {
      const keysToPreserve = new Set(["auth_token", "theme"]);
      const allKeys = Object.keys(localStorage);
      allKeys.forEach((key) => {
        if (!keysToPreserve.has(key) && key.startsWith("chat_")) {
          localStorage.removeItem(key);
        }
      });
    } catch (e) {
      console.warn("Failed to clear cache:", e);
    }

    reset();
    window.location.href = "/app";
  };

  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error("ChatPage Error:", error, errorInfo);
        onError?.(error, errorInfo);
      }}
      fallbackRender={(error, reset) => (
        <ErrorFallbackCard
          icon="💬"
          title="Chat Error"
          description="The chat encountered an error. Your conversation data is safe."
          error={error}
        >
          <Button size="sm" onClick={() => handleReset(reset)}>
            Return to Chat
          </Button>
        </ErrorFallbackCard>
      )}
    >
      {children}
    </ErrorBoundary>
  );
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
