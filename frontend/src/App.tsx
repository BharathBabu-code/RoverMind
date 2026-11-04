import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { MissionStatusBar } from './components/MissionStatusBar';
import { SpacecraftCursor } from './components/SpacecraftCursor';
import { ImageUploadPanel } from './components/ImageUploadPanel';
import { InteractiveMapViewer } from './components/InteractiveMapViewer';
import { AnalysisPanel } from './components/AnalysisPanel';
import { DiagnosticsDrawer } from './components/DiagnosticsDrawer';
import { MethodologyModal } from './components/MethodologyModal';
import { PlanetaryNarrative } from './components/PlanetaryNarrative';
import { PathCalculationExplainer } from './components/PathCalculationExplainer';
import { MissionIntelligencePanel } from './components/MissionIntelligencePanel';
import { MissionChatbot } from './components/MissionChatbot';
import {
  HealthResponse,
  ConfigStatusResponse,
  ImageMetadata,
  FullAnalysisResponse,
  MissionBriefing,
} from './types/api';
import {
  fetchHealth,
  fetchConfig,
  runFullAnalysis,
  recomputePath,
  loadSampleRoverImage,
  fetchMissionBriefing,
} from './services/api';
import { ShieldAlert, Compass, Sparkles, UploadCloud } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [config, setConfig] = useState<ConfigStatusResponse | null>(null);
  const [currentImage, setCurrentImage] = useState<ImageMetadata | null>(null);
  const [analysis, setAnalysis] = useState<FullAnalysisResponse | null>(null);
  const [briefing, setBriefing] = useState<MissionBriefing | null>(null);
  const [isBriefingLoading, setIsBriefingLoading] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPlanning, setIsPlanning] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(false);

  // Path planning interactive state
  const [startCoord, setStartCoord] = useState<[number, number] | null>(null);
  const [goalCoord, setGoalCoord] = useState<[number, number] | null>(null);
  const [selectionMode, setSelectionMode] = useState<'start' | 'goal'>('start');
  const [allowDiagonal, setAllowDiagonal] = useState(true);

  const workspaceRef = useRef<HTMLDivElement>(null);

  // Poll system health and configuration on startup
  useEffect(() => {
    const pollStatus = async () => {
      try {
        const [h, c] = await Promise.all([fetchHealth(), fetchConfig()]);
        setHealth(h);
        setConfig(c);
      } catch (e) {
        console.warn('Backend polling warning:', e);
      }
    };
    pollStatus();
    const interval = setInterval(pollStatus, 15000);
    return () => clearInterval(interval);
  }, []);

  const scrollToWorkspace = () => {
    workspaceRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Refresh or regenerate mission briefing
  const handleRefreshBriefing = async () => {
    if (!currentImage) return;
    setIsBriefingLoading(true);
    try {
      const b = await fetchMissionBriefing(currentImage.image_id);
      setBriefing(b);
    } catch (err) {
      console.warn('Failed to refresh mission briefing:', err);
    } finally {
      setIsBriefingLoading(false);
    }
  };

  // When a new image is selected or loaded, execute pipeline
  const handleImageSelected = async (metadata: ImageMetadata) => {
    setCurrentImage(metadata);
    setIsLoading(true);
    setBriefing(null);
    try {
      const res = await runFullAnalysis(metadata.image_id, {
        allowDiagonal,
      });
      setAnalysis(res);

      // Default start (bottom-center) and goal (top-center)
      const rows = res.segmentation.grid_height;
      const cols = res.segmentation.grid_width;
      setStartCoord([rows - 1, Math.floor(cols / 2)]);
      setGoalCoord([0, Math.floor(cols / 2)]);

      // Scroll smoothly to interactive workspace
      setTimeout(scrollToWorkspace, 100);

      // Asynchronously fetch mission briefing for the new analysis
      setIsBriefingLoading(true);
      fetchMissionBriefing(metadata.image_id)
        .then((b) => setBriefing(b))
        .catch((e) => console.warn('Briefing background load:', e))
        .finally(() => setIsBriefingLoading(false));
    } catch (err) {
      console.error('Failed to run full analysis:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Immediate load of the local authentic rover image
  const handleLoadSample = async () => {
    setIsLoading(true);
    try {
      const res = await loadSampleRoverImage();
      await handleImageSelected(res.metadata);
    } catch (err) {
      console.error('Failed to load sample image:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle cell selection on the interactive grid
  const handleSelectCoord = (coord: [number, number]) => {
    if (selectionMode === 'start') {
      setStartCoord(coord);
      setSelectionMode('goal'); // auto-advance to goal selection
    } else {
      setGoalCoord(coord);
    }
  };

  // Reset origin and goal to defaults
  const handleResetPoints = () => {
    if (analysis) {
      const rows = analysis.segmentation.grid_height;
      const cols = analysis.segmentation.grid_width;
      setStartCoord([rows - 1, Math.floor(cols / 2)]);
      setGoalCoord([0, Math.floor(cols / 2)]);
    } else {
      setStartCoord(null);
      setGoalCoord(null);
    }
  };

  // Recalculate A* path with updated coordinates or diagonal setting
  const handleRecalculatePath = async () => {
    if (!analysis || !startCoord || !goalCoord) return;
    setIsPlanning(true);
    try {
      const resp = await recomputePath({
        image_id: analysis.image_id,
        terrain_costs: analysis.costmap.terrain_costs,
        start: startCoord,
        goal: goalCoord,
        allow_diagonal: allowDiagonal,
      });
      setAnalysis({
        ...analysis,
        costmap: resp.costmap,
        path_result: resp.path_result,
        breakdown: resp.breakdown,
      });
    } catch (err) {
      console.error('Failed to recalculate path:', err);
    } finally {
      setIsPlanning(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-mars-950 text-slate-100 relative">
      {/* Interactive Spacecraft Cursor Layer */}
      <SpacecraftCursor />

      {/* Top Aerospace Mission Control Navigation Bar */}
      <Navbar
        health={health}
        config={config}
        onOpenMethodology={() => setIsMethodologyOpen(true)}
        onOpenUpload={() => setIsUploadOpen(true)}
        onLoadSample={handleLoadSample}
        isLoading={isLoading}
      />

      {/* Scroll-Driven Planetary Narrative Journey */}
      <PlanetaryNarrative
        currentImage={currentImage}
        analysis={analysis}
        isLoading={isLoading}
        onLoadSample={handleLoadSample}
        onOpenUpload={() => setIsUploadOpen(true)}
        onScrollToWorkspace={scrollToWorkspace}
      />

      {/* Operational Exploration Workspace Section */}
      <section
        id="workspace"
        ref={workspaceRef}
        className="scroll-mt-14 py-8 px-4 sm:px-6 lg:px-8 max-w-7xl w-full mx-auto"
      >
        <div className="flex items-center justify-between pb-4 mb-4 border-b border-mars-800">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <h2 className="font-display font-bold text-xl uppercase tracking-wider text-white">
              Phase 05 // Tactical Mission Control Workspace
            </h2>
          </div>
          <span className="font-mono text-xs text-slate-400">
            {analysis ? 'REAL-TIME COCKPIT ENGAGED' : 'AWAITING SURFACE FRAME INGESTION'}
          </span>
        </div>

        {/* Tactical Pipeline Status Bar */}
        <MissionStatusBar
          currentImage={currentImage}
          analysis={analysis}
          isLoading={isLoading}
          onLoadSample={handleLoadSample}
          onOpenUpload={() => setIsUploadOpen(true)}
        />

        {/* If Analysis is Active: Immersive Viewport & Telemetry HUD */}
        {analysis ? (
          <div className="space-y-6 mt-4">
            <InteractiveMapViewer
              analysis={analysis}
              startCoord={startCoord}
              goalCoord={goalCoord}
              onSelectCoord={handleSelectCoord}
              selectionMode={selectionMode}
              setSelectionMode={setSelectionMode}
              onResetPoints={handleResetPoints}
              onRecalculatePath={handleRecalculatePath}
              isPlanning={isPlanning}
            />

            {/* Dedicated Path Calculation Explainer & Dynamic Cost Configuration */}
            <PathCalculationExplainer
              analysis={analysis}
              onAnalysisUpdate={(updated) => setAnalysis(updated)}
              startCoord={startCoord}
              goalCoord={goalCoord}
              allowDiagonal={allowDiagonal}
            />

            <AnalysisPanel
              analysis={analysis}
              startCoord={startCoord}
              goalCoord={goalCoord}
              allowDiagonal={allowDiagonal}
              setAllowDiagonal={setAllowDiagonal}
              onRecalculatePath={handleRecalculatePath}
              onResetPoints={handleResetPoints}
              isPlanning={isPlanning}
            />

            {/* Mission Intelligence Observation Briefing */}
            <MissionIntelligencePanel
              briefing={briefing}
              isLoading={isBriefingLoading}
              onRefreshBriefing={handleRefreshBriefing}
            />

            {/* Contextual Mission Chatbot Assistant */}
            <MissionChatbot
              imageId={analysis.image_id}
              isReasoningConfigured={Boolean(config?.is_reasoning_api_configured)}
              reasoningModelName={config?.reasoning_model}
            />

            <DiagnosticsDrawer analysis={analysis} />
          </div>
        ) : (
          /* Empty Workspace Ingestion Prompt */
          <div className="hud-panel p-10 my-6 text-center border-mars-750">
            <div className="max-w-md mx-auto space-y-4">
              <div className="w-14 h-14 rounded-full bg-mars-900 border border-mars-800 flex items-center justify-center mx-auto text-mars-copper">
                <Compass className="w-7 h-7" />
              </div>
              <h3 className="font-display font-bold text-lg text-white uppercase">
                Ingest Surface Imagery to Initialize Workspace
              </h3>
              <p className="text-xs font-mono text-slate-400 leading-relaxed">
                Load the authentic 1648×1200 Jezero Crater navigation frame or upload a custom PNG/JPEG image to execute SAM 3.1 visual segmentation, generate costmaps, and solve A* paths.
              </p>
              <div className="pt-2 flex flex-wrap items-center justify-center gap-3">
                <button
                  onClick={handleLoadSample}
                  disabled={isLoading}
                  className="btn-primary text-xs px-4 py-2.5 flex items-center gap-2"
                >
                  <Sparkles className="w-4 h-4 text-mars-amber" />
                  {isLoading ? 'Ingesting Sample...' : 'Load Authentic Rover Frame'}
                </button>
                <button
                  onClick={() => setIsUploadOpen(true)}
                  disabled={isLoading}
                  className="btn-secondary text-xs px-4 py-2.5 flex items-center gap-2"
                >
                  <UploadCloud className="w-4 h-4 text-mars-sky" />
                  Upload Custom Frame
                </button>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Optical Frame Upload Dialog */}
      <ImageUploadPanel
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onImageSelected={handleImageSelected}
        isLoading={isLoading}
        setIsLoading={setIsLoading}
      />

      {/* Methodology Reference Modal */}
      <MethodologyModal
        isOpen={isMethodologyOpen}
        onClose={() => setIsMethodologyOpen(false)}
      />

      {/* Operational Disclaimer Footer */}
      <footer className="border-t border-mars-800 bg-mars-950 py-4 text-xs font-mono text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>RoverMind Mission Control — Computational Decision Support System</span>
          <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <ShieldAlert className="w-3.5 h-3.5 text-mars-rust" />
            Decision-support only. Monocular 2D imagery does not certify physical traversability or autonomous flight.
          </span>
        </div>
      </footer>
    </div>
  );
};
