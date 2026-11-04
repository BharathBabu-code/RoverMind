import React, { useState } from 'react';
import {
  Terminal,
  ChevronDown,
  ChevronUp,
  ShieldAlert,
  FileCode,
  Box,
} from 'lucide-react';
import { FullAnalysisResponse } from '../types/api';

interface DiagnosticsDrawerProps {
  analysis: FullAnalysisResponse | null;
}

export const DiagnosticsDrawer: React.FC<DiagnosticsDrawerProps> = ({ analysis }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!analysis) return null;

  const { segmentation, metadata, diagnostics, path_result } = analysis;

  return (
    <div className="hud-panel mb-8 border-mars-800">
      {/* Drawer Toggle Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full hud-panel-header flex items-center justify-between text-left hover:bg-mars-800/40 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <Terminal className="w-4 h-4 text-mars-sky" />
          <h3 className="font-display font-bold text-xs uppercase tracking-wider text-slate-200">
            Telemetry & Deep Technical Inspection
          </h3>
          <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-mars-800 text-slate-400">
            {segmentation.masks.length} Objects Detected
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
          <span>{isOpen ? 'Collapse Telemetry' : 'Expand Telemetry'}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {/* Collapsible Content */}
      {isOpen && (
        <div className="p-5 border-t border-mars-800 space-y-5 bg-mars-950/70">
          {/* Scientific Honesty Notice */}
          <div className="p-3.5 rounded bg-mars-rust/10 border-l-4 border-mars-rust border border-mars-rust/20 flex items-start gap-3">
            <ShieldAlert className="w-5 h-5 text-mars-rust flex-shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <h4 className="font-display font-semibold text-xs text-white uppercase tracking-wider">
                Operational Reality & Computational Scope
              </h4>
              <p className="text-[11px] font-mono text-slate-300 leading-relaxed">
                Visual concepts extracted from 2D monocular images are computational estimations. They do not
                measure true geotechnical soil mechanics, shear compaction, or 3D slope gradients.
                Calculated paths represent mathematical lowest-cost solutions under configured parameters, not certified autonomous drive commands.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Decoded Mask Instances Table */}
            <div className="space-y-2">
              <div className="font-mono text-xs text-slate-300 flex items-center gap-1.5 uppercase font-semibold">
                <Box className="w-3.5 h-3.5 text-mars-amber" />
                Decoded Mask Instances ({segmentation.masks.length})
              </div>
              <div className="max-h-52 overflow-y-auto space-y-1.5 pr-1">
                {segmentation.masks.map((mask, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded bg-mars-900 border border-mars-800 text-[11px] font-mono flex items-center justify-between"
                  >
                    <div>
                      <span className="text-white font-bold">{mask.object_id}</span>
                      <div className="text-[10px] text-slate-400">
                        {mask.bounds
                          ? `Box: [${mask.bounds.left}, ${mask.bounds.top}, ${mask.bounds.right}, ${mask.bounds.bottom}]`
                          : 'Full-frame'}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="text-mars-rust uppercase font-semibold">[{mask.concept}]</span>
                      <div className="text-[10px] text-slate-400">
                        {mask.area_pixels.toLocaleString()} pixels
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Pipeline Execution Traces */}
            <div className="space-y-2">
              <div className="font-mono text-xs text-slate-300 flex items-center gap-1.5 uppercase font-semibold">
                <FileCode className="w-3.5 h-3.5 text-mars-sky" />
                Pipeline Trace Logs
              </div>
              <div className="p-3 bg-mars-950 rounded border border-mars-800 font-mono text-[11px] text-slate-400 max-h-52 overflow-y-auto space-y-1.5">
                <div className="text-emerald-400">[200 OK] Ingested optical frame: {metadata.filename}</div>
                <div className="text-emerald-400">[200 OK] Resolution verified: {metadata.width}×{metadata.height} ({metadata.mime_type})</div>
                <div className="text-mars-sky">[INFO] Model: {segmentation.source_model}</div>
                <div className="text-mars-sky">[INFO] Grid discretization: {segmentation.grid_width} cols × {segmentation.grid_height} rows</div>
                {diagnostics.map((d, idx) => (
                  <div key={idx} className="text-amber-400">[DIAG] {d}</div>
                ))}
                {path_result && (
                  <div className="text-purple-400">
                    [A* PATH] Result: {path_result.is_success ? 'Success' : 'No Path'} (expanded {path_result.expanded_nodes} nodes, cost: {path_result.total_weighted_cost.toFixed(2)})
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
