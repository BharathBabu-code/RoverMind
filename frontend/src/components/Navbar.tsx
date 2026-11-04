import React from 'react';
import { Compass, Server, Cpu, Info, Sparkles, Upload } from 'lucide-react';
import { HealthResponse, ConfigStatusResponse } from '../types/api';

interface NavbarProps {
  health: HealthResponse | null;
  config: ConfigStatusResponse | null;
  onOpenMethodology: () => void;
  onOpenUpload: () => void;
  onLoadSample: () => void;
  isLoading: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  config,
  onOpenMethodology,
  onOpenUpload,
  onLoadSample,
  isLoading,
}) => {
  const isBackendHealthy = health?.status === 'ok';

  return (
    <header className="border-b border-mars-800 bg-mars-950/95 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Treatment */}
        <div className="flex items-center gap-3.5">
          <div className="w-9 h-9 rounded bg-gradient-to-br from-mars-copper to-mars-rust flex items-center justify-center shadow-lg shadow-mars-rust/20 border border-orange-500/40">
            <Compass className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display font-bold text-lg tracking-wider text-white">
                ROVER<span className="text-mars-rust">MIND</span>
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-mars-800 text-slate-300 border border-mars-700">
                AEROSPACE MISSION CONTROL
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-mono hidden sm:block">
              Planetary Surface Hazard Perception & A* Decision Support
            </p>
          </div>
        </div>

        {/* Center / Right: System Telemetry Status & Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Quick Upload and Sample Buttons in Navbar */}
          <button
            onClick={onLoadSample}
            disabled={isLoading}
            className="hidden sm:flex btn-ghost text-xs items-center gap-1 border border-mars-750"
            title="Load authentic Mars rover camera frame"
          >
            <Sparkles className="w-3.5 h-3.5 text-mars-amber" />
            <span>Sample Frame</span>
          </button>

          <button
            onClick={onOpenUpload}
            disabled={isLoading}
            className="hidden sm:flex btn-ghost text-xs items-center gap-1 border border-mars-750"
          >
            <Upload className="w-3.5 h-3.5 text-mars-sky" />
            <span>Upload</span>
          </button>

          {/* Local Backend Server Indicator */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-mars-900 border border-mars-800 text-xs font-mono"
            title={isBackendHealthy ? 'Local Python FastAPI Backend Operational' : 'Backend Disconnected'}
          >
            <Server className="w-3.5 h-3.5 text-slate-400" />
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendHealthy ? 'bg-emerald-400' : 'bg-red-500'
              }`}
            />
            <span className="hidden lg:inline text-slate-300">
              SERVER: {isBackendHealthy ? 'LOCAL OK' : 'OFFLINE'}
            </span>
          </div>

          {/* SAM Model Status - Truthful Telemetry */}
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-mars-900 border border-mars-800 text-xs font-mono"
            title={
              !config?.external_api_enabled
                ? 'External API calls disabled via kill switch (EXTERNAL_API_ENABLED=false).'
                : config?.external_api_dry_run
                ? 'Dry-Run Mode active (EXTERNAL_API_DRY_RUN=true): Simulates SAM response without external calls.'
                : config?.sam_status === 'last_request_successful'
                ? `Meta SAM 3.1 Live Verified (${config.sam_last_verified || 'Active'})`
                : config?.sam_status === 'configured_untested'
                ? 'META_API_KEY Configured in .env (No external request verified yet)'
                : config?.sam_status === 'request_failed'
                ? 'Meta SAM 3.1 External Request Failed'
                : 'No META_API_KEY provided. Operating with labelled synthetic segmentation fixture.'
            }
          >
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span
              className={`w-2 h-2 rounded-full ${
                !config?.external_api_enabled
                  ? 'bg-slate-500'
                  : config?.external_api_dry_run
                  ? 'bg-blue-400 animate-pulse'
                  : config?.sam_status === 'last_request_successful'
                  ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                  : config?.sam_status === 'configured_untested'
                  ? 'bg-amber-400'
                  : config?.sam_status === 'request_failed'
                  ? 'bg-red-400'
                  : 'bg-slate-500'
              }`}
            />
            <span className="hidden lg:inline text-slate-300">
              {!config?.external_api_enabled
                ? 'SAM: OFFLINE SAFE'
                : config?.external_api_dry_run
                ? 'SAM: DRY RUN'
                : config?.sam_status === 'last_request_successful'
                ? 'SAM 3.1: LIVE VERIFIED'
                : config?.sam_status === 'configured_untested'
                ? 'SAM 3.1: UNTESTED'
                : config?.sam_status === 'request_failed'
                ? 'SAM: REQ FAILED'
                : 'SAM: SYNTHETIC FIXTURE'}
            </span>
          </div>

          {/* Reasoning Engine Status */}
          <div
            className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded bg-mars-900 border border-mars-800 text-xs font-mono"
            title={
              !config?.external_api_enabled
                ? 'External inference disabled via kill switch (EXTERNAL_API_ENABLED=false).'
                : config?.external_api_dry_run
                ? `Dry-Run Mode active: Simulating ${config.reasoning_provider === 'muse-spark' ? 'Muse Spark' : 'Llama'} reasoning without cost.`
                : config?.reasoning_status === 'last_request_successful'
                ? `Meta ${config.reasoning_provider === 'muse-spark' ? 'Muse Spark' : 'Llama'} Live Verified (${config.reasoning_last_verified || 'Active'})`
                : config?.reasoning_status === 'configured_untested'
                ? `API Key Configured for ${config.reasoning_provider || 'Reasoning'} (Untested)`
                : 'Reasoning layer operating in deterministic offline mode (no keys required).'
            }
          >
            <Sparkles className="w-3.5 h-3.5 text-slate-400" />
            <span
              className={`w-2 h-2 rounded-full ${
                !config?.external_api_enabled
                  ? 'bg-slate-500'
                  : config?.external_api_dry_run
                  ? 'bg-blue-400 animate-pulse'
                  : config?.reasoning_status === 'last_request_successful'
                  ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                  : config?.reasoning_status === 'request_in_progress'
                  ? 'bg-blue-400 animate-pulse'
                  : config?.is_reasoning_api_configured
                  ? 'bg-amber-400'
                  : 'bg-slate-500'
              }`}
            />
            <span className="text-slate-300 text-[11px]">
              {!config?.external_api_enabled
                ? 'AI: OFFLINE SAFE'
                : config?.external_api_dry_run
                ? 'AI: DRY RUN'
                : config?.reasoning_status === 'last_request_successful'
                ? (config?.reasoning_provider === 'muse-spark' ? 'MUSE SPARK: LIVE' : 'LLAMA 3.3: LIVE')
                : config?.reasoning_status === 'request_in_progress'
                ? 'AI: INFERRING...'
                : config?.is_reasoning_api_configured
                ? (config?.reasoning_provider === 'muse-spark' ? 'MUSE SPARK: READY' : 'LLAMA 3.3: READY')
                : 'AI: DETERMINISTIC'}
            </span>
          </div>

          {/* Action Links */}
          <button
            onClick={onOpenMethodology}
            className="flex items-center gap-1 px-2.5 py-1 rounded font-display text-xs text-mars-sky hover:bg-mars-sky/10 transition-colors border border-mars-sky/30"
          >
            <Info className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Methodology</span>
          </button>
        </div>
      </div>
    </header>
  );
};
