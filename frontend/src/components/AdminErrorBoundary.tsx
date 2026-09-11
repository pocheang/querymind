import type React from "react";
import type { ReactNode, ErrorInfo } from "react";

import { Button } from "@/components/ui/button";
import { ErrorBoundary, ErrorFallbackCard } from "@/components/ErrorBoundary";

interface Props {
  children: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

/**
 * Error boundary specifically for the Admin page
 * Provides admin-specific error recovery
 */
export function AdminErrorBoundary({ children, onError }: Readonly<Props>) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error("AdminPage Error:", error, errorInfo);
        onError?.(error, errorInfo);
      }}
      fallbackRender={(error, reset) => (
        <ErrorFallbackCard
          icon="⚠️"
          title="Admin Console Error"
          description="Something went wrong loading the admin console."
          error={error}
        >
          <Button size="sm" onClick={reset}>
            Try Again
          </Button>
          <Button variant="secondary" size="sm" onClick={() => (window.location.href = "/app")}>
            Back to Chat
          </Button>
        </ErrorFallbackCard>
      )}
    >
      {children}
    </ErrorBoundary>
  );
}

export function withAdminErrorBoundary<P extends object>(
  Component: React.ComponentType<P>
): React.ComponentType<P> {
  return function AdminErrorBoundaryWrapper(props: P) {
    return (
      <AdminErrorBoundary>
        <Component {...props} />
      </AdminErrorBoundary>
    );
  };
}
