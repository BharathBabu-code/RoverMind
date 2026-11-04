import React from 'react';
import { X, BookOpen, Layers, Cpu, Route, ShieldAlert, ArrowRight } from 'lucide-react';

interface MethodologyModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const MethodologyModal: React.FC<MethodologyModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="hud-card max-w-3xl w-full max-h-[90vh] flex flex-col my-auto border border-[#38bdf8]/40 shadow-2xl shadow-[#38bdf8]/10">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#242e42] bg-[#141a26]">
          <div className="flex items-center gap-2.5">
            <BookOpen className="w-5 h-5 text-[#38bdf8]" />
            <h3 className="font-display font-bold text-lg text-white">
              RoverMind Methodology & Architecture
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#94a3b8] hover:text-white p-1 rounded-md hover:bg-[#1e2638] transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm text-[#cbd5e1] leading-relaxed">
          {/* Section 1: Overview */}
          <div className="space-y-2">
            <h4 className="font-display font-semibold text-base text-[#e25822] flex items-center gap-2">
              <Layers className="w-4 h-4" />
              1. Architectural Pipeline
            </h4>
            <p className="text-xs text-[#94a3b8]">
              RoverMind is a computational decision-support platform designed for planetary exploration.
              The application translates raw optical camera frames into traversable terrain cost representations
              and computes lower-cost paths using an exact custom A* algorithm.
            </p>
            <div className="p-3 bg-[#0a0d13] rounded border border-[#1f2838] text-[11px] font-mono text-[#38bdf8] flex items-center justify-between flex-wrap gap-2">
              <span>Monocular Image</span>
              <ArrowRight className="w-3 h-3 text-[#64748b]" />
              <span>SAM 3.1 Segmentation</span>
              <ArrowRight className="w-3 h-3 text-[#64748b]" />
              <span>Mask Decoding</span>
              <ArrowRight className="w-3 h-3 text-[#64748b]" />
              <span>Terrain Costmap</span>
              <ArrowRight className="w-3 h-3 text-[#64748b]" />
              <span>Custom A* Path</span>
            </div>
          </div>

          {/* Section 2: SAM 3.1 & Mask Parsing */}
          <div className="space-y-2">
            <h4 className="font-display font-semibold text-base text-[#38bdf8] flex items-center gap-2">
              <Cpu className="w-4 h-4" />
              2. Meta SAM 3.1 Visual Segmentation & Decoding
            </h4>
            <p className="text-xs text-[#94a3b8]">
              The model segmentations are queried via Meta's OpenAI-compatible responses API endpoint.
              The streamed special-token grammar is consumed and decoded using the verified <code>meta-sam-parser</code> package:
            </p>
            <ul className="list-disc pl-5 space-y-1 text-xs text-[#94a3b8]">
              <li>Short noun phrases (e.g. <code>rock</code>, <code>loose sand</code>, <code>obstacle</code>) prompt the concept segmenter.</li>
              <li>Mask payloads are decoded into strict binary 1-byte-per-pixel rasters.</li>
              <li>Spatial coordinates are registered using half-open media bounds and projected onto the downsampled spatial grid.</li>
              <li>Overlapping masks are deterministically arbitrated using safety priority rules (Obstacles &gt; Rocks &gt; Loose Sand &gt; Clear).</li>
            </ul>
          </div>

          {/* Section 3: Costmap & A* Planning */}
          <div className="space-y-2">
            <h4 className="font-display font-semibold text-base text-[#10b981] flex items-center gap-2">
              <Route className="w-4 h-4" />
              3. Terrain Costmap & Custom A* Pathfinding
            </h4>
            <p className="text-xs text-[#94a3b8]">
              Normalized terrain labels are converted into numerical traversal costs:
            </p>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
              <div className="p-2 rounded bg-[#10b981]/10 border border-[#10b981]/30 text-[#34d399]">
                Clear Ground: 1.0
              </div>
              <div className="p-2 rounded bg-[#f59e0b]/10 border border-[#f59e0b]/30 text-[#fbbf24]">
                Rocky Field: 3.0
              </div>
              <div className="p-2 rounded bg-[#e25822]/10 border border-[#e25822]/30 text-[#ff8533]">
                Loose Sand: 5.0
              </div>
              <div className="p-2 rounded bg-[#ef4444]/10 border border-[#ef4444]/30 text-[#f87171]">
                Obstacle: Impassable
              </div>
            </div>
            <p className="text-xs text-[#94a3b8] mt-2">
              The custom A* planner uses admissible heuristics (Manhattan for 4-way, Octile for 8-way diagonal).
              It strictly forbids diagonal corner-cutting past impassable cells and resolves ties deterministically.
            </p>
          </div>

          {/* Section 4: Scientific Honesty */}
          <div className="p-4 rounded bg-[#ef4444]/10 border border-[#ef4444]/30 space-y-2">
            <h4 className="font-display font-semibold text-xs text-[#fca5a5] flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-[#ef4444]" />
              Scientific Honesty & Engineering Limitations
            </h4>
            <p className="text-xs text-[#94a3b8] leading-relaxed">
              A single 2D camera image cannot provide true physical depth, slope angle, sub-surface mechanical compaction, or slip coefficients.
              RoverMind results must always be characterized as <strong>image-derived visual estimations</strong> and 
              <strong> computed lowest-cost paths</strong>, never as physically certified navigation clearances.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-[#242e42] bg-[#141a26] flex justify-end">
          <button onClick={onClose} className="btn-secondary text-xs">
            Close Reference
          </button>
        </div>
      </div>
    </div>
  );
};
