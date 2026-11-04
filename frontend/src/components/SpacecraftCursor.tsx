import React, { useEffect, useRef } from 'react';

/**
 * SpacecraftCursor
 * Renders an animated Mars exploration drone/craft that follows the user's cursor
 * using requestAnimationFrame and linear interpolation (lerp).
 * 
 * Features:
 * - pointer-events: none (zero obstruction to underlying elements)
 * - Directly updates element style via refs to avoid React re-renders
 * - Angle orientation towards heading vector
 * - Subtle ion thruster glow
 * - Disabled on coarse touch pointers and prefers-reduced-motion
 */
export const SpacecraftCursor: React.FC = () => {
  const craftRef = useRef<HTMLDivElement>(null);
  const thrusterRef = useRef<SVGCircleElement>(null);

  useEffect(() => {
    // Check for touch device or reduced motion preferences
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const isTouch = window.matchMedia('(pointer: coarse)').matches;

    if (prefersReducedMotion || isTouch) {
      return;
    }

    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let currentX = mouseX;
    let currentY = mouseY;
    let currentAngle = 0;
    let isVisible = false;
    let animationFrameId: number;

    const handleMouseMove = (e: MouseEvent) => {
      mouseX = e.clientX;
      mouseY = e.clientY;
      if (!isVisible) {
        isVisible = true;
        currentX = mouseX;
        currentY = mouseY;
      }
    };

    const handleMouseLeave = () => {
      isVisible = false;
      if (craftRef.current) {
        craftRef.current.style.opacity = '0';
      }
    };

    const handleMouseEnter = () => {
      isVisible = true;
      if (craftRef.current) {
        craftRef.current.style.opacity = '1';
      }
    };

    window.addEventListener('mousemove', handleMouseMove, { passive: true });
    document.addEventListener('mouseleave', handleMouseLeave);
    document.addEventListener('mouseenter', handleMouseEnter);

    const LERP_FACTOR = 0.085; // Smooth trailing delay

    let tick = 0;
    const animate = () => {
      tick++;

      // Interpolate position
      const dx = mouseX - currentX;
      const dy = mouseY - currentY;
      
      currentX += dx * LERP_FACTOR;
      currentY += dy * LERP_FACTOR;

      // Calculate heading angle if moving sufficiently
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist > 1.2) {
        const targetAngle = Math.atan2(dy, dx) * (180 / Math.PI) + 90; // Align nose forward
        // Smooth angle interpolation
        let angleDiff = targetAngle - currentAngle;
        while (angleDiff > 180) angleDiff -= 360;
        while (angleDiff < -180) angleDiff += 360;
        currentAngle += angleDiff * 0.12;
      }

      // Subtle propulsion pulsation
      const thrusterIntensity = 0.6 + 0.4 * Math.sin(tick * 0.15) + Math.min(0.5, dist * 0.02);

      if (craftRef.current && isVisible) {
        craftRef.current.style.transform = `translate3d(${currentX - 18}px, ${currentY - 18}px, 0) rotate(${currentAngle}deg)`;
        craftRef.current.style.opacity = '1';
        // Dynamically update ambient cursor lighting coordinates
        document.documentElement.style.setProperty('--cursor-x', `${currentX.toFixed(1)}px`);
        document.documentElement.style.setProperty('--cursor-y', `${currentY.toFixed(1)}px`);
      }

      if (thrusterRef.current) {
        thrusterRef.current.setAttribute('opacity', thrusterIntensity.toFixed(2));
      }

      animationFrameId = requestAnimationFrame(animate);
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseleave', handleMouseLeave);
      document.removeEventListener('mouseenter', handleMouseEnter);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return (
    <div
      ref={craftRef}
      className="spacecraft-follower"
      style={{
        width: 36,
        height: 36,
        opacity: 0,
        transition: 'opacity 0.25s ease',
      }}
      aria-hidden="true"
    >
      <svg
        viewBox="0 0 36 36"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: '100%' }}
      >
        {/* Ion Propulsion Flame */}
        <circle
          ref={thrusterRef}
          cx="18"
          cy="31"
          r="4"
          fill="#ff8533"
          filter="blur(1.5px)"
        />
        <circle cx="18" cy="30" r="2" fill="#fff" opacity="0.8" />

        {/* Spacecraft Body - Sleek Orbital Scout Vessel */}
        <path
          d="M18 4L26 22L18 26L10 22L18 4Z"
          fill="#1c2433"
          stroke="#e25822"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />

        {/* Solar / Sensor Fins */}
        <path
          d="M10 18L4 25L10 23Z"
          fill="#253247"
          stroke="#e25822"
          strokeWidth="1"
        />
        <path
          d="M26 18L32 25L26 23Z"
          fill="#253247"
          stroke="#e25822"
          strokeWidth="1"
        />

        {/* Central Cockpit / Optical Sensor */}
        <circle cx="18" cy="14" r="2.5" fill="#38bdf8" />
        <circle cx="18" cy="14" r="1" fill="#ffffff" />
      </svg>
    </div>
  );
};
