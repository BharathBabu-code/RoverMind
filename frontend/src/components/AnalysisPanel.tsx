import React from 'react';
import {
  Route,
  Play,
  CheckCircle2,
  AlertTriangle,
  Navigation,
  Activity,
  PieChart,
  Info,
} from 'lucide-react';
import { FullAnalysisResponse } from '../types/api';

interface AnalysisPanelProps {
  analysis: FullAnalysisResponse;
  startCoord: [number, number] | null;
  goalCoord: [number, number] | null;
  allowDiagonal: boolean;
  setAllowDiagonal: (allow: boolean) => void;
  onRecalculatePath: () => void;
  onResetPoints: () => void;
  isPlanning: boolean;
}

export const AnalysisPanel: React.FC<AnalysisPanelProps> = ({
  analysis,
  startCoord,
  goalCoord,
  allowDiagonal,
  setAllowDiagonal,
  onRecalculatePath,
  isPlanning,
}) => {
  const { segmentation, costmap, path_result } = analysis;
  const isSuccess = path_result?.is_success ?? false;

  // Calculate terrain distribution strictly from actual response grid
  const counts: Record<string, number> = {
    clear: 0,
    rocky: 0,
    loose: 0,
    obstacle: 0,
    unknown: 0,
  };

  let totalCells = 0;
  let traversableCells = 0;
  let blockedCells = 0;

  segmentation.terrain_grid.forEach((row, r) => {
    row.forEach((cell, c) => {
      totalCells++;
      const normCell = cell.toLowerCase();
      if (normCell.includes('rock')) counts.rocky++;
      else if (normCell.includes('loose') || normCell.includes('sand')) counts.loose++;
      else if (normCell.includes('obstacle') || normCell.includes('crater')) counts.obstacle++;
      else if (normCell.includes('clear') || normCell.includes('bedrock') || normCell.includes('soil')) counts.clear++;
      else counts.unknown++;

      if (costmap.cost_grid[r][c] === null) {
        blockedCells++;
      } else {
        traversableCells++;
      }
    });
  });

  const getPercentage = (count: number) =>
    totalCells > 0 ? ((count / totalCells) * 100).toFixed(1) : '0.0';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
      {/* Left Column (8 cols): A* Path Planning & Telemetry HUD */}
      <div className="lg:col-span-8 hud-panel p-5 flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-3.5 border-b border-mars-800 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Route className="w-4 h-4 text-mars-rust" />
                <h3 className="font-display font-bold text-sm tracking-wide text-white uppercase">
                  Custom A* Pathfinding Engine
                </h3>
              </div>
              <p className="font-mono text-xs text-slate-400 mt-0.5">
                Authoritative backend heuristic graph search (Manhattan / Octile metric)
              </p>
            </div>

            {/* Movement Mode & Actions */}
            <div className="flex items-center gap-2.5">
              <label className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-mars-850 border border-mars-750 text-xs font-mono text-slate-300 cursor-pointer hover:border-mars-rust/50 transition-colors">
                <input
                  type="checkbox"
                  checked={allowDiagonal}
                  onChange={(e) => setAllowDiagonal(e.target.checked)}
                  className="accent-mars-rust cursor-pointer"
                />
                8-Way Diagonal
              </label>

              <button
                onClick={onRecalculatePath}
                disabled={isPlanning || !startCoord || !goalCoord}
                className="btn-primary flex items-center gap-1.5 text-xs"
              >
                <Play className={`w-3.5 h-3.5 ${isPlanning ? 'animate-spin' : ''}`} />
                {isPlanning ? 'Calculating...' : 'Recalculate Route'}
              </button>
            </div>
          </div>

          {/* Core Route Metrics Tiles */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            {/* Status Metric */}
            <div className="bg-mars-950/80 border border-mars-800 rounded p-3">
              <div className="font-mono text-[10px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Navigation className="w-3 h-3 text-mars-sky" />
                Solution Status
              </div>
              <div className="mt-1 flex items-center gap-1.5">
                {path_result ? (
                  isSuccess ? (
                    <>
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      <span className="font-display font-bold text-xs text-emerald-400 tracking-wide">
                        OPTIMAL PATH
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <span className="font-display font-bold text-xs text-red-400 tracking-wide">
                        UNREACHABLE
                      </span>
                    </>
                  )
                ) : (
                  <span className="font-mono text-xs text-slate-500">Ready</span>
                )}
              </div>
            </div>

            {/* Cumulative Weighted Cost */}
            <div className="bg-mars-950/80 border border-mars-800 rounded p-3">
              <div className="font-mono text-[10px] text-slate-400 uppercase tracking-wider mb-1">
                Weighted Cost
              </div>
              <div className="font-mono font-bold text-lg text-mars-amber">
                {path_result && isSuccess ? path_result.total_weighted_cost.toFixed(2) : '--'}
              </div>
              <div className="text-[10px] font-mono text-slate-500">Accumulated traversal penalty</div>
            </div>

            {/* Geometric Distance */}
            <div className="bg-mars-950/80 border border-mars-800 rounded p-3">
              <div className="font-mono text-[10px] text-slate-400 uppercase tracking-wider mb-1">
                Geometric Distance
              </div>
              <div className="font-mono font-bold text-lg text-mars-sky">
                {path_result && isSuccess ? (
                  <>
                    {path_result.geometric_length.toFixed(2)}{' '}
                    <span className="text-[11px] text-slate-400 font-normal">units</span>
                  </>
                ) : (
                  '--'
                )}
              </div>
              <div className="text-[10px] font-mono text-slate-500">Physical Euclidean distance</div>
            </div>

            {/* Expanded Nodes */}
            <div className="bg-mars-950/80 border border-mars-800 rounded p-3">
              <div className="font-mono text-[10px] text-slate-400 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Activity className="w-3 h-3 text-purple-400" />
                Expanded Nodes
              </div>
              <div className="font-mono font-bold text-lg text-slate-100">
                {path_result ? path_result.expanded_nodes : '--'}
              </div>
              <div className="text-[10px] font-mono text-slate-500">Search graph complexity</div>
            </div>
          </div>
        </div>

        {/* Path Meaning & Engineering Explanation Box */}
        <div className="mt-4 p-3 bg-mars-950/90 rounded border border-mars-800/80 text-xs font-mono text-slate-400 flex items-start gap-2.5">
          <Info className="w-4 h-4 text-mars-sky flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed text-[11px]">
            <strong className="text-slate-200">Weighted Traversal Cost</strong> multiplies distance by terrain risk (e.g. 3.0× for rock, 5.0× for loose sand).
            The path planner purposefully detours around high-drag sand and boulder fields even if geometric distance increases, minimizing energy expenditure and mechanical slip.
          </p>
        </div>
      </div>

      {/* Right Column (4 cols): Terrain Distribution & Risk Telemetry */}
      <div className="lg:col-span-4 hud-panel p-5 flex flex-col justify-between">
        <div>
          {/* Header */}
          <div className="flex items-center justify-between pb-3.5 border-b border-mars-800">
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-mars-rust" />
              <h3 className="font-display font-bold text-sm tracking-wide text-white uppercase">
                Terrain Distribution
              </h3>
            </div>
            <span className="font-mono text-[11px] text-slate-400">
              {totalCells} Total Cells
            </span>
          </div>

          {/* Segmented Distribution Bar */}
          <div className="mt-4">
            <div className="h-3 w-full bg-mars-950 rounded-full overflow-hidden flex border border-mars-800">
              <div
                style={{ width: `${getPercentage(counts.clear)}%` }}
                className="bg-emerald-500 transition-all duration-300"
                title={`Clear: ${getPercentage(counts.clear)}%`}
              />
              <div
                style={{ width: `${getPercentage(counts.rocky)}%` }}
                className="bg-amber-500 transition-all duration-300"
                title={`Rocky: ${getPercentage(counts.rocky)}%`}
              />
              <div
                style={{ width: `${getPercentage(counts.loose)}%` }}
                className="bg-orange-600 transition-all duration-300"
                title={`Loose: ${getPercentage(counts.loose)}%`}
              />
              <div
                style={{ width: `${getPercentage(counts.obstacle)}%` }}
                className="bg-red-500 transition-all duration-300"
                title={`Obstacle: ${getPercentage(counts.obstacle)}%`}
              />
              <div
                style={{ width: `${getPercentage(counts.unknown)}%` }}
                className="bg-slate-400 transition-all duration-300"
                title={`Unknown: ${getPercentage(counts.unknown)}%`}
              />
            </div>
          </div>

          {/* Category Percentage Breakdown */}
          <div className="mt-4 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="text-slate-300">Clear Bedrock</span>
              </div>
              <span className="text-slate-200 font-bold">{getPercentage(counts.clear)}%</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="text-slate-300">Rocky Field</span>
              </div>
              <span className="text-slate-200 font-bold">{getPercentage(counts.rocky)}%</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-orange-600" />
                <span className="text-slate-300">Loose Sand</span>
              </div>
              <span className="text-slate-200 font-bold">{getPercentage(counts.loose)}%</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="text-slate-300">Obstacle / Hazard</span>
              </div>
              <span className="text-slate-200 font-bold">{getPercentage(counts.obstacle)}%</span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                <span className="text-slate-300">Unknown Terrain</span>
              </div>
              <span className="text-slate-200 font-bold">{getPercentage(counts.unknown)}%</span>
            </div>
          </div>
        </div>

        {/* Traversable Ratio Badge */}
        <div className="mt-4 pt-3 border-t border-mars-800 flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400">Traversability:</span>
          <span className="text-emerald-400 font-bold">
            {traversableCells} / {totalCells} Cells ({((traversableCells / totalCells) * 100).toFixed(0)}%)
          </span>
        </div>
      </div>
    </div>
  );
};
