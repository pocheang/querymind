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
 * Error boundary specifically for the Admin page
 * Provides admin-specific error recovery
 */
export class AdminErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("AdminPage Error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  handleReturnHome = () => {
    window.location.href = "/app";
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="aurora-bg flex min-h-screen flex-col items-center justify-center p-8">
          <div className="glass-card w-full max-w-lg rounded-panel p-8 text-center">
            <div className="mb-4 text-5xl" aria-hidden="true">
              ⚠️
            </div>
            <h2 className="mb-4 text-base sm:text-lg font-bold text-ink">Admin Console Error</h2>
            <p className="mb-6 text-sm text-ink/80 leading-relaxed">
              Something went wrong loading the admin console.
            </p>
            {this.state.error && (
              <details className="mb-6 text-left">
                <summary className="mb-2 cursor-pointer text-xs font-semibold text-ink/80">Error details</summary>
                <pre className="overflow-auto rounded-control bg-surface-muted p-2.5 font-mono text-xs text-ink">
                  {this.state.error.message}
                </pre>
              </details>
            )}
            <div className="flex justify-center gap-3">
              <Button size="sm" onClick={this.handleReset}>
                Try Again
              </Button>
              <Button variant="secondary" size="sm" onClick={this.handleReturnHome}>
                Back to Chat
              </Button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
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
