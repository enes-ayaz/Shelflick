"use client";

import React from "react";
import { Sparkles } from "lucide-react";

interface HoloOverlayProps {
  mouseX: number; // 0 to 100
  mouseY: number; // 0 to 100
  isHovered: boolean;
  className?: string;
}

export const HoloOverlay: React.FC<HoloOverlayProps> = ({
  mouseX,
  mouseY,
  isHovered,
  className = "",
}) => {
  // Angle calculated dynamically based on mouse position
  const angle = Math.round((mouseX + mouseY) * 1.8);

  return (
    <div
      className={`absolute inset-0 pointer-events-none rounded-xl overflow-hidden z-20 transition-opacity duration-300 ${
        isHovered ? "opacity-100" : "opacity-90"
      } ${className}`}
    >
      {/* 1. Iridescent Rainbow Holo Sheen (Screen Blend - never blocks the image) */}
      <div
        className="absolute inset-0 pointer-events-none transition-all duration-75"
        style={{
          mixBlendMode: "screen",
          background: `
            radial-gradient(
              circle at ${mouseX}% ${mouseY}%,
              rgba(255, 255, 255, 0.4) 0%,
              rgba(255, 130, 180, 0.25) 25%,
              rgba(100, 200, 255, 0.25) 50%,
              rgba(255, 215, 0, 0.2) 75%,
              transparent 100%
            ),
            repeating-linear-gradient(
              ${angle}deg,
              rgba(255, 90, 180, 0.12) 0px,
              rgba(60, 190, 255, 0.12) 15px,
              rgba(255, 220, 0, 0.12) 30px,
              rgba(50, 215, 120, 0.12) 45px,
              rgba(180, 90, 255, 0.12) 60px,
              transparent 75px
            )
          `,
          opacity: isHovered ? 0.95 : 0.7,
        }}
      />

      {/* 2. Prismatic Glitter Sparkle Texture (Overlay Blend) */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          mixBlendMode: "overlay",
          background: `linear-gradient(
            ${180 - angle}deg,
            rgba(255, 255, 255, 0.2) 0%,
            transparent 45%,
            rgba(255, 215, 0, 0.25) 60%,
            transparent 100%
          )`,
          opacity: 0.6,
        }}
      />

      {/* 3. Metallic Gold Border & Inner Glow */}
      <div className="absolute inset-0 rounded-xl border-2 border-amber-400/90 shadow-[0_0_15px_rgba(245,158,11,0.45)] pointer-events-none" />

      {/* 4. Top-Right Gold Hologram Star Badge */}
      <div className="absolute top-2 right-2 flex items-center justify-center w-5 h-5 rounded-full bg-gradient-to-tr from-amber-500 to-yellow-300 text-neutral-950 shadow-md">
        <Sparkles className="w-3 h-3 text-neutral-950 fill-neutral-950 animate-pulse" />
      </div>
    </div>
  );
};
