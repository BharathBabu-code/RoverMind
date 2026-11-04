import React from 'react';
import { Camera, Layers, Route, Cpu, Sparkles, RefreshCw } from 'lucide-react';
import { ImageMetadata, FullAnalysisResponse } from '../types/api';

interface MissionStatusBarProps {
  currentImage: ImageMetadata | null;
  analysis: FullAnalysisResponse | null;
  isLoading: boolean;
  onLoadSample: () => void;
  onOpenUpload: () => void;
}

export const MissionStatusBar: React.FC<MissionStatusBarProps> = ({
  currentImage,
  analysis,
  isLoading,
  onLoadSample,
  onOpenUpload,
}) => {
  const isSynthetic = analysis?.segmentation?.is_synthetic ?? true;
  const steps = [
    { id: 1, name: 'Optical Ingestion (Real)', done: !!currentImage, icon: Camera },
    {
      id: 2,
      name: analysis ? (isSynthetic ? 'Synthetic Fixture' : 'SAM 3.1 Inference') : 'Segmentation',
      done: !!analysis,
      icon: Cpu,
      badge: analysis ? (isSynthetic ? 'OFFLINE' : 'LIVE') : undefined,
    },
    { id: 3, name: 'Terrain Normalization', done: !!analysis, icon: Layers },
    { id: 4, name: 'Risk Costmap (Calculated)', done: !!analysis?.costmap, icon: Layers },
    { id: 5, name: 'A* Solver (Real Alg)', done: !!analysis?.path_result?.is_success, icon: Route },
  ];

  return (
    <div className="hud-panel p-3.5 mb-5 border-mars-750/90 bg-gradient-to-r from-mars-950 via-mars-900 to-mars-950">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Left: Mission & Payload Telemetry */}
        <div className="flex items-center gap-4">
          <div className="w-11 h-11 rounded bg-mars-800/80 border border-mars-copper/40 flex items-center justify-center text-mars-rust shadow-hud">
            {isLoading ? (
              <RefreshCw className="w-5 h-5 animate-spin text-mars-glow" />
            ) : (
              <Camera className="w-5 h-5" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[11px] text-mars-copper uppercase tracking-widest font-semibold">
                TACTICAL MISSION SESSION
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-mars-800 text-slate-300 border border-mars-700">
                ACTIVE
              </span>
            </div>
            <h1 className="font-display font-bold text-base text-white tracking-wide flex items-center gap-2">
              {currentImage ? currentImage.filename : 'No Optical Payload Ingested'}
              {currentImage && (
                <span className="font-mono font-normal text-xs text-mars-sky">
                  [{currentImage.width} × {currentImage.height} px]
                </span>
              )}
            </h1>
          </div>
        </div>

        {/* Center: Pipeline Step Indicators */}
        <div className="hidden md:flex items-center gap-1.5 xl:gap-2">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            const isComplete = step.done;
            return (
              <React.Fragment key={step.id}>
                <div
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] font-mono transition-all ${
                    isComplete
                      ? 'bg-mars-emerald/15 text-emerald-400 border border-mars-emerald/40'
                      : 'bg-mars-850/60 text-slate-500 border border-mars-800'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{step.name}</span>
                  {step.badge && (
                    <span className="text-[9px] px-1 py-0.2 rounded bg-mars-800 text-mars-amber border border-mars-amber/30">
                      {step.badge}
                    </span>
                  )}
                </div>
                {idx < steps.length - 1 && (
                  <span className="text-mars-700 font-mono text-xs">→</span>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Right: Quick Action Controls */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onLoadSample}
            disabled={isLoading}
            className="btn-secondary text-[11px] flex items-center gap-1.5"
            title="Load authentic Mars rover camera frame from repository"
          >
            <Sparkles className="w-3.5 h-3.5 text-mars-amber" />
            Load Sample Frame
          </button>
          <button
            onClick={onOpenUpload}
            disabled={isLoading}
            className="btn-primary text-[11px] flex items-center gap-1.5"
          >
            <Camera className="w-3.5 h-3.5" />
            Upload Frame
          </button>
        </div>
      </div>
    </div>
  );
};
