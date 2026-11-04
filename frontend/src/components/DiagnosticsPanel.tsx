import React from 'react';
import { ShieldAlert, Cpu, Terminal } from 'lucide-react';
import { FullAnalysisResponse } from '../types/api';

interface DiagnosticsPanelProps {
  analysis: FullAnalysisResponse | null;
}

export const DiagnosticsPanel: React.FC<DiagnosticsPanelProps> = ({ analysis }) => {
  if (!analysis) {
    return (
      <div className="hud-card p-6 text-center text-xs font-mono text-[#64748b]">
        No active telemetry session. Ingest a rover optical frame and run analysis.
      </div>
    );
  }

  const { segmentation, path_result, diagnostics, metadata } = analysis;

  return (
    <div className="space-y-6">
      {/* Scientific Honesty Notice Banner */}
      <div className="bg-[#191e2b] border-l-4 border-[#e25822] p-4 rounded-r-lg border border-[#242e42] shadow-lg">
        <div className="flex items-start gap-3">
          <ShieldAlert className="w-5 h-5 text-[#e25822] flex-shrink-0 mt-0.5" />
          <div className="space-y-1">
            <h4 className="font-display font-semibold text-sm text-white">
              Scientific & Operational Reality Notice
            </h4>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              Monocular 2D RGB imagery cannot verify mechanical bearing capacity, subsurface soil shear
              strength, slope stability, or certified traversability. Terrain labels represent 
              <strong className="text-slate-200"> image-derived visual estimations</strong>, and the route represents a 
              <strong className="text-slate-200"> computed lowest-cost decision-support path</strong> under configured traversal parameters.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Model & Mask Diagnostics */}
        <div className="hud-card p-5">
          <h3 className="font-display font-semibold text-base text-white flex items-center gap-2 pb-3 border-b border-[#242e42]">
            <Cpu className="w-4 h-4 text-[#38bdf8]" />
            Segmentation Model Diagnostics
          </h3>

          <div className="mt-4 space-y-3 text-xs font-mono">
            <div className="flex justify-between py-1 border-b border-[#1f2838]">
              <span className="text-[#64748b]">Model Provider:</span>
              <span className="text-slate-200">{segmentation.source_model}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#1f2838]">
              <span className="text-[#64748b]">Execution Mode:</span>
              <span className={segmentation.is_synthetic ? 'text-[#f59e0b]' : 'text-[#10b981]'}>
                {segmentation.is_synthetic ? 'Labelled Synthetic Fixture' : 'Live SAM 3.1 API'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#1f2838]">
              <span className="text-[#64748b]">Detected Masks:</span>
              <span className="text-[#38bdf8] font-bold">{segmentation.masks.length}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#1f2838]">
              <span className="text-[#64748b]">Grid Resolution:</span>
              <span className="text-slate-200">
                {segmentation.grid_width} cols × {segmentation.grid_height} rows
              </span>
            </div>
          </div>

          {/* Mask Table */}
          <div className="mt-4">
            <div className="text-[11px] font-mono uppercase text-[#64748b] mb-2">Decoded Mask Instances</div>
            <div className="max-h-48 overflow-y-auto space-y-1.5 pr-1">
              {segmentation.masks.map((mask, i) => (
                <div
                  key={i}
                  className="p-2 rounded bg-[#141a26] border border-[#1f2838] text-[11px] font-mono flex items-center justify-between"
                >
                  <span className="text-slate-300 font-semibold">{mask.object_id}</span>
                  <span className="text-[#ff8533] uppercase">[{mask.concept}]</span>
                  <span className="text-[#64748b]">{mask.area_pixels.toLocaleString()} px</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* System Logs & Diagnostic Traces */}
        <div className="hud-card p-5">
          <h3 className="font-display font-semibold text-base text-white flex items-center gap-2 pb-3 border-b border-[#242e42]">
            <Terminal className="w-4 h-4 text-[#10b981]" />
            Pipeline Execution Log
          </h3>

          <div className="mt-4 bg-[#0a0d13] p-3 rounded-md border border-[#1f2838] font-mono text-xs text-[#94a3b8] max-h-72 overflow-y-auto space-y-2">
            <div className="text-[#10b981]">[OK] Raw image loaded: {metadata.filename} ({metadata.width}x{metadata.height})</div>
            <div className="text-[#38bdf8]">[INFO] Spatial downsample factor computed: {segmentation.grid_width}x{segmentation.grid_height} grid cells</div>
            {diagnostics.map((diag, idx) => (
              <div key={idx} className="text-[#f59e0b]">
                [DIAG] {diag}
              </div>
            ))}
            <div className="text-[#10b981]">[OK] Normalized terrain grid generated via SegmentationResult contract</div>
            <div className="text-[#10b981]">[OK] Terrain costmap compiled across canonical classes</div>
            {path_result && (
              <div className="text-[#a855f7]">
                [A*] Path search completed: {path_result.is_success ? 'Success' : 'No Path'} (expanded {path_result.expanded_nodes} nodes)
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
