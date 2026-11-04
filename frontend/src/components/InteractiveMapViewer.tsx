import React, { useState, useRef } from 'react';
import {
  Layers,
  MapPin,
  Flag,
  Crosshair,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Eye,
  Sliders,
  RotateCcw,
  AlertOctagon,
  CheckCircle2,
  Grid as GridIcon,
  HelpCircle,
  Navigation,
  RefreshCw,
  AlertTriangle,
} from 'lucide-react';
import { FullAnalysisResponse } from '../types/api';
import { getRawImageUrl } from '../services/api';

interface InteractiveMapViewerProps {
  analysis: FullAnalysisResponse;
  startCoord: [number, number] | null;
  goalCoord: [number, number] | null;
  onSelectCoord: (coord: [number, number]) => void;
  selectionMode: 'start' | 'goal';
  setSelectionMode: (mode: 'start' | 'goal') => void;
  onResetPoints: () => void;
  onRecalculatePath?: () => void;
  isPlanning?: boolean;
}

export const InteractiveMapViewer: React.FC<InteractiveMapViewerProps> = ({
  analysis,
  startCoord,
  goalCoord,
  onSelectCoord,
  selectionMode,
  setSelectionMode,
  onResetPoints,
  onRecalculatePath,
  isPlanning = false,
}) => {
  // Layer visibility state
  const [showImage, setShowImage] = useState(true);
  const [showCostmap, setShowCostmap] = useState(true);
  const [showRoute, setShowRoute] = useState(true);
  const [showGridLines, setShowGridLines] = useState(true);
  const [overlayOpacity, setOverlayOpacity] = useState(0.6);
  const [selectionError, setSelectionError] = useState<string | null>(null);

  // Zoom & Pan state
  const [zoomLevel, setZoomLevel] = useState(1);
  const [panOffset, setPanOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });

  // Hovered cell tooltip inspection state
  const [hoveredCell, setHoveredCell] = useState<{
    r: number;
    c: number;
    x: number;
    y: number;
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);

  const { segmentation, costmap, path_result, metadata } = analysis;
  const rows = segmentation.grid_height;
  const cols = segmentation.grid_width;
  const path = path_result?.is_success ? path_result.path : [];
  const pathSet = new Set(path.map(([r, c]) => `${r},${c}`));

  // Zoom controls
  const handleZoomIn = () => setZoomLevel((z) => Math.min(3, +(z + 0.25).toFixed(2)));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(1, +(z - 0.25).toFixed(2)));
  const handleResetView = () => {
    setZoomLevel(1);
    setPanOffset({ x: 0, y: 0 });
  };

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button === 1 || (e.button === 0 && e.altKey)) {
      e.preventDefault();
      setIsPanning(true);
      setPanStart({ x: e.clientX - panOffset.x, y: e.clientY - panOffset.y });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isPanning) {
      setPanOffset({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y,
      });
    }
  };

  const handleMouseUp = () => setIsPanning(false);

  // Color generator for terrain classification
  const getCellVisual = (terrain: string, cost: number | null) => {
    if (cost === null || terrain === 'obstacle') {
      return {
        bg: 'rgba(239, 68, 68, 0.85)',
        label: 'Obstacle / Hazard',
        traversable: false,
        costStr: 'IMP (Blocked)',
      };
    }
    switch (terrain) {
      case 'clear':
        return {
          bg: 'rgba(16, 185, 129, 0.45)',
          label: 'Clear Bedrock',
          traversable: true,
          costStr: cost.toFixed(1),
        };
      case 'rocky':
        return {
          bg: 'rgba(245, 158, 11, 0.65)',
          label: 'Rocky Field',
          traversable: true,
          costStr: cost.toFixed(1),
        };
      case 'loose':
        return {
          bg: 'rgba(226, 88, 34, 0.75)',
          label: 'Loose Sand Drift',
          traversable: true,
          costStr: cost.toFixed(1),
        };
      case 'unknown':
        return {
          bg: 'rgba(148, 163, 184, 0.5)',
          label: 'Unknown / Precaution',
          traversable: true,
          costStr: cost.toFixed(1),
        };
      default:
        return {
          bg: 'rgba(100, 116, 139, 0.4)',
          label: terrain,
          traversable: true,
          costStr: cost.toFixed(1),
        };
    }
  };

  return (
    <div className="hud-panel corner-bracket mb-6">
      {/* Top Viewport Toolbar */}
      <div className="hud-panel-header flex flex-wrap items-center justify-between gap-3 bg-mars-950/80">
        {/* Left: Viewport Title & Mode Indicator */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <Crosshair className="w-4 h-4 text-mars-rust" />
            <h2 className="font-display font-bold text-sm tracking-wide text-white uppercase">
              Immersive Exploration Viewport
            </h2>
          </div>
          <span className="font-mono text-[11px] text-slate-400">
            Grid: <strong className="text-mars-sky">{cols}×{rows}</strong> ({cols * rows} cells)
          </span>
          {segmentation.is_synthetic && (
            <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-mars-amber/15 text-mars-amber border border-mars-amber/30 uppercase tracking-wider">
              Offline Synthetic Fixture
            </span>
          )}
        </div>

        {/* Center: Layer Switches & Opacity Slider */}
        <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
          {/* Opacity Control */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-mars-850 border border-mars-750">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-[11px] text-slate-400">Opacity:</span>
            <input
              type="range"
              min="0.1"
              max="1.0"
              step="0.05"
              value={overlayOpacity}
              onChange={(e) => setOverlayOpacity(parseFloat(e.target.value))}
              className="w-16 accent-mars-rust cursor-pointer h-1.5"
            />
            <span className="text-slate-200 text-[11px] w-7 text-right">
              {Math.round(overlayOpacity * 100)}%
            </span>
          </div>

          {/* Layer Buttons */}
          <button
            onClick={() => setShowImage(!showImage)}
            className={`px-2 py-1 rounded flex items-center gap-1 text-[11px] border transition-all ${
              showImage
                ? 'bg-mars-sky/15 text-mars-sky border-mars-sky/40'
                : 'bg-mars-850 text-slate-500 border-mars-800'
            }`}
          >
            <Eye className="w-3 h-3" />
            Optical Frame
          </button>

          <button
            onClick={() => setShowCostmap(!showCostmap)}
            className={`px-2 py-1 rounded flex items-center gap-1 text-[11px] border transition-all ${
              showCostmap
                ? 'bg-mars-rust/20 text-mars-rust border-mars-rust/50 font-semibold'
                : 'bg-mars-850 text-slate-500 border-mars-800'
            }`}
          >
            <Layers className="w-3 h-3" />
            Terrain Risk
          </button>

          <button
            onClick={() => setShowRoute(!showRoute)}
            className={`px-2 py-1 rounded flex items-center gap-1 text-[11px] border transition-all ${
              showRoute
                ? 'bg-mars-emerald/20 text-emerald-400 border-mars-emerald/50 font-semibold'
                : 'bg-mars-850 text-slate-500 border-mars-800'
            }`}
          >
            A* Route
          </button>

          <button
            onClick={() => setShowGridLines(!showGridLines)}
            className={`px-2 py-1 rounded flex items-center gap-1 text-[11px] border transition-all ${
              showGridLines
                ? 'bg-mars-800 text-slate-200 border-mars-700'
                : 'bg-mars-850 text-slate-500 border-mars-800'
            }`}
          >
            <GridIcon className="w-3 h-3" />
            Grid
          </button>
        </div>

        {/* Right: Zoom & Reset Controls */}
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleZoomIn}
            className="btn-ghost p-1.5 border border-mars-750"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-xs text-slate-400 w-9 text-center">
            {Math.round(zoomLevel * 100)}%
          </span>
          <button
            onClick={handleZoomOut}
            className="btn-ghost p-1.5 border border-mars-750"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleResetView}
            className="btn-ghost p-1.5 border border-mars-750"
            title="Reset Zoom & Pan"
          >
            <Maximize2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Interactive Selection Action Bar */}
      <div className="px-4 py-2.5 bg-mars-950 border-b border-mars-800 flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-slate-400 text-[11px] uppercase tracking-wider">
            Click Map to Place:
          </span>
          <button
            onClick={() => {
              setSelectionMode('start');
              setSelectionError(null);
            }}
            className={`px-3 py-1 rounded-full flex items-center gap-1.5 transition-all text-xs ${
              selectionMode === 'start'
                ? 'bg-mars-emerald/25 text-emerald-300 border border-mars-emerald font-semibold shadow-sm animate-pulse'
                : 'bg-mars-850 text-slate-400 hover:text-white border border-mars-750'
            }`}
          >
            <MapPin className="w-3.5 h-3.5 text-mars-emerald" />
            Rover Origin (S){startCoord ? ` [${startCoord[0]}, ${startCoord[1]}]` : ''}
          </button>

          <button
            onClick={() => {
              setSelectionMode('goal');
              setSelectionError(null);
            }}
            className={`px-3 py-1 rounded-full flex items-center gap-1.5 transition-all text-xs ${
              selectionMode === 'goal'
                ? 'bg-mars-amber/25 text-amber-300 border border-mars-amber font-semibold shadow-sm animate-pulse'
                : 'bg-mars-850 text-slate-400 hover:text-white border border-mars-750'
            }`}
          >
            <Flag className="w-3.5 h-3.5 text-mars-amber" />
            Destination (G){goalCoord ? ` [${goalCoord[0]}, ${goalCoord[1]}]` : ''}
          </button>

          {onRecalculatePath && (
            <button
              onClick={() => {
                setSelectionError(null);
                onRecalculatePath();
              }}
              disabled={isPlanning || !startCoord || !goalCoord}
              className="px-3 py-1 rounded bg-mars-emerald/20 hover:bg-mars-emerald/30 border border-emerald-500/50 text-emerald-300 text-xs font-semibold flex items-center gap-1.5 transition-all disabled:opacity-50 disabled:pointer-events-none shadow-sm"
              title="Solve A* lowest-cost path with updated start and goal coordinates"
            >
              {isPlanning ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Navigation className="w-3.5 h-3.5" />
              )}
              <span>{isPlanning ? 'Calculating...' : 'Replan Route (A*)'}</span>
            </button>
          )}

          {(startCoord || goalCoord) && (
            <button
              onClick={() => {
                setSelectionError(null);
                onResetPoints();
              }}
              className="text-[11px] text-slate-400 hover:text-mars-rust flex items-center gap-1 underline transition-colors"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          )}
        </div>

        <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
          <HelpCircle className="w-3.5 h-3.5 text-mars-sky" />
          <span>Click a cell to set {selectionMode === 'start' ? 'Rover Origin' : 'Destination'}. Alt+Drag to pan.</span>
        </div>
      </div>

      {/* Warning/Error Banner when user clicks blocked obstacle cell */}
      {selectionError && (
        <div className="px-4 py-2 bg-red-950/90 border-b border-red-500/50 text-red-200 text-xs font-mono flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0" />
            <span>{selectionError}</span>
          </div>
          <button
            onClick={() => setSelectionError(null)}
            className="text-red-400 hover:text-white underline text-[11px] ml-4"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Main Large Visual Viewport */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          handleMouseUp();
          setHoveredCell(null);
        }}
        className={`relative w-full overflow-hidden bg-black flex items-center justify-center select-none ${
          isPanning ? 'cursor-grabbing' : 'cursor-crosshair'
        }`}
        style={{ minHeight: '520px', maxHeight: '720px' }}
      >
        <div
          className="relative transition-transform duration-75 ease-out"
          style={{
            transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoomLevel})`,
            transformOrigin: 'center center',
            aspectRatio: `${metadata.width} / ${metadata.height}`,
            width: '100%',
            maxWidth: '1200px',
          }}
        >
          {/* Base Layer: Optical Rover Image */}
          {showImage && (
            <img
              src={getRawImageUrl(metadata.image_id)}
              alt="Mars Rover Camera Frame"
              className="w-full h-full object-contain pointer-events-none select-none block"
            />
          )}

          {/* Interactive Costmap & Terrain Overlay Grid */}
          <div
            className="absolute inset-0 grid"
            style={{
              gridTemplateRows: `repeat(${rows}, 1fr)`,
              gridTemplateColumns: `repeat(${cols}, 1fr)`,
            }}
          >
            {segmentation.terrain_grid.map((rowArr, r) =>
              rowArr.map((terrainLabel, c) => {
                const cost = costmap.cost_grid[r][c];
                const isStart = startCoord && startCoord[0] === r && startCoord[1] === c;
                const isGoal = goalCoord && goalCoord[0] === r && goalCoord[1] === c;
                const isPath = showRoute && pathSet.has(`${r},${c}`);
                const visual = getCellVisual(terrainLabel, cost);

                return (
                  <div
                    key={`${r}-${c}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (cost === null || terrainLabel === 'obstacle') {
                        setSelectionError(
                          `Cell [${r}, ${c}] is an impassable obstacle (${terrainLabel.toUpperCase()}). Rover locomotion cannot be initialized on or targeted at blocked hazard terrain.`
                        );
                        return;
                      }
                      setSelectionError(null);
                      onSelectCoord([r, c]);
                    }}
                    onMouseEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setHoveredCell({
                        r,
                        c,
                        x: rect.left + rect.width / 2,
                        y: rect.top,
                      });
                    }}
                    className={`relative flex items-center justify-center transition-all ${
                      showGridLines ? 'border-[0.5px] border-white/10' : ''
                    } hover:ring-2 hover:ring-white hover:z-20`}
                    style={{
                      backgroundColor: showCostmap ? visual.bg : 'transparent',
                      opacity: showCostmap ? overlayOpacity : 1,
                    }}
                  >
                    {/* A* Route Waypoint Marker */}
                    {isPath && !isStart && !isGoal && (
                      <div className="w-2.5 h-2.5 rounded-full bg-mars-sky shadow-[0_0_8px_#38bdf8] pointer-events-none z-10 animate-pulse" />
                    )}

                    {/* Start Marker (Green Rover Origin) */}
                    {isStart && (
                      <div
                        className="w-full h-full flex items-center justify-center bg-mars-emerald text-black font-mono font-bold text-[10px] z-20 shadow-[0_0_12px_#10b981] rounded-sm pointer-events-none"
                        title="Rover Origin (Start)"
                      >
                        S
                      </div>
                    )}

                    {/* Goal Marker (Amber Destination Flag) */}
                    {isGoal && (
                      <div
                        className="w-full h-full flex items-center justify-center bg-mars-amber text-black font-mono font-bold text-[10px] z-20 shadow-[0_0_12px_#f59e0b] rounded-sm pointer-events-none"
                        title="Target Destination (Goal)"
                      >
                        G
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Polished Hover HUD Tooltip (Smart Fixed Floating) */}
        {hoveredCell && (
          <div
            className="fixed pointer-events-none z-50 bg-mars-950/95 border border-mars-copper/80 rounded-md p-3 shadow-2xl backdrop-blur-md font-mono text-xs text-slate-200 transform -translate-x-1/2 -translate-y-full mb-3"
            style={{
              left: `${hoveredCell.x}px`,
              top: `${hoveredCell.y}px`,
              minWidth: '220px',
            }}
          >
            <div className="flex items-center justify-between pb-1.5 border-b border-mars-800 text-[11px]">
              <span className="text-mars-rust font-bold">
                GRID CELL [{hoveredCell.r}, {hoveredCell.c}]
              </span>
              {costmap.cost_grid[hoveredCell.r][hoveredCell.c] !== null ? (
                <span className="text-emerald-400 flex items-center gap-1 text-[10px]">
                  <CheckCircle2 className="w-3 h-3" />
                  Traversable
                </span>
              ) : (
                <span className="text-red-400 flex items-center gap-1 text-[10px]">
                  <AlertOctagon className="w-3 h-3" />
                  Hazard / Blocked
                </span>
              )}
            </div>

            <div className="mt-2 space-y-1 text-[11px]">
              <div className="flex justify-between">
                <span className="text-slate-400">Class:</span>
                <span className="text-mars-sky font-semibold uppercase">
                  {segmentation.terrain_grid[hoveredCell.r][hoveredCell.c]}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Traversal Cost:</span>
                <span className="text-mars-amber font-bold">
                  {costmap.cost_grid[hoveredCell.r][hoveredCell.c] !== null
                    ? `${costmap.cost_grid[hoveredCell.r][hoveredCell.c]}x`
                    : 'IMP (Infinite)'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Pixel Footprint:</span>
                <span className="text-slate-300">
                  X:[{Math.round(hoveredCell.c * metadata.width / cols)}..{Math.round((hoveredCell.c + 1) * metadata.width / cols)}] Y:[{Math.round(hoveredCell.r * metadata.height / rows)}..{Math.round((hoveredCell.r + 1) * metadata.height / rows)}]
                </span>
              </div>
              {pathSet.has(`${hoveredCell.r},${hoveredCell.c}`) && (
                <div className="flex justify-between pt-1 border-t border-mars-800 text-emerald-400 font-semibold">
                  <span>A* Route Status:</span>
                  <span>
                    Waypoint #{path.findIndex(([pr, pc]) => pr === hoveredCell.r && pc === hoveredCell.c) + 1} of {path.length}
                  </span>
                </div>
              )}
              <div className="pt-1 border-t border-mars-800/60 text-[10px] text-slate-400">
                <span>Source: {segmentation.is_synthetic ? 'Synthetic Grid Pattern' : 'Meta SAM 3.1 Output'}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Unified Mission Terrain Legend */}
      <div className="px-5 py-3.5 bg-mars-950 border-t border-mars-800 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
        <div className="flex flex-wrap items-center gap-5">
          <span className="text-slate-400 font-semibold uppercase text-[11px] tracking-wider">
            Risk Legend:
          </span>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[rgba(16,185,129,0.85)] border border-emerald-400" />
            <span className="text-slate-200">Clear Bedrock (1.0x)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[rgba(245,158,11,0.85)] border border-amber-400" />
            <span className="text-slate-200">Rocky Terrain (3.0x)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[rgba(226,88,34,0.85)] border border-orange-500" />
            <span className="text-slate-200">Loose Sand Drift (5.0x)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[rgba(239,68,68,0.85)] border border-red-500" />
            <span className="text-slate-200">Obstacle (Impassable)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3.5 h-3.5 rounded-sm bg-[rgba(148,163,184,0.85)] border border-slate-400" />
            <span className="text-slate-200">Unknown / Precaution (2.0x)</span>
          </div>
        </div>

        <div className="text-[11px] text-slate-400">
          Navigation Path: <span className="text-mars-sky font-semibold">{path.length} Waypoints</span>
        </div>
      </div>
    </div>
  );
};
