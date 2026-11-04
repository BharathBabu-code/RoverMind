import React, { useState, useEffect } from 'react';
import {
  Compass,
  Sparkles,
  UploadCloud,
  ChevronDown,
  Cpu,
  Route,
  ArrowRight,
  Crosshair,
  Maximize2
} from 'lucide-react';
import { ImageMetadata, FullAnalysisResponse } from '../types/api';
import { RocketHeroGraphic } from './RocketHeroGraphic';

interface PlanetaryNarrativeProps {
  currentImage: ImageMetadata | null;
  analysis: FullAnalysisResponse | null;
  isLoading: boolean;
  onLoadSample: () => void;
  onOpenUpload: () => void;
  onScrollToWorkspace: () => void;
}

export const PlanetaryNarrative: React.FC<PlanetaryNarrativeProps> = ({
  currentImage,
  analysis,
  isLoading,
  onLoadSample,
  onOpenUpload,
  onScrollToWorkspace,
}) => {
  const [activeConceptTab, setActiveConceptTab] = useState<'rock' | 'sand' | 'obstacle' | 'clear'>('rock');
  const [launchProgress, setLaunchProgress] = useState(0);

  // Performant scroll-driven multi-stage rocket launch animation
  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setLaunchProgress(0.04);
      return;
    }

    let ticking = false;
    const handleScroll = () => {
      if (!ticking) {
        window.requestAnimationFrame(() => {
          const scrollY = window.scrollY;
          // Progress from 0 (at top of page) to 1.0 (after 750px of scroll)
          const heroLaunchDistance = 750;
          const progress = Math.min(1, Math.max(0, scrollY / heroLaunchDistance));
          setLaunchProgress(progress);
          ticking = false;
        });
        ticking = true;
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const getStageTelemetry = (p: number) => {
    if (p < 0.08) return 'PAD PRE-LAUNCH // T-00:05 // UMBILICAL SECURED';
    if (p < 0.28) return 'STAGE 02: IGNITION // T+00:02 // GANTRY RETRACTED';
    if (p < 0.75) return 'STAGE 03: SUPERSONIC LIFTOFF // T+00:18 // MAX-Q';
    return 'STAGE 04: TRANS-MARS INJECTION // ORBITAL ASCENT';
  };

  return (
    <div className="relative text-slate-100 overflow-hidden font-sans">
      {/* Background celestial grid & nebula effects */}
      <div className="absolute inset-0 pointer-events-none opacity-40">
        <div className="absolute top-10 left-1/4 w-96 h-96 bg-mars-rust/20 rounded-full blur-3xl animate-pulse" />
        <div className="absolute top-96 right-10 w-[500px] h-[500px] bg-mars-copper/15 rounded-full blur-[120px]" />
      </div>

      {/* =========================================================================
          SCENE 1: DEEP SPACE / ORBITAL APPROACH WITH CINEMATIC ROCKET LAUNCH
          ========================================================================= */}
      <section className="relative min-h-[96vh] flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 pt-10 pb-20 border-b border-mars-800/80 overflow-hidden">
        {/* Massive Rocket Visual with Multi-Stage Scroll-Driven Launch Sequence */}
        <div
          className="absolute inset-0 flex items-center justify-center pointer-events-none z-0 overflow-visible will-change-transform"
        >
          <div className="opacity-45 sm:opacity-55 md:opacity-70 filter brightness-110 drop-shadow-[0_20px_60px_rgba(234,88,12,0.35)]">
            <RocketHeroGraphic
              className="w-[340px] sm:w-[420px] md:w-[490px] translate-y-12 sm:translate-y-6"
              launchProgress={launchProgress}
            />
          </div>
        </div>

        {/* Ambient Darkened Radial Scrim behind text for 100% typography readability */}
        <div className="absolute inset-0 bg-radial-gradient pointer-events-none z-0 bg-[radial-gradient(ellipse_at_center,rgba(6,8,13,0.75)_0%,rgba(6,8,13,0.4)_65%,transparent_100%)]" />

        {/* Dynamic Orbital & Launch telemetry HUD badge */}
        <div className="relative z-10 flex items-center gap-3 px-4 py-1.5 rounded-full bg-mars-900/90 border border-mars-750 backdrop-blur-md mb-8 shadow-hud-glow">
          <span className={`flex h-2 w-2 rounded-full ${launchProgress > 0.08 ? 'bg-orange-500 animate-ping' : 'bg-emerald-400'}`} />
          <span className="font-mono text-[11px] tracking-widest text-slate-300 uppercase">
            {getStageTelemetry(launchProgress)}
          </span>
        </div>

        {/* Cinematic Main Title */}
        <div className="relative z-10 max-w-4xl mx-auto text-center space-y-6">
          <h1 className="font-display font-bold tracking-tight text-4xl sm:text-6xl md:text-7xl uppercase leading-none">
            <span className="block text-white drop-shadow-[0_4px_24px_rgba(255,255,255,0.15)]">
              ROVERMIND
            </span>
            <span className="block bg-gradient-to-r from-mars-copper via-mars-rust to-mars-amber bg-clip-text text-transparent mt-2">
              PLANETARY EXPLORATION
            </span>
          </h1>

          <p className="max-w-2xl mx-auto text-sm sm:text-base font-mono text-slate-300 leading-relaxed">
            AI-assisted surface hazard perception and deterministic route planning.
            Transforming monocular rover imagery into promptable Meta SAM 3.1 visual segmentations,
            impedance costmaps, and lowest-cost A* trajectories.
          </p>

          {/* Call to Actions with Magnetic Aerospace Glow */}
          <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
            <button
              onClick={onLoadSample}
              disabled={isLoading}
              className="btn-primary flex items-center gap-2.5 text-xs sm:text-sm px-6 py-3 shadow-hud-glow hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              <Sparkles className="w-4 h-4 text-mars-amber" />
              {isLoading ? 'Ingesting Jezero Frame...' : 'Load Authentic Rover Frame (1648×1200)'}
            </button>

            <button
              onClick={onOpenUpload}
              disabled={isLoading}
              className="btn-secondary flex items-center gap-2 text-xs sm:text-sm px-5 py-3 hover:scale-[1.02] transition-all"
            >
              <UploadCloud className="w-4 h-4 text-mars-sky" />
              Upload Custom Surface Frame
            </button>

            {analysis && (
              <button
                onClick={onScrollToWorkspace}
                className="px-5 py-3 rounded bg-mars-800 hover:bg-mars-750 border border-mars-700 text-xs font-mono text-emerald-400 flex items-center gap-2 transition-all"
              >
                <Maximize2 className="w-4 h-4" />
                Jump to Active Workspace
              </button>
            )}
          </div>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-6 flex flex-col items-center gap-2 text-slate-500 font-mono text-[10px] tracking-widest uppercase">
          <span>SCROLL TO DESCEND</span>
          <ChevronDown className="w-4 h-4 animate-bounce text-mars-rust" />
        </div>
      </section>

      {/* =========================================================================
          SCENE 2: DESCENT & OPTICAL SENSING
          ========================================================================= */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-mars-800/80">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 text-mars-copper font-mono text-xs uppercase tracking-wider">
              <span className="w-6 h-px bg-mars-copper" />
              PHASE 02 // SURFACE TELEMETRY INGESTION
            </div>

            <h2 className="font-display font-bold text-3xl sm:text-4xl text-white uppercase">
              Monocular Optical Ingestion & Verification
            </h2>

            <p className="text-xs sm:text-sm font-mono text-slate-300 leading-relaxed">
              Planetary rovers rely on mast-mounted Navigation Cameras (Navcam) and Hazard Avoidance Cameras (Hazcam).
              RoverMind validates uncompressed optical frames using strict, two-pass verification with Pillow,
              enforcing a 25-Megapixel decompression bomb ceiling and thread-safe dual memory bounding.
            </p>

            <div className="grid grid-cols-2 gap-3 pt-3">
              <div className="p-3.5 rounded bg-mars-900/80 border border-mars-800">
                <span className="text-[10px] font-mono text-slate-400 block uppercase">Standard Frame Resolution</span>
                <span className="font-display font-bold text-lg text-white">1648 × 1200 px</span>
                <span className="text-[10px] font-mono text-emerald-400 block mt-1">Verified Monocular Frame</span>
              </div>
              <div className="p-3.5 rounded bg-mars-900/80 border border-mars-800">
                <span className="text-[10px] font-mono text-slate-400 block uppercase">Pillow Pixel Ceiling</span>
                <span className="font-display font-bold text-lg text-white">25.0 Megapixels</span>
                <span className="text-[10px] font-mono text-mars-amber block mt-1">Decompression Bomb Proof</span>
              </div>
            </div>
          </div>

          {/* Visual sensor monitor card */}
          <div className="hud-panel p-6 corner-bracket border-mars-750">
            <div className="flex items-center justify-between pb-3 border-b border-mars-800 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-2">
                <Crosshair className="w-4 h-4 text-mars-rust" />
                OPTICAL SENSOR STREAM
              </span>
              <span>SOL 214 // FRAME INGEST</span>
            </div>

            <div className="my-4 aspect-[4/3] rounded bg-mars-950 border border-mars-800 relative overflow-hidden flex items-center justify-center">
              {currentImage ? (
                <img
                  src={`/api/images/${currentImage.image_id}/raw`}
                  alt="Current optical frame"
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="text-center p-6 space-y-3">
                  <div className="w-12 h-12 rounded-full bg-mars-900 border border-mars-800 flex items-center justify-center mx-auto text-mars-copper">
                    <Compass className="w-6 h-6" />
                  </div>
                  <p className="text-xs font-mono text-slate-400">
                    No active optical frame ingested in current session.
                  </p>
                  <button
                    onClick={onLoadSample}
                    disabled={isLoading}
                    className="btn-primary text-xs px-4 py-2"
                  >
                    Load Authentic Rover Frame
                  </button>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
              <span>MIME: {currentImage?.mime_type || 'image/png'}</span>
              <span>DIMENSIONS: {currentImage ? `${currentImage.width}×${currentImage.height}` : 'STANDBY'}</span>
            </div>
          </div>
        </div>
      </section>

      {/* =========================================================================
          SCENE 3: VISION INTELLIGENCE (META SAM 3.1)
          ========================================================================= */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-mars-800/80">
        <div className="text-center max-w-3xl mx-auto space-y-4 mb-14">
          <div className="inline-flex items-center gap-2 text-mars-amber font-mono text-xs uppercase tracking-wider">
            <Cpu className="w-4 h-4" />
            PHASE 03 // VISION INTELLIGENCE VIA META SAM 3.1
          </div>
          <h2 className="font-display font-bold text-3xl sm:text-4xl text-white uppercase">
            Promptable Terrain Semantic Segmentation
          </h2>
          <p className="text-xs sm:text-sm font-mono text-slate-300 leading-relaxed">
            Meta SAM 3.1 evaluates promptable visual concepts against the optical frame.
            The raw token grammar is streamed, parsed via the official <code className="text-mars-copper font-mono">meta-sam-parser</code>,
            and decoded into discrete bounding rasters.
          </p>
        </div>

        {/* Interactive Concept Showcase */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[
            {
              id: 'clear',
              name: 'Firm Bedrock',
              cost: '1.0 Impedance',
              color: 'text-emerald-400 border-emerald-500/30 bg-emerald-950/20',
              badge: 'bg-emerald-500',
              desc: 'Compact Martian soil and smooth bedrock; nominal wheel traction and minimal sinkage risk.'
            },
            {
              id: 'sand',
              name: 'Loose Sand Drift',
              cost: '3.5 Impedance',
              color: 'text-mars-amber border-amber-500/30 bg-amber-950/20',
              badge: 'bg-amber-500',
              desc: 'Windblown fine regolith and sand dunes; elevated motor current and wheel slippage risk.'
            },
            {
              id: 'rock',
              name: 'Rocky Field',
              cost: '6.0 Impedance',
              color: 'text-mars-rust border-orange-500/30 bg-orange-950/20',
              badge: 'bg-orange-500',
              desc: 'Scattered basalt boulders and angular stones; mechanical shock and high-centering hazard.'
            },
            {
              id: 'obstacle',
              name: 'Obstacle / Crater',
              cost: 'IMPASSABLE',
              color: 'text-red-400 border-red-500/30 bg-red-950/20',
              badge: 'bg-red-500',
              desc: 'Severe crater rims or large perched boulders exceeding suspension clearance. Blocked from traversal.'
            }
          ].map((c) => (
            <div
              key={c.id}
              onClick={() => setActiveConceptTab(c.id as any)}
              className={`p-5 rounded-lg border cursor-pointer transition-all ${
                activeConceptTab === c.id
                  ? `${c.color} shadow-hud-glow scale-[1.02]`
                  : 'bg-mars-900/60 border-mars-800 text-slate-400 hover:border-mars-700'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <span className="font-display font-bold text-sm text-white uppercase">{c.name}</span>
                <span className={`w-2.5 h-2.5 rounded-full ${c.badge}`} />
              </div>
              <span className="font-mono text-[11px] font-semibold block mb-2">{c.cost}</span>
              <p className="text-[11px] font-mono leading-relaxed text-slate-300">{c.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* =========================================================================
          SCENE 4: RISK COSTMAP & A* PATH PLANNING
          ========================================================================= */}
      <section className="py-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto border-b border-mars-800/80">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="hud-panel p-6 corner-bracket border-mars-750">
            <div className="flex items-center justify-between pb-3 border-b border-mars-800 text-xs font-mono text-slate-400">
              <span className="flex items-center gap-2">
                <Route className="w-4 h-4 text-emerald-400" />
                A* HEURISTIC TRAJECTORY ENGINE
              </span>
              <span>OCTILE METRIC (8-WAY)</span>
            </div>

            <div className="my-5 p-4 rounded bg-mars-950 border border-mars-800 space-y-3 font-mono text-xs">
              <div className="flex justify-between text-slate-300">
                <span>Cardinal Step Cost:</span>
                <span className="text-emerald-400 font-bold">1.0 × cell_cost</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Diagonal Step Cost:</span>
                <span className="text-mars-amber font-bold">√2 × ((cost_A + cost_B) / 2)</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Corner-Cutting Protection:</span>
                <span className="text-mars-sky font-bold">STRICTLY FORBIDDEN</span>
              </div>
              <div className="flex justify-between text-slate-300">
                <span>Admissible Heuristic:</span>
                <span className="text-purple-400 font-bold">Octile Distance h(n)</span>
              </div>
            </div>

            <p className="text-[11px] font-mono text-slate-400 leading-relaxed">
              The custom A* algorithm guarantees mathematical optimality on discrete cost grids,
              bypassing impassable obstacles while trading off distance against severe terrain shock.
            </p>
          </div>

          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 text-emerald-400 font-mono text-xs uppercase tracking-wider">
              <span className="w-6 h-px bg-emerald-400" />
              PHASE 04 // TACTICAL PATH DETERMINATION
            </div>

            <h2 className="font-display font-bold text-3xl sm:text-4xl text-white uppercase">
              Impedance Risk Costmaps & Custom A*
            </h2>

            <p className="text-xs sm:text-sm font-mono text-slate-300 leading-relaxed">
              RoverMind transforms semantic categories into a continuous impedance potential field.
              The custom A* path-planner finds the global minimum of traversal cost from the rover's current
              location to the target waypoint.
            </p>

            <div className="pt-2">
              <button
                onClick={onScrollToWorkspace}
                className="btn-primary flex items-center gap-2 text-xs sm:text-sm px-6 py-3"
              >
                <span>Enter Interactive Mission Control Workspace</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
