import React from 'react';
import { Route, Play, CheckCircle2, XCircle, Navigation, Activity, ArrowRight } from 'lucide-react';
import { PathPlanResponse } from '../types/api';

interface PathPlanningPanelProps {
  pathResult: PathPlanResponse | null | undefined;
  startCoord: [number, number] | null;
  goalCoord: [number, number] | null;
  allowDiagonal: boolean;
  setAllowDiagonal: (allow: boolean) => void;
  onRecalculatePath: () => void;
  isPlanning: boolean;
}

export const PathPlanningPanel: React.FC<PathPlanningPanelProps> = ({
  pathResult,
  startCoord,
  goalCoord,
  allowDiagonal,
  setAllowDiagonal,
  onRecalculatePath,
  isPlanning,
}) => {
  const isSuccess = pathResult?.is_success ?? false;

  return (
    <div className="hud-card p-5 mb-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-[#242e42] gap-3">
        <div>
          <h3 className="font-display font-semibold text-base text-white flex items-center gap-2">
            <Route className="w-5 h-5 text-[#e25822]" />
            Custom A* Path Planning Engine
          </h3>
          <p className="text-xs text-[#94a3b8] font-mono">
            Optimized route computation based on backend weighted terrain costmap
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs font-mono text-slate-300 cursor-pointer bg-[#141a26] px-2.5 py-1.5 rounded border border-[#242e42]">
            <input
              type="checkbox"
              checked={allowDiagonal}
              onChange={(e) => setAllowDiagonal(e.target.checked)}
              className="accent-[#e25822] cursor-pointer"
            />
            Allow 8-Way Diagonal
          </label>

          <button
            onClick={onRecalculatePath}
            disabled={isPlanning || !startCoord || !goalCoord}
            className="btn-primary text-xs"
          >
            <Play className={`w-3.5 h-3.5 ${isPlanning ? 'animate-spin' : ''}`} />
            {isPlanning ? 'Calculating Path...' : 'Execute A* Routing'}
          </button>
        </div>
      </div>

      {/* Metrics HUD Row */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Route Status */}
        <div className="bg-[#141a26] border border-[#242e42] rounded-lg p-3">
          <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-1 flex items-center gap-1.5">
            <Navigation className="w-3.5 h-3.5 text-[#38bdf8]" />
            Route Solution
          </div>
          <div className="flex items-center gap-2 mt-1">
            {pathResult ? (
              isSuccess ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-[#10b981]" />
                  <span className="font-display font-bold text-sm text-[#34d399]">
                    Optimal Path Found
                  </span>
                </>
              ) : (
                <>
                  <XCircle className="w-4 h-4 text-[#ef4444]" />
                  <span className="font-display font-bold text-sm text-[#f87171]">
                    Destination Blocked
                  </span>
                </>
              )
            ) : (
              <span className="text-xs text-[#64748b] font-mono">Ready to compute</span>
            )}
          </div>
        </div>

        {/* Total Traversal Cost */}
        <div className="bg-[#141a26] border border-[#242e42] rounded-lg p-3">
          <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-1">
            Cumulative Cost
          </div>
          <div className="font-mono font-bold text-lg text-white">
            {pathResult && isSuccess ? (
              <span className="text-[#f59e0b]">{pathResult.total_weighted_cost.toFixed(2)}</span>
            ) : (
              <span className="text-[#64748b]">--</span>
            )}
          </div>
        </div>

        {/* Geometric Distance */}
        <div className="bg-[#141a26] border border-[#242e42] rounded-lg p-3">
          <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-1">
            Geometric Distance
          </div>
          <div className="font-mono font-bold text-lg text-white">
            {pathResult && isSuccess ? (
              <span className="text-[#38bdf8]">
                {pathResult.geometric_length.toFixed(2)} <span className="text-xs text-[#64748b]">grid units</span>
              </span>
            ) : (
              <span className="text-[#64748b]">--</span>
            )}
          </div>
        </div>

        {/* Expanded Nodes */}
        <div className="bg-[#141a26] border border-[#242e42] rounded-lg p-3">
          <div className="text-[11px] font-mono text-[#64748b] uppercase tracking-wider mb-1 flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-[#a855f7]" />
            Expanded Nodes
          </div>
          <div className="font-mono font-bold text-lg text-white">
            {pathResult ? (
              <span className="text-slate-200">{pathResult.expanded_nodes}</span>
            ) : (
              <span className="text-[#64748b]">--</span>
            )}
          </div>
        </div>
      </div>

      {/* Selected Coordinates Readout */}
      <div className="mt-4 p-3 bg-[#111622] rounded-md border border-[#1f2838] flex flex-wrap items-center justify-between text-xs font-mono text-[#94a3b8] gap-3">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#10b981]" />
            Start: {startCoord ? `[Row ${startCoord[0]}, Col ${startCoord[1]}]` : 'Not Selected'}
          </span>
          <ArrowRight className="w-3.5 h-3.5 text-[#64748b]" />
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-[#f59e0b]" />
            Destination: {goalCoord ? `[Row ${goalCoord[0]}, Col ${goalCoord[1]}]` : 'Not Selected'}
          </span>
        </div>

        {pathResult?.path && pathResult.path.length > 0 && (
          <span className="text-[#38bdf8]">
            {pathResult.path.length} Waypoints in Route Sequence
          </span>
        )}
      </div>
    </div>
  );
};
