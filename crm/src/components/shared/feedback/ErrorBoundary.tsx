import { Component, type ErrorInfo, type ReactNode } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  resetKey?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = {
    hasError: false,
    message: '',
  };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      message: error.message || 'This CRM view failed to render.',
    };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[AI Hub CRM] View render failed', error, info);
  }

  componentDidUpdate(previousProps: ErrorBoundaryProps) {
    if (previousProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, message: '' });
    }
  }

  private reset = () => {
    this.setState({ hasError: false, message: '' });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <section className="card error-boundary">
        <div>
          <div className="text-xs font-semibold uppercase text-muted">View error</div>
          <h2>Could not render this workspace view</h2>
          <p>{this.state.message}</p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={this.reset}>
          Try again
        </button>
      </section>
    );
  }
}
