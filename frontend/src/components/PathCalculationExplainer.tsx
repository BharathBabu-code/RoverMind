import React, { useState } from 'react';
import {
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Route,
  Zap,
  Activity,
  ShieldAlert,
  Info
} from 'lucide-react';
import { FullAnalysisResponse, RecomputePathResponse } from '../types/api';
import { recomputePath } from '../services/api';

interface PathCalculationExplainerProps {
  analysis: FullAnalysisResponse;
  onAnalysisUpdate: (updated: FullAnalysisResponse) => void;
  startCoord: [number, number] | null;
  goalCoord: [number, number] | null;
  allowDiagonal: boolean;
}

export const PathCalculationExplainer: React.FC<PathCalculationExplainerProps> = ({
  analysis,
  onAnalysisUpdate,
  startCoord,
  goalCoord,
  allowDiagonal,
}) => {
  const { costmap, path_result, breakdown } = analysis;
  const terrainCosts = costmap.terrain_costs;

  // Local state for dynamic terrain cost adjustments
  const [customCosts, setCustomCosts] = useState<Record<string, number>>({
    clear: Number(terrainCosts.clear ?? 1.0),
    rocky: Number(terrainCosts.rocky ?? 3.0),
    loose: Number(terrainCosts.loose ?? 5.0),
    unknown: Number(terrainCosts.unknown ?? 2.0),
  });

  const [isRecomputing, setIsRecomputing] = useState(false);
  const [recomputeError, setRecomputeError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'breakdown' | 'costs' | 'math' | 'provenance'>('breakdown');

  // Handle slider or input change
  const handleCostChange = (label: string, value: number) => {
    setCustomCosts((prev) => ({
      ...prev,
      [label]: Math.max(0.1, Math.min(50.0, parseFloat(value.toFixed(1)))),
    }));
  };

  // Recompute route via backend API
  const handleRecompute = async () => {
    setIsRecomputing(true);
    setRecomputeError(null);
    try {
      const resp: RecomputePathResponse = await recomputePath({
        image_id: analysis.image_id,
        terrain_costs: {
          clear: customCosts.clear,
          rocky: customCosts.rocky,
          loose: customCosts.loose,
          unknown: customCosts.unknown,
          obstacle: null, // Obstacles strictly blocked
        },
        start: startCoord ?? undefined,
        goal: goalCoord ?? undefined,
        allow_diagonal: allowDiagonal,
      });

      // Update parent analysis state
      onAnalysisUpdate({
        ...analysis,
        costmap: resp.costmap,
        path_result: resp.path_result,
        breakdown: resp.breakdown,
      });
    } catch (err) {
      setRecomputeError(err instanceof Error ? err.message : 'Recomputation failed.');
    } finally {
      setIsRecomputing(false);
    }
  };

  // Reset costs to default constants
  const handleResetDefaults = () => {
    setCustomCosts({
      clear: 1.0,
      rocky: 3.0,
      loose: 5.0,
      unknown: 2.0,
    });
  };

  return (
    <div className="hud-panel corner-bracket mb-6 border-mars-750 bg-gradient-to-b from-mars-950 via-mars-900 to-mars-950">
      {/* Header with Explainer Badge and Tab Selectors */}
      <div className="hud-panel-header flex flex-wrap items-center justify-between gap-3 bg-mars-950/90 border-b border-mars-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-mars-800 border border-mars-copper/50 flex items-center justify-center text-mars-amber shadow-sm">
            <Route className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-display font-bold text-sm text-white tracking-wide uppercase flex items-center gap-2">
              How Was This Route Calculated?
              <span className="text-[10px] px-1.5 py-0.2 rounded bg-mars-800 text-mars-sky font-mono border border-mars-700">
                A* EXPLAINABILITY
              </span>
            </h2>
            <p className="text-[11px] font-mono text-slate-400">
              Deterministic Traversal Physics, Terrain Impedance & Heuristic Search
            </p>
          </div>
        </div>

        {/* Tab Controls */}
        <div className="flex items-center gap-1.5 bg-mars-900 p-1 rounded border border-mars-800 text-xs font-mono">
          <button
            onClick={() => setActiveTab('breakdown')}
            className={`px-3 py-1 rounded transition-all ${
              activeTab === 'breakdown'
                ? 'bg-mars-rust text-white font-semibold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Cost Breakdown
          </button>
          <button
            onClick={() => setActiveTab('costs')}
            className={`px-3 py-1 rounded transition-all ${
              activeTab === 'costs'
                ? 'bg-mars-rust text-white font-semibold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Terrain Weights
          </button>
          <button
            onClick={() => setActiveTab('math')}
            className={`px-3 py-1 rounded transition-all ${
              activeTab === 'math'
                ? 'bg-mars-rust text-white font-semibold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            A* Mathematics
          </button>
          <button
            onClick={() => setActiveTab('provenance')}
            className={`px-3 py-1 rounded transition-all ${
              activeTab === 'provenance'
                ? 'bg-mars-rust text-white font-semibold'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Data Provenance
          </button>
        </div>
      </div>

      <div className="p-5 space-y-6">
        {/* =========================================================================
            TAB 1: RECONCILED ROUTE COST BREAKDOWN
            ========================================================================= */}
        {activeTab === 'breakdown' && (
          <div className="space-y-5">
            {/* High-level Summary Metrics Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 font-mono">
              <div className="p-3 rounded bg-mars-850/80 border border-mars-750">
                <span className="text-[10px] text-slate-400 block uppercase">Total Weighted Cost</span>
                <span className="text-xl font-bold text-mars-amber">
                  {path_result ? path_result.total_weighted_cost.toFixed(2) : '0.00'}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Sum of Step Impedance</span>
              </div>

              <div className="p-3 rounded bg-mars-850/80 border border-mars-750">
                <span className="text-[10px] text-slate-400 block uppercase">Geometric Length</span>
                <span className="text-xl font-bold text-mars-sky">
                  {path_result ? path_result.geometric_length.toFixed(2) : '0.00'}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Grid Unit Distance</span>
              </div>

              <div className="p-3 rounded bg-mars-850/80 border border-mars-750">
                <span className="text-[10px] text-slate-400 block uppercase">Waypoints Count</span>
                <span className="text-xl font-bold text-emerald-400">
                  {path_result ? path_result.path.length : 0}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Discrete Nodes</span>
              </div>

              <div className="p-3 rounded bg-mars-850/80 border border-mars-750">
                <span className="text-[10px] text-slate-400 block uppercase">Expanded Nodes</span>
                <span className="text-xl font-bold text-slate-200">
                  {path_result ? path_result.expanded_nodes : 0}
                </span>
                <span className="text-[10px] text-slate-500 block mt-0.5">Search Complexity</span>
              </div>
            </div>

            {/* Step Geometry & Mathematical Reconciliation */}
            {breakdown && (
              <div className="p-4 rounded-lg bg-mars-950 border border-mars-800 space-y-3 font-mono text-xs">
                <div className="flex items-center justify-between pb-2 border-b border-mars-800">
                  <span className="text-slate-300 font-bold uppercase tracking-wider flex items-center gap-2">
                    <Activity className="w-4 h-4 text-mars-rust" />
                    Exact Step-Cost Reconciliation
                  </span>
                  {breakdown.reconciled ? (
                    <span className="text-emerald-400 flex items-center gap-1.5 text-[11px] font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      RECONCILED (0.0000 Deviation)
                    </span>
                  ) : (
                    <span className="text-amber-400 flex items-center gap-1.5 text-[11px] font-semibold">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      APPROXIMATE MATCH
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-1">
                  {/* Step Movement Types */}
                  <div className="space-y-1.5">
                    <span className="text-slate-400 text-[11px] block">Step Geometry:</span>
                    <div className="flex justify-between p-2 rounded bg-mars-900 border border-mars-800">
                      <span className="text-slate-300">Cardinal Steps (1.0x distance):</span>
                      <strong className="text-mars-sky">{breakdown.cardinal_steps_count}</strong>
                    </div>
                    <div className="flex justify-between p-2 rounded bg-mars-900 border border-mars-800">
                      <span className="text-slate-300">Diagonal Steps (√2 ≈ 1.414x distance):</span>
                      <strong className="text-mars-sky">{breakdown.diagonal_steps_count}</strong>
                    </div>
                  </div>

                  {/* Terrain Class Contributions */}
                  <div className="space-y-1.5">
                    <span className="text-slate-400 text-[11px] block">Cost Contribution by Terrain:</span>
                    <div className="space-y-1">
                      {Object.entries(breakdown.cost_contributions).map(([cat, costVal]) => (
                        <div
                          key={cat}
                          className="flex justify-between p-1.5 rounded bg-mars-900 border border-mars-800/80 text-[11px]"
                        >
                          <span className="text-slate-300 uppercase">{cat}:</span>
                          <span className="text-mars-amber font-bold">
                            {costVal.toFixed(2)} cost ({Math.round(path_result?.total_weighted_cost ? (costVal / path_result.total_weighted_cost) * 100 : 0)}%)
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Unknown Terrain Warning Banner */}
                {breakdown.unknown_warning && (
                  <div className="p-3 rounded bg-amber-950/60 border border-amber-500/40 text-amber-200 text-xs flex items-start gap-2.5 mt-3">
                    <ShieldAlert className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                    <div>
                      <strong className="block font-bold">Unknown Terrain Exposure: {breakdown.unknown_percentage}%</strong>
                      <span>
                        The computed route crosses {breakdown.unknown_cells_count} unclassified or shadow-obscured grid cells. 
                        A penalty weight of {terrainCosts.unknown ?? 2.0}x was applied. Monocular cameras cannot verify physical stability in unclassified areas.
                      </span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Why did A* avoid other regions? */}
            <div className="p-4 rounded-lg bg-mars-850/60 border border-mars-750 space-y-2 font-mono text-xs">
              <h3 className="font-bold text-slate-200 flex items-center gap-1.5 uppercase tracking-wide">
                <Info className="w-4 h-4 text-mars-sky" />
                Why Did A* Select This Corridor?
              </h3>
              <p className="text-slate-300 leading-relaxed">
                A* evaluates each cell using the objective function <strong className="text-mars-amber">f(n) = g(n) + h(n)</strong>. 
                Cells identified as <span className="text-red-400 font-semibold">Obstacles</span> are strictly impassable (impedance = ∞), 
                forcing the search tree to branch around boulder clusters and crater rims. 
                Areas of <span className="text-orange-400 font-semibold">Loose Sand (5.0x)</span> and <span className="text-amber-400 font-semibold">Rocky Terrain (3.0x)</span> 
                are heavily penalized relative to <span className="text-emerald-400 font-semibold">Clear Bedrock (1.0x)</span>, causing the algorithm 
                to detour slightly longer geometrically in order to achieve a lower cumulative traversal impedance.
              </p>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 2: TERRAIN WEIGHT CONFIGURATION
            ========================================================================= */}
        {activeTab === 'costs' && (
          <div className="space-y-5 font-mono text-xs">
            <div className="flex items-center justify-between pb-3 border-b border-mars-800">
              <div>
                <h3 className="font-bold text-slate-200 uppercase tracking-wide">
                  Interactive Terrain Cost Weights
                </h3>
                <p className="text-slate-400 text-[11px]">
                  Adjust the impedance multipliers and recalculate the A* route to observe how routing decisions change.
                </p>
              </div>
              <button
                onClick={handleResetDefaults}
                className="btn-ghost text-xs flex items-center gap-1 border border-mars-750"
              >
                <RotateCcw className="w-3 h-3" />
                Reset Defaults
              </button>
            </div>

            {/* Sliders Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Clear */}
              <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-emerald-400 font-bold uppercase flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
                    Clear Bedrock
                  </span>
                  <span className="text-white font-bold text-sm">{customCosts.clear.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="5.0"
                  step="0.1"
                  value={customCosts.clear}
                  onChange={(e) => handleCostChange('clear', parseFloat(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400 block">Baseline firm ground / flat bedrock.</span>
              </div>

              {/* Rocky */}
              <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-amber-400 font-bold uppercase flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                    Rocky Field
                  </span>
                  <span className="text-white font-bold text-sm">{customCosts.rocky.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="20.0"
                  step="0.5"
                  value={customCosts.rocky}
                  onChange={(e) => handleCostChange('rocky', parseFloat(e.target.value))}
                  className="w-full accent-amber-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400 block">Scattered stones and boulders, wheel wear hazard.</span>
              </div>

              {/* Loose Sand */}
              <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-orange-500 font-bold uppercase flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-orange-500" />
                    Loose Sand Drift
                  </span>
                  <span className="text-white font-bold text-sm">{customCosts.loose.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="25.0"
                  step="0.5"
                  value={customCosts.loose}
                  onChange={(e) => handleCostChange('loose', parseFloat(e.target.value))}
                  className="w-full accent-orange-500 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400 block">Soft dunes and wheel sinkage trap hazards.</span>
              </div>

              {/* Unknown */}
              <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-slate-300 font-bold uppercase flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-full bg-slate-400" />
                    Unknown / Shadow Precaution
                  </span>
                  <span className="text-white font-bold text-sm">{customCosts.unknown.toFixed(1)}x</span>
                </div>
                <input
                  type="range"
                  min="1.0"
                  max="15.0"
                  step="0.5"
                  value={customCosts.unknown}
                  onChange={(e) => handleCostChange('unknown', parseFloat(e.target.value))}
                  className="w-full accent-slate-400 cursor-pointer"
                />
                <span className="text-[10px] text-slate-400 block">Unmapped or optical shadow regions.</span>
              </div>
            </div>

            {/* Obstacle Notice */}
            <div className="p-3 rounded bg-red-950/40 border border-red-500/30 text-red-300 text-xs flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span>
                  <strong>Obstacles (Impassable / Blocked):</strong> Strict safety policy locks obstacles to infinite cost (null). 
                  They can never be made traversable to prevent simulated rover high-centering.
                </span>
              </div>
              <span className="font-bold text-red-400">LOCKED</span>
            </div>

            {/* Recompute Action Button */}
            {recomputeError && (
              <div className="p-2.5 rounded bg-red-950/80 border border-red-500 text-red-200 text-xs">
                {recomputeError}
              </div>
            )}

            <div className="pt-2 flex items-center justify-end gap-3">
              <button
                onClick={handleRecompute}
                disabled={isRecomputing}
                className="btn-primary text-xs px-5 py-2.5 flex items-center gap-2 shadow-md hover:scale-[1.02] transition-all"
              >
                <Zap className="w-4 h-4 text-mars-amber" />
                {isRecomputing ? 'Recomputing A* Route...' : 'Recompute Route with New Costs'}
              </button>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 3: A* MATHEMATICS
            ========================================================================= */}
        {activeTab === 'math' && (
          <div className="space-y-4 font-mono text-xs text-slate-300 leading-relaxed">
            <h3 className="font-bold text-white uppercase text-sm">
              Mathematical Formulation of RoverMind A* Search
            </h3>

            <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
              <strong className="text-mars-rust block uppercase text-[11px]">1. Step Cost Formula:</strong>
              <p>
                The transition cost from current node <code>u</code> to adjacent destination node <code>v</code> is:
              </p>
              <div className="p-2 rounded bg-mars-900 border border-mars-800 text-mars-sky font-semibold text-center">
                Δg(u, v) = d(u, v) × Cost(v)
              </div>
              <p className="text-[11px] text-slate-400">
                Where <code>d(u, v) = 1.0</code> for cardinal transitions (N, S, E, W), and <code>d(u, v) = √2 ≈ 1.4142</code> for diagonal moves. 
                <code>Cost(v)</code> is the configured terrain impedance at the destination cell.
              </p>
            </div>

            <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
              <strong className="text-mars-rust block uppercase text-[11px]">2. Admissible Octile Heuristic:</strong>
              <p>
                To guarantee optimality under 8-directional movement, RoverMind computes the Octile distance scaled by <code>min_cost</code>:
              </p>
              <div className="p-2 rounded bg-mars-900 border border-mars-800 text-mars-amber font-semibold text-center">
                h(r, c) = [ max(Δr, Δc) + (√2 - 1) min(Δr, Δc) ] × min_cost
              </div>
              <p className="text-[11px] text-slate-400">
                Because <code>min_cost ≤ Cost(v)</code> for all traversable cells, <code>h(r, c)</code> is strictly admissible and consistent, 
                guaranteeing that A* discovers the mathematically optimal lowest-cost trajectory.
              </p>
            </div>

            <div className="p-3.5 rounded bg-mars-950 border border-mars-800 space-y-2">
              <strong className="text-mars-rust block uppercase text-[11px]">3. Corner-Cutting Prevention:</strong>
              <p>
                Diagonal transitions between <code>(r, c)</code> and <code>(r+dr, c+dc)</code> are strictly rejected if either orthogonal neighbor is blocked:
              </p>
              <div className="p-2 rounded bg-mars-900 border border-mars-800 text-slate-200 font-semibold text-center">
                Valid Diagonal ⇔ Cost(r+dr, c) ≠ null AND Cost(r, c+dc) ≠ null
              </div>
              <p className="text-[11px] text-slate-400">
                This prevents the mathematical route from "squeezing" through impassable diagonal corners, respecting the physical chassis width of the rover.
              </p>
            </div>
          </div>
        )}

        {/* =========================================================================
            TAB 4: DATA PROVENANCE (REAL VS SYNTHETIC AUDIT)
            ========================================================================= */}
        {activeTab === 'provenance' && (
          <div className="space-y-4 font-mono text-xs text-slate-300">
            <h3 className="font-bold text-white uppercase text-sm">
              Offline Demonstration Audit: Real vs. Simulated Components
            </h3>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              Because RoverMind is designed to run completely offline without mandatory cloud credentials, 
              here is an honest, line-by-line accounting of what is genuinely computed vs. synthetic fixtures:
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse border border-mars-800">
                <thead>
                  <tr className="bg-mars-900 text-slate-300 text-[11px] uppercase">
                    <th className="p-2.5 border border-mars-800">Pipeline Component</th>
                    <th className="p-2.5 border border-mars-800">Offline Demonstration Mode</th>
                    <th className="p-2.5 border border-mars-800">Live API Mode (With Keys)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-mars-800/80">
                  <tr>
                    <td className="p-2.5 font-bold text-white">Uploaded Rover Frame</td>
                    <td className="p-2.5 text-emerald-400">REAL (Authentic raw pixels ingested & validated)</td>
                    <td className="p-2.5 text-emerald-400">REAL (Authentic raw pixels ingested & validated)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">Visual Segmentation</td>
                    <td className="p-2.5 text-amber-400">SYNTHETIC (Predefined geometric benchmark pattern)</td>
                    <td className="p-2.5 text-emerald-400">REAL AI (Meta SAM 3.1 streaming token inference)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">Terrain Normalization</td>
                    <td className="p-2.5 text-emerald-400">REAL ALGORITHM (Maps labels to canonical classes)</td>
                    <td className="p-2.5 text-emerald-400">REAL ALGORITHM (Maps SAM concepts to classes)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">Risk Costmap</td>
                    <td className="p-2.5 text-emerald-400">REAL CALCULATION (Built from terrain weights)</td>
                    <td className="p-2.5 text-emerald-400">REAL CALCULATION (Built from terrain weights)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">A* Path Planning</td>
                    <td className="p-2.5 text-emerald-400">REAL ALGORITHM (8-way optimal octile search)</td>
                    <td className="p-2.5 text-emerald-400">REAL ALGORITHM (8-way optimal octile search)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">Mission Briefing</td>
                    <td className="p-2.5 text-slate-400">DETERMINISTIC (Statistical rule engine)</td>
                    <td className="p-2.5 text-emerald-400">REAL AI (Meta Llama 3.3 70B Instruct LLM)</td>
                  </tr>
                  <tr>
                    <td className="p-2.5 font-bold text-white">Mission Chatbot</td>
                    <td className="p-2.5 text-slate-400">DETERMINISTIC (Pattern query interpreter + tools)</td>
                    <td className="p-2.5 text-emerald-400">REAL AI (Llama tool-calling loop, max 4 turns)</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="p-3 rounded bg-mars-850 border border-mars-750 text-[11px] text-slate-400">
              <strong className="text-slate-200 block mb-1">Key Scientific Conclusion:</strong>
              When running offline, A* genuinely finds the lowest-cost route across the discrete cost grid, 
              but the grid reflects a synthetic fixture rather than an image-vision model analysing the uploaded pixels.
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
