import React from 'react';

interface RocketHeroGraphicProps {
  className?: string;
  launchProgress?: number; // 0.0 (launch pad pre-launch) to 1.0 (deep space ascent)
}

export const RocketHeroGraphic: React.FC<RocketHeroGraphicProps> = ({
  className = '',
  launchProgress = 0,
}) => {
  // Clamp progress between 0.0 and 1.0
  const progress = Math.max(0, Math.min(1, launchProgress));

  // ---------------------------------------------------------------------------
  // MULTI-STAGE DYNAMIC KINEMATICS & INTENSITIES
  // ---------------------------------------------------------------------------
  // Stage 1: Pre-launch venting (0.00 -> 0.12)
  const ventingOpacity = progress < 0.25 ? Math.max(0.1, 1 - progress * 4) : 0;

  // Stage 2: Umbilical Arm Swing Retraction (0.06 -> 0.22)
  const armRetraction = Math.min(1, Math.max(0, (progress - 0.06) / 0.16));
  const leftArmAngle = -armRetraction * 36;
  const rightArmAngle = armRetraction * 36;

  // Stage 2/3: Ignition & Supersonic Engine Thrust (0.08 -> 0.35)
  const ignitionProgress = Math.min(1, Math.max(0, (progress - 0.08) / 0.22));
  const isIgnited = progress >= 0.08;
  const flameScaleY = isIgnited ? 0.3 + ignitionProgress * 0.7 : 0;
  const flameOpacity = isIgnited ? Math.min(1, 0.4 + ignitionProgress * 0.6) : 0;

  // Stage 3: Liftoff Vertical Translation (non-linear easing t^1.8)
  const liftoffProgress = Math.max(0, (progress - 0.22) / 0.55);
  const rocketTranslationY = -Math.pow(liftoffProgress, 1.8) * 360;

  // Stage 3/4: Deluge Ground Smoke & Dust Billow (0.12 -> 0.85)
  const smokeActive = progress >= 0.10 && progress <= 0.95;
  const smokeProgress = Math.min(1, Math.max(0, (progress - 0.10) / 0.30));
  const smokeDissipate = progress > 0.70 ? Math.max(0, 1 - (progress - 0.70) / 0.25) : 1;
  const smokeOpacity = smokeActive ? smokeProgress * smokeDissipate * 0.85 : 0;
  const smokeSpread = smokeProgress * 55;

  // Exhaust ground light spill intensity
  const lightSpillOpacity = isIgnited ? Math.min(0.9, ignitionProgress * smokeDissipate * 0.8) : 0;

  return (
    <div className={`relative flex items-center justify-center select-none pointer-events-none ${className}`}>
      <svg
        viewBox="0 0 440 840"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full max-w-[500px] max-h-[900px] overflow-visible drop-shadow-[0_0_60px_rgba(249,115,22,0.20)]"
      >
        <defs>
          {/* Hull Shading Gradients */}
          <linearGradient id="hullBoosterGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0f172a" />
            <stop offset="25%" stopColor="#334155" />
            <stop offset="50%" stopColor="#64748b" />
            <stop offset="75%" stopColor="#334155" />
            <stop offset="100%" stopColor="#090d16" />
          </linearGradient>

          <linearGradient id="fairingGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="40%" stopColor="#94a3b8" />
            <stop offset="55%" stopColor="#f8fafc" />
            <stop offset="80%" stopColor="#475569" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>

          <linearGradient id="copperAccentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#7c2d12" />
            <stop offset="50%" stopColor="#ea580c" />
            <stop offset="100%" stopColor="#431407" />
          </linearGradient>

          <linearGradient id="gantrySteelGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#1e293b" />
            <stop offset="50%" stopColor="#334155" />
            <stop offset="100%" stopColor="#0f172a" />
          </linearGradient>

          {/* Supersonic Exhaust Plume Plasma Gradient */}
          <linearGradient id="supersonicPlumeGrad" x1="50%" y1="0%" x2="50%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="1" />
            <stop offset="10%" stopColor="#38bdf8" stopOpacity="0.95" />
            <stop offset="28%" stopColor="#0284c7" stopOpacity="0.9" />
            <stop offset="60%" stopColor="#f97316" stopOpacity="0.85" />
            <stop offset="85%" stopColor="#dc2626" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#7c2d12" stopOpacity="0" />
          </linearGradient>

          {/* Mach Shock Diamonds Diamond Pattern */}
          <linearGradient id="shockDiamondGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffffff" />
            <stop offset="50%" stopColor="#e0f2fe" />
            <stop offset="100%" stopColor="#38bdf8" />
          </linearGradient>

          {/* Atmospheric Deluge Ground Light Spill */}
          <radialGradient id="launchPadLightSpill" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#fb923c" stopOpacity="0.9" />
            <stop offset="40%" stopColor="#ea580c" stopOpacity="0.5" />
            <stop offset="70%" stopColor="#0284c7" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#000000" stopOpacity="0" />
          </radialGradient>

          {/* Volumetric Smoke Cloud Gradient */}
          <radialGradient id="smokeCloudGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#cbd5e1" stopOpacity="0.75" />
            <stop offset="45%" stopColor="#94a3b8" stopOpacity="0.45" />
            <stop offset="75%" stopColor="#475569" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#0f172a" stopOpacity="0" />
          </radialGradient>

          {/* Cryo Boil-off Venting Vapor */}
          <linearGradient id="cryoVentingGrad" x1="0%" y1="50%" x2="100%" y2="50%">
            <stop offset="0%" stopColor="#ffffff" stopOpacity="0" />
            <stop offset="50%" stopColor="#e2e8f0" stopOpacity="0.6" />
            <stop offset="100%" stopColor="#94a3b8" stopOpacity="0" />
          </linearGradient>
        </defs>

        {/* =========================================================================
            LAYER 1: GROUND LAUNCH PAD, GANTRY TOWER & RETRACTABLE SUPPORT ARMS
            ========================================================================= */}
        <g id="launch-pad-structure">
          {/* Ground Surface Foundation & Flame Trench Deflector */}
          <polygon points="40,820 400,820 420,838 20,838" fill="#090d16" stroke="#1e293b" strokeWidth="1.5" />
          <polygon points="120,820 320,820 280,838 160,838" fill="#030712" />

          {/* Heavy Concrete Blast Deflector Trench Wedge */}
          <polygon points="190,820 220,775 250,820" fill="#0f172a" stroke="#334155" strokeWidth="1.5" />

          {/* Strongback Vertical Gantry Tower (Port Side) */}
          <g id="strongback-tower">
            <rect x="70" y="240" width="36" height="580" fill="url(#gantrySteelGrad)" stroke="#1e293b" strokeWidth="1.5" />
            {/* Lattice Truss Cross-Braces */}
            {Array.from({ length: 12 }).map((_, i) => {
              const y = 250 + i * 46;
              return (
                <g key={i}>
                  <line x1="70" y1={y} x2="106" y2={y + 46} stroke="#475569" strokeWidth="1.2" opacity="0.7" />
                  <line x1="106" y1={y} x2="70" y2={y + 46} stroke="#475569" strokeWidth="1.2" opacity="0.7" />
                  <line x1="70" y1={y} x2="106" y2={y} stroke="#334155" strokeWidth="1.5" />
                </g>
              );
            })}
            {/* Tower Aviation Warning Beacon */}
            <circle cx="78" cy="236" r="3.5" fill="#ef4444" className="animate-ping" />
            <circle cx="78" cy="236" r="3" fill="#ef4444" />
          </g>

          {/* Retractable Umbilical Arm 1 (Upper Stage Umbilical at y=320) */}
          <g
            id="upper-umbilical-arm"
            style={{
              transformOrigin: '106px 320px',
              transform: `rotate(${leftArmAngle}deg)`,
              transition: 'transform 0.15s ease-out',
            }}
          >
            <rect x="106" y="316" width="84" height="8" rx="1" fill="#334155" stroke="#475569" strokeWidth="1" />
            <polygon points="186,314 196,320 186,326" fill="#ea580c" />
            {/* Electrical lines on arm */}
            <line x1="110" y1="320" x2="186" y2="320" stroke="#f97316" strokeWidth="1.5" strokeDasharray="3 2" />
          </g>

          {/* Retractable Umbilical Arm 2 (Booster Quick Disconnect at y=550) */}
          <g
            id="lower-umbilical-arm"
            style={{
              transformOrigin: '106px 550px',
              transform: `rotate(${leftArmAngle * 1.1}deg)`,
              transition: 'transform 0.15s ease-out',
            }}
          >
            <rect x="106" y="546" width="84" height="9" rx="1" fill="#334155" stroke="#475569" strokeWidth="1" />
            <polygon points="186,544 196,550 186,557" fill="#ea580c" />
            <line x1="110" y1="550" x2="186" y2="550" stroke="#38bdf8" strokeWidth="1.5" strokeDasharray="4 2" />
          </g>

          {/* Starboard Hold-Down Clamp Stand */}
          <rect x="330" y="620" width="22" height="200" fill="url(#gantrySteelGrad)" stroke="#1e293b" strokeWidth="1.5" />
          <g
            id="starboard-clamp-arm"
            style={{
              transformOrigin: '330px 640px',
              transform: `rotate(${rightArmAngle}deg)`,
              transition: 'transform 0.15s ease-out',
            }}
          >
            <rect x="246" y="636" width="84" height="8" rx="1" fill="#334155" stroke="#475569" strokeWidth="1" />
            <polygon points="246,634 236,640 246,646" fill="#64748b" />
          </g>
        </g>

        {/* =========================================================================
            LAYER 2: ATMOSPHERIC IGNITION LIGHT SPILL ON DECK
            ========================================================================= */}
        {lightSpillOpacity > 0 && (
          <ellipse
            cx="220"
            cy="770"
            rx="160"
            ry="55"
            fill="url(#launchPadLightSpill)"
            opacity={lightSpillOpacity}
          />
        )}

        {/* =========================================================================
            LAYER 3: ASCENDING ROCKET VEHICLE (TRANSLATES VERTICALLY)
            ========================================================================= */}
        <g
          id="rocket-assembly"
          style={{
            transform: `translate3d(0px, ${rocketTranslationY}px, 0px)`,
            transition: 'transform 0.08s linear',
          }}
        >
          {/* Supersonic Exhaust Plume (Scales with Ignition & Thrust) */}
          {flameOpacity > 0 && (
            <g
              id="exhaust-plume"
              style={{
                transformOrigin: '220px 675px',
                transform: `scaleY(${flameScaleY})`,
                opacity: flameOpacity,
              }}
            >
              {/* Outer supersonic plasma expansion envelope */}
              <polygon
                points="198,675 242,675 285,860 220,910 155,860"
                fill="url(#supersonicPlumeGrad)"
              />

              {/* High-velocity cyan/white core */}
              <polygon
                points="208,675 232,675 250,810 220,845 190,810"
                fill="url(#supersonicPlumeGrad)"
                opacity="0.95"
              />

              {/* Mach Shock Diamonds (Supersonic Expansion Waves) */}
              <polygon points="220,705 228,716 220,727 212,716" fill="url(#shockDiamondGrad)" opacity="0.95" />
              <polygon points="220,745 230,758 220,771 210,758" fill="url(#shockDiamondGrad)" opacity="0.85" />
              <polygon points="220,790 231,804 220,818 209,804" fill="url(#shockDiamondGrad)" opacity="0.75" />
              <polygon points="220,838 230,852 220,866 210,852" fill="url(#shockDiamondGrad)" opacity="0.6" />

              {/* Supersonic boundary shear lines */}
              <line x1="202" y1="680" x2="165" y2="850" stroke="#f97316" strokeWidth="1" opacity="0.6" />
              <line x1="238" y1="680" x2="275" y2="850" stroke="#f97316" strokeWidth="1" opacity="0.6" />
            </g>
          )}

          {/* Stage 1 Aerodynamic Stabilizer Fins (Port & Starboard) */}
          <polygon
            points="188,605 125,685 138,702 188,660"
            fill="url(#copperAccentGrad)"
            stroke="#334155"
            strokeWidth="1.5"
          />
          <polygon
            points="252,605 315,685 302,702 252,660"
            fill="url(#copperAccentGrad)"
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* Stage 1 Core Booster Tank (Lower Main Stage) */}
          <rect
            x="188"
            y="440"
            width="64"
            height="230"
            rx="2"
            fill="url(#hullBoosterGrad)"
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* Booster Stringers & Stiffener Rings */}
          <line x1="188" y1="490" x2="252" y2="490" stroke="#1e293b" strokeWidth="1.5" />
          <line x1="188" y1="550" x2="252" y2="550" stroke="#1e293b" strokeWidth="1.5" />
          <line x1="188" y1="615" x2="252" y2="615" stroke="#1e293b" strokeWidth="1.5" />
          <line x1="220" y1="440" x2="220" y2="670" stroke="#475569" strokeWidth="0.8" strokeDasharray="4 3" />

          {/* Grid Fins for Atmospheric Re-entry Control */}
          <rect x="178" y="450" width="10" height="14" rx="1" fill="#1e293b" stroke="#64748b" strokeWidth="1" />
          <rect x="252" y="450" width="10" height="14" rx="1" fill="#1e293b" stroke="#64748b" strokeWidth="1" />

          {/* Interstage Lattice Adapter Section (Open Truss) */}
          <rect x="192" y="405" width="56" height="35" fill="#090d16" stroke="#475569" strokeWidth="1.5" />
          <line x1="192" y1="405" x2="248" y2="440" stroke="#64748b" strokeWidth="1.2" />
          <line x1="248" y1="405" x2="192" y2="440" stroke="#64748b" strokeWidth="1.2" />

          {/* Cryo Boil-off Venting Plume at Interstage */}
          {ventingOpacity > 0 && (
            <g id="cryo-venting" opacity={ventingOpacity}>
              <ellipse cx="178" cy="420" rx="22" ry="7" fill="url(#cryoVentingGrad)" />
              <ellipse cx="262" cy="420" rx="22" ry="7" fill="url(#cryoVentingGrad)" />
            </g>
          )}

          {/* Stage 2 Upper Stage (Avionics & Orbital Payload) */}
          <rect
            x="190"
            y="265"
            width="60"
            height="140"
            rx="1.5"
            fill="url(#hullBoosterGrad)"
            stroke="#334155"
            strokeWidth="1.5"
          />

          {/* RoverMind Mission Livery & Marking */}
          <rect x="206" y="325" width="28" height="10" rx="1" fill="#ea580c" />
          <text
            x="220"
            y="332"
            textAnchor="middle"
            fill="#ffffff"
            fontSize="6.5"
            fontFamily="monospace"
            fontWeight="bold"
            letterSpacing="1"
          >
            RM-26
          </text>

          {/* Reaction Control System (RCS) Pitch/Yaw Thruster Quads */}
          <circle cx="190" cy="285" r="2.5" fill="#f97316" />
          <circle cx="250" cy="285" r="2.5" fill="#f97316" />
          <circle cx="190" cy="455" r="2.5" fill="#f97316" />
          <circle cx="250" cy="455" r="2.5" fill="#f97316" />

          {/* Payload Fairing Nosecone (Aerodynamic Shielding) */}
          <path
            d="M 190 265 C 190 200 205 110 220 80 C 235 110 250 200 250 265 Z"
            fill="url(#fairingGrad)"
            stroke="#475569"
            strokeWidth="1.5"
          />

          {/* Fairing Thermal Tiles & Longitudinal Separation Seam */}
          <path d="M 198 200 Q 220 206 242 200" stroke="#94a3b8" strokeWidth="1" fill="none" />
          <line x1="220" y1="80" x2="220" y2="265" stroke="#94a3b8" strokeWidth="0.9" />

          {/* Main Aerospike / Supersonic Vacuum Nozzle Bell */}
          <path
            d="M 203 670 L 199 686 L 241 686 L 237 670 Z"
            fill="#1e293b"
            stroke="#94a3b8"
            strokeWidth="1.5"
          />
          <ellipse
            cx="220"
            cy="686"
            rx="21"
            ry="5"
            fill={isIgnited ? '#f97316' : '#0f172a'}
            stroke={isIgnited ? '#ffffff' : '#334155'}
            strokeWidth="1"
          />
        </g>

        {/* =========================================================================
            LAYER 4: VOLUMETRIC DELUGE GROUND SMOKE & DUST BILLOWS
            ========================================================================= */}
        {smokeOpacity > 0 && (
          <g id="ground-deluge-smoke" opacity={smokeOpacity}>
            {/* Left Rolling Steam/Dust Plume */}
            <circle cx={180 - smokeSpread} cy="780" r={45 + smokeSpread * 0.4} fill="url(#smokeCloudGrad)" />
            <circle cx={140 - smokeSpread * 1.3} cy="800" r={55 + smokeSpread * 0.5} fill="url(#smokeCloudGrad)" />
            <circle cx={110 - smokeSpread * 1.5} cy="820" r={60 + smokeSpread * 0.6} fill="url(#smokeCloudGrad)" />

            {/* Right Rolling Steam/Dust Plume */}
            <circle cx={260 + smokeSpread} cy="780" r={45 + smokeSpread * 0.4} fill="url(#smokeCloudGrad)" />
            <circle cx={300 + smokeSpread * 1.3} cy="800" r={55 + smokeSpread * 0.5} fill="url(#smokeCloudGrad)" />
            <circle cx={330 + smokeSpread * 1.5} cy="820" r={60 + smokeSpread * 0.6} fill="url(#smokeCloudGrad)" />

            {/* Center Deluge Vapor Core */}
            <ellipse cx="220" cy="805" rx={75 + smokeSpread} ry="35" fill="url(#smokeCloudGrad)" />
          </g>
        )}
      </svg>
    </div>
  );
};
