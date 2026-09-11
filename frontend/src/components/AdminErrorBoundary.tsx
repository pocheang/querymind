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
function AdminFallback({ error, onReset }: Readonly<{ error: Error | null; onReset: () => void }>) {
  return (
    <ErrorFallbackCard
      icon="⚠️"
      title="Admin Console Error"
      description="Something went wrong loading the admin console."
      error={error}
    >
      <Button size="sm" onClick={onReset}>
        Try Again
      </Button>
      <Button variant="secondary" size="sm" onClick={() => (window.location.href = "/app")}>
        Back to Chat
      </Button>
    </ErrorFallbackCard>
  );
}

function renderAdminFallback(error: Error | null, reset: () => void) {
  return <AdminFallback error={error} onReset={reset} />;
}

export function AdminErrorBoundary({ children, onError }: Readonly<Props>) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        console.error("AdminPage Error:", error, errorInfo);
        onError?.(error, errorInfo);
      }}
      fallbackRender={renderAdminFallback}
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
