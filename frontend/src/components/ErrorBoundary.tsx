import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Unhandled RoverMind UI Error Boundary caught an error:', error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-mars-950 text-slate-100 flex items-center justify-center p-6">
          <div className="hud-panel p-8 max-w-lg w-full text-center space-y-4 border-mars-750">
            <div className="w-12 h-12 rounded-full bg-red-950/80 border border-red-500/40 flex items-center justify-center mx-auto text-red-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="font-display font-bold text-lg text-white uppercase tracking-wider">
              Telemetry Render Interruption
            </h2>
            <p className="font-mono text-xs text-slate-400 leading-relaxed">
              A mission control telemetry component encountered an unexpected schema or render state.
            </p>
            {this.state.error && (
              <div className="p-3 rounded bg-mars-900 border border-mars-800 text-left font-mono text-[11px] text-red-300 overflow-x-auto max-h-32">
                {this.state.error.message}
              </div>
            )}
            <button
              onClick={this.handleReset}
              className="btn-primary text-xs px-5 py-2.5 mx-auto flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reset Mission Control View
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
