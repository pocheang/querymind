import { Component, type ReactNode, type ErrorInfo } from "react";

import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, errorInfo);
    this.props.onError?.(error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        /* Amber like the rest of the app. This was the one surface the
           restyling never reached, and it is the only thing a reader sees
           when something breaks -- it was still painting `#007bff` on `#fee`
           from the palette this theme replaced, behind `var(--x, fallback)`
           pairs whose variables no longer exist, so the fallbacks were what
           rendered. */
        <div className="mx-auto my-8 max-w-xl rounded-panel border border-danger-border bg-danger-surface p-8 text-center">
          <h2 className="mb-4 text-sm font-bold text-danger">Something went wrong</h2>
          <p className="mb-4 text-xs text-ink-muted">
            {this.state.error?.message || "An unexpected error occurred"}
          </p>
          <Button size="sm" onClick={this.handleReset}>
            Try Again
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
