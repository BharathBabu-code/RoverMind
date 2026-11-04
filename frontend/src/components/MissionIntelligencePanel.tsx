import React from 'react';
import {
  Brain,
  Compass,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Info,
  ShieldCheck,
  Layers
} from 'lucide-react';
import { MissionBriefing } from '../types/api';

interface MissionIntelligencePanelProps {
  briefing: MissionBriefing | null;
  isLoading: boolean;
  onRefreshBriefing: () => void;
}

export const MissionIntelligencePanel: React.FC<MissionIntelligencePanelProps> = ({
  briefing,
  isLoading,
  onRefreshBriefing,
}) => {
  if (!briefing) {
    return (
      <div className="hud-panel p-6 border-mars-750 text-center text-slate-400 font-mono text-xs">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 text-mars-amber">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Generating Mission Intelligence Briefing...
          </div>
        ) : (
          <p>Mission briefing will generate automatically once surface analysis completes.</p>
        )}
      </div>
    );
  }

  const { observation_overview, navigation_assessment, risk_and_uncertainty, mission_takeaways } = briefing;

  return (
    <div className="hud-panel corner-bracket border-mars-750 p-6 space-y-6">
      {/* Header with AI Provenance & Refresh */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-mars-800">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-gradient-to-br from-mars-copper to-mars-rust flex items-center justify-center text-white shadow-hud-glow">
            <Brain className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-display font-bold text-base text-white uppercase tracking-wider flex items-center gap-2">
              Mission Intelligence & Observation Briefing
            </h3>
            <span className="font-mono text-[11px] text-slate-400">
              Reasoning Layer // Synthesizing Visual Segmentation, Costmaps & A* Telemetry
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center">
          <div className={`px-2.5 py-1 rounded-full text-[10px] font-mono tracking-wider uppercase border flex items-center gap-1.5 ${
            briefing.is_ai_generated
              ? 'bg-emerald-950/60 border-emerald-500/40 text-emerald-400'
              : 'bg-amber-950/60 border-amber-500/40 text-amber-300'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${briefing.is_ai_generated ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}`} />
            {briefing.source_model.includes('DRY RUN')
              ? 'DRY RUN SIMULATION'
              : briefing.source_model.includes('DISABLED')
              ? 'EXTERNAL INFERENCE DISABLED'
              : briefing.is_ai_generated
              ? `META REASONING (${briefing.source_model.toUpperCase()})`
              : 'DETERMINISTIC RULE ENGINE'}
          </div>

          <button
            onClick={onRefreshBriefing}
            disabled={isLoading}
            className="p-1.5 rounded bg-mars-800 hover:bg-mars-750 border border-mars-700 text-slate-300 hover:text-white transition-all"
            title="Regenerate Briefing"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin text-mars-amber' : ''}`} />
          </button>
        </div>
      </div>

      {/* Grid of Briefing Sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Section A: Observation Overview */}
        <div className="p-4 rounded bg-mars-950/80 border border-mars-800 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-mars-copper font-display font-bold text-xs uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Layers className="w-4 h-4" />
              A // Terrain Perception & Composition
            </span>
            <span className="text-[10px] text-slate-400">
              Dominant: <strong className="text-white uppercase">{observation_overview.dominant_terrain || 'N/A'}</strong>
            </span>
          </div>

          {observation_overview.terrain_breakdown && (
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              {Object.entries(observation_overview.terrain_breakdown).map(([label, desc]) => (
                <div key={label} className="p-2 rounded bg-mars-900 border border-mars-800">
                  <span className="text-slate-400 block uppercase font-semibold text-[10px]">{label}</span>
                  <span className="text-slate-200">{desc}</span>
                </div>
              ))}
            </div>
          )}

          {observation_overview.spatial_highlights && observation_overview.spatial_highlights.length > 0 && (
            <div className="space-y-1 pt-1">
              <span className="text-[10px] text-slate-500 uppercase tracking-widest block">Spatial Observations:</span>
              <ul className="list-disc list-inside text-slate-300 space-y-1 text-[11px]">
                {observation_overview.spatial_highlights.map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Section B: Navigation Assessment */}
        <div className="p-4 rounded bg-mars-950/80 border border-mars-800 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-emerald-400 font-display font-bold text-xs uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <Compass className="w-4 h-4" />
              B // A* Navigation & Feasibility
            </span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              navigation_assessment.path_feasibility === 'FEASIBLE'
                ? 'bg-emerald-950 text-emerald-400 border border-emerald-500/30'
                : 'bg-red-950 text-red-400 border border-red-500/30'
            }`}>
              {navigation_assessment.path_feasibility || 'UNKNOWN'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded bg-mars-900 border border-mars-800">
              <span className="text-[10px] text-slate-400 block uppercase">Waypoints</span>
              <span className="font-display font-bold text-white text-base">{navigation_assessment.waypoints_count ?? 0}</span>
            </div>
            <div className="p-2 rounded bg-mars-900 border border-mars-800">
              <span className="text-[10px] text-slate-400 block uppercase">Weighted Cost</span>
              <span className="font-display font-bold text-emerald-400 text-base">{navigation_assessment.total_weighted_cost?.toFixed(1) ?? '0.0'}</span>
            </div>
            <div className="p-2 rounded bg-mars-900 border border-mars-800">
              <span className="text-[10px] text-slate-400 block uppercase">Geometric Dist</span>
              <span className="font-display font-bold text-mars-sky text-base">{navigation_assessment.geometric_length_units?.toFixed(1) ?? '0.0'}</span>
            </div>
          </div>

          <div className="text-[11px] text-slate-300 space-y-1">
            <p><strong className="text-slate-400">Obstacle Avoidance:</strong> {navigation_assessment.obstacle_avoidance}</p>
            <p><strong className="text-slate-400">Optimization:</strong> {navigation_assessment.influencing_factors}</p>
          </div>
        </div>

        {/* Section C: Risk & Uncertainty */}
        <div className="p-4 rounded bg-mars-950/80 border border-mars-800 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-mars-amber font-display font-bold text-xs uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <AlertTriangle className="w-4 h-4 text-mars-amber" />
              C // Terrain Risk & Operational Uncertainty
            </span>
          </div>

          {risk_and_uncertainty.elevated_cost_regions && (
            <div>
              <span className="text-[10px] text-slate-500 uppercase tracking-widest block mb-1">Elevated Impedance Zones:</span>
              <div className="flex flex-wrap gap-1.5">
                {risk_and_uncertainty.elevated_cost_regions.map((r, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-mars-900 border border-mars-800 text-[11px] text-amber-300">
                    {r}
                  </span>
                ))}
              </div>
            </div>
          )}

          {risk_and_uncertainty.unknown_unmapped_regions && (
            <p className="text-[11px] text-slate-300">
              <strong className="text-slate-400">Unmapped Cells:</strong> {risk_and_uncertainty.unknown_unmapped_regions}
            </p>
          )}

          {/* Monocular Limitation Callout */}
          <div className="p-2.5 rounded bg-mars-900/90 border border-mars-800 text-[10px] text-slate-400 space-y-1">
            <span className="text-mars-rust font-bold uppercase flex items-center gap-1">
              <Info className="w-3 h-3" />
              Monocular Sensor Boundary Notice:
            </span>
            <ul className="list-disc list-inside space-y-0.5">
              {risk_and_uncertainty.monocular_limitations?.map((lim, idx) => (
                <li key={idx}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Section D: Mission Takeaways */}
        <div className="p-4 rounded bg-mars-950/80 border border-mars-800 space-y-3 font-mono text-xs">
          <div className="flex items-center justify-between text-purple-400 font-display font-bold text-xs uppercase tracking-wider">
            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4" />
              D // Actionable Operator Takeaways
            </span>
          </div>

          <div className="space-y-2">
            {mission_takeaways.map((takeaway, i) => (
              <div key={i} className="flex items-start gap-2 p-2 rounded bg-mars-900 border border-mars-800 text-[11px] text-slate-200">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <span>{takeaway}</span>
              </div>
            ))}
          </div>

          <div className="p-2.5 rounded bg-mars-900/60 border border-mars-800/80 text-[10px] text-slate-500">
            <strong>Decision-Support Notice:</strong> RoverMind estimates traversal impedance on 2D imagery.
            Outputs do not guarantee physical traversability. Always cross-reference high-resolution stereoscopic imagery.
          </div>
        </div>
      </div>
    </div>
  );
};
