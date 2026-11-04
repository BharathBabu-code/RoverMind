import React, { useState, useEffect } from 'react';
import { Sparkles, ArrowRight, ShieldCheck, Orbit, RefreshCw, X } from 'lucide-react';

interface MarsFact {
  id: number;
  category: string;
  topic: string;
  fact: string;
  source: string;
}

const VERIFIED_MARS_FACTS: MarsFact[] = [
  {
    id: 1,
    category: 'PLANETARY GEOLOGY',
    topic: 'Olympus Mons Volcano',
    fact: 'Olympus Mons towers 21.9 km (72,000 ft) above the Martian datum—nearly 2.5 times the height of Mount Everest. Its caldera is 80 km across, large enough to engulf Greater London or Los Angeles.',
    source: 'NASA Mars Global Surveyor (MOLA) Science Data',
  },
  {
    id: 2,
    category: 'PLANETARY DYNAMICS',
    topic: 'Martian Sol Duration',
    fact: 'A Martian solar day (sol) lasts 24 hours, 39 minutes, and 35.244 seconds—just 2.7% longer than an Earth day. A Martian year spans 668.6 sols (687 Earth days).',
    source: 'NASA Jet Propulsion Laboratory (JPL) Planetary Constants',
  },
  {
    id: 3,
    category: 'ATMOSPHERIC OPTICS',
    topic: 'Martian Blue Sunsets',
    fact: 'Sunsets on Mars appear distinctly blue. Fine iron-rich dust particles in the thin atmosphere scatter red light across the sky while forward-scattering blue wavelengths directly toward the observer at twilight.',
    source: 'NASA Curiosity Mastcam Optical Scattering Science Archive',
  },
  {
    id: 4,
    category: 'ATMOSPHERIC DYNAMICS',
    topic: 'Surface Atmospheric Pressure',
    fact: 'Mars has an atmospheric surface pressure averaging 610 Pascals (6.1 millibars)—less than 1% of Earth’s sea-level pressure. It consists of 95.3% Carbon Dioxide ($CO_2$), 2.6% Nitrogen ($N_2$), and 1.9% Argon ($Ar$).',
    source: 'Viking Lander & Mars Science Laboratory Barometric Telemetry',
  },
  {
    id: 5,
    category: 'ROVER TRAVERSE',
    topic: 'Curiosity Odometer Milestone',
    fact: 'Since landing in August 2012, NASA’s Curiosity rover has climbed Mount Sharp and traversed over 32 kilometers (20 miles) across Gale Crater, enduring wheel punctures from sharp ventifact rocks.',
    source: 'NASA JPL MSL Mission Status & Traverse Telemetry',
  },
  {
    id: 6,
    category: 'PALEOLAKES & ASTROBIOLOGY',
    topic: 'Jezero Crater Delta',
    fact: 'Around 3.7 billion years ago, Jezero Crater held an open-basin lake 250 meters deep. The fan-shaped delta preserved fine-grained smectite and carbonate mudstones that can trap ancient biosignatures.',
    source: 'Perseverance Science Team / Nature Astronomy Reports',
  },
  {
    id: 7,
    category: 'IN-SITU RESOURCE UTILIZATION',
    topic: 'MOXIE Oxygen Production',
    fact: 'Perseverance’s MOXIE experiment proved that humans can generate breathable oxygen on Mars by using solid oxide electrolysis to split atmospheric $CO_2$ into pure $O_2$ and carbon monoxide.',
    source: 'MIT & NASA Space Technology Mission Directorate (STMD)',
  },
  {
    id: 8,
    category: 'TECTONIC LANDSCAPES',
    topic: 'Valles Marineris Grand Canyon',
    fact: 'Valles Marineris is the grandest canyon system in the Solar System, spanning 4,000 km across—wide enough to cross the continental United States—and descending down to 7 km in depth.',
    source: 'ESA Mars Express HRSC Topographic Imaging Survey',
  },
  {
    id: 9,
    category: 'SURFACE GRAVITY',
    topic: 'Martian Gravity Physics',
    fact: 'Mars surface gravity is 3.72 m/s² (~38% of Earth’s gravity). A 1,025 kg rover like Perseverance weighs only 389 kgf on Martian regolith, reducing wheel soil shear stresses.',
    source: 'NASA Planetary Data System (PDS) Geodesy Data',
  },
  {
    id: 10,
    category: 'ORBITAL MECHANICS',
    topic: 'Phobos Inward Orbital Decay',
    fact: 'Mars’ moon Phobos orbits just 6,000 km above the surface and completes an orbit in only 7 hours 39 minutes. Tidal deceleration pulls it inward by ~2 meters per century; it will crash or shred into a ring in 30–50 million years.',
    source: 'ESA Mars Express Radio Science Experiment (MaRS)',
  },
  {
    id: 11,
    category: 'INTERPLANETARY COMMUNICATIONS',
    topic: 'Radio Signal Latency',
    fact: 'Because the Earth-Mars orbital distance varies between 54.6 million km and 401 million km, radio commands travel between 3.1 and 22.3 minutes one-way at the speed of light, making real-time joystick driving impossible.',
    source: 'NASA Deep Space Network (DSN) Telemetry Records',
  },
  {
    id: 12,
    category: 'CRYOSPHERE & HYDROLOGY',
    topic: 'Vast Subsurface Glaciers',
    fact: 'Radar sounders (SHARAD on MRO and MARSIS on Mars Express) have mapped massive glaciers containing billions of metric tons of water ice hidden beneath insulating dust blankets across mid-latitudes.',
    source: 'NASA Mars Reconnaissance Orbiter (MRO) Science Bulletin',
  },
  {
    id: 13,
    category: 'AERIAL EXPLORATION',
    topic: 'Ingenuity Rotorcraft Triumph',
    fact: 'Designed as a 5-flight tech demo in Mars’ thin atmosphere (equivalent to Earth’s stratosphere at 100,000 ft), the Ingenuity helicopter completed 72 flights and covered 17.0 km of terrain scouting for Perseverance.',
    source: 'NASA JPL Mars 2020 Aerial Mobility Engineering Team',
  },
  {
    id: 14,
    category: 'ACOUSTIC PROPAGATION',
    topic: 'Speed of Sound on Mars',
    fact: 'Sound travels at ~240 m/s on Mars compared to 340 m/s on Earth due to cold temperature and low density. High-frequency sounds attenuate in meters, creating an eerie, deep-toned acoustic environment.',
    source: 'SuperCam Microphone Experiment / Nature Communications 2022',
  },
  {
    id: 15,
    category: 'ROVER MOBILITY ENGINEERING',
    topic: 'Curved Titanium Wheel Spokes',
    fact: 'Perseverance features machined aluminum wheels with curved titanium spokes that act as leaf springs, absorbing mechanical shock when traversing sharp basalt rocks and volcanic caprocks.',
    source: 'NASA JPL Mobility and Robotic Systems Forum',
  },
  {
    id: 16,
    category: 'SURFACE ENVIRONMENT',
    topic: 'Extreme Thermal Swings',
    fact: 'Surface temperatures at the Martian equator swing from a daytime high of +20°C (68°F) to an overnight plunge of -73°C (-100°F). At the winter poles, temperatures drop below -125°C, freezing $CO_2$ into dry ice.',
    source: 'Mars Environmental Dynamics Analyzer (MEDA) Instrument Data',
  },
];

interface MarsFactTickerProps {
  isLoading: boolean;
  statusLabel?: string;
}

export const MarsFactTicker: React.FC<MarsFactTickerProps> = ({
  isLoading,
  statusLabel = 'Analyzing Optical Frame...',
}) => {
  const [factIndex, setFactIndex] = useState(() => Math.floor(Math.random() * VERIFIED_MARS_FACTS.length));
  const [progress, setProgress] = useState(0);
  const [isDismissed, setIsDismissed] = useState(false);

  // When isLoading turns true, reset dismissal, pick a fresh random fact, and start 10s progress cycle
  useEffect(() => {
    if (!isLoading) {
      setProgress(0);
      return;
    }

    setIsDismissed(false);
    setFactIndex(Math.floor(Math.random() * VERIFIED_MARS_FACTS.length));
    setProgress(0);

    const DURATION_MS = 10000; // 10 seconds per fact
    const STEP_MS = 100;
    let elapsed = 0;

    const interval = window.setInterval(() => {
      elapsed += STEP_MS;
      const pct = Math.min(100, (elapsed / DURATION_MS) * 100);
      setProgress(pct);

      if (elapsed >= DURATION_MS) {
        elapsed = 0;
        setProgress(0);
        setFactIndex((prev) => (prev + 1) % VERIFIED_MARS_FACTS.length);
      }
    }, STEP_MS);

    return () => window.clearInterval(interval);
  }, [isLoading]);

  if (!isLoading || isDismissed) return null;

  const currentFact = VERIFIED_MARS_FACTS[factIndex];

  const handleNextFact = (e: React.MouseEvent) => {
    e.stopPropagation();
    setProgress(0);
    setFactIndex((prev) => (prev + 1) % VERIFIED_MARS_FACTS.length);
  };

  return (
    <div className="fixed bottom-6 right-6 z-[9999] max-w-lg w-[calc(100vw-3rem)] pointer-events-auto animate-fadeIn shadow-2xl">
      <div className="hud-panel corner-bracket border-mars-600 bg-mars-950/95 backdrop-blur-lg p-4 text-slate-200 border-2 shadow-[0_0_30px_rgba(234,88,12,0.25)]">
        {/* Animated Cycle Progress Bar */}
        <div className="w-full bg-mars-900 h-1 rounded-full overflow-hidden mb-3">
          <div
            className="bg-gradient-to-r from-mars-rust via-mars-amber to-orange-400 h-full transition-all duration-100 ease-linear"
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Top Header Row */}
        <div className="flex items-center justify-between pb-2 mb-2 border-b border-mars-800 text-[11px] font-mono">
          <div className="flex items-center gap-2 text-mars-amber font-semibold tracking-wider uppercase">
            <RefreshCw className="w-3.5 h-3.5 animate-spin text-mars-glow" />
            <span>{statusLabel}</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded bg-mars-900 border border-mars-750 text-[10px] text-slate-300 uppercase tracking-widest flex items-center gap-1">
              <Orbit className="w-3 h-3 text-mars-copper" />
              {currentFact.category}
            </span>
            <button
              onClick={() => setIsDismissed(true)}
              className="p-1 rounded hover:bg-mars-800 text-slate-400 hover:text-white transition-colors"
              title="Dismiss Mars facts"
              aria-label="Dismiss Mars facts"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Fact Title & Content */}
        <div className="space-y-1.5 py-1">
          <div className="flex items-center justify-between">
            <h4 className="font-display font-bold text-xs uppercase tracking-wide text-white flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-mars-amber" />
              {currentFact.topic}
            </h4>
            <span className="text-[10px] font-mono text-slate-400">
              Sol Facts #{currentFact.id} of {VERIFIED_MARS_FACTS.length}
            </span>
          </div>

          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            {currentFact.fact}
          </p>
        </div>

        {/* Footer Verification Citation & Controls */}
        <div className="mt-3 pt-2 border-t border-mars-850 flex items-center justify-between text-[10px] font-mono text-slate-400">
          <div className="flex items-center gap-1 text-slate-400 truncate max-w-[240px]">
            <ShieldCheck className="w-3 h-3 text-emerald-400 flex-shrink-0" />
            <span className="truncate">Source: {currentFact.source}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsDismissed(true)}
              className="text-slate-500 hover:text-slate-300 px-2 py-1 rounded hover:bg-mars-900 border border-transparent hover:border-mars-800 transition-colors"
            >
              Dismiss
            </button>
            <button
              onClick={handleNextFact}
              className="text-mars-copper hover:text-white flex items-center gap-1 px-2 py-1 rounded bg-mars-900 hover:bg-mars-850 border border-mars-800 transition-colors"
            >
              <span>Next Fact</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
