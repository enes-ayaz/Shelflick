"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Film, Tv, Sparkles, Star, Clapperboard, Calendar, Edit3, XCircle } from "lucide-react";
import { LibraryItemDTO, WatchStatus } from "@/types";
import { formatPosterUrl } from "@/services/api";
import { useSoundEffects } from "@/hooks/useSoundEffects";
import { HoloOverlay } from "./HoloOverlay";

interface BoxItemProps {
  item: LibraryItemDTO;
  onClick: (item: LibraryItemDTO) => void;
}

/**
 * Returns the CSS filter styling corresponding to the item's WatchStatus.
 */
function getStatusFilterClass(status: WatchStatus): string {
  switch (status) {
    case "COMPLETED":
      return ""; // Vibrant original poster
    case "WATCHING":
      return "grayscale contrast-125"; // Monochrome gray
    case "DROPPED":
      return "grayscale sepia hue-rotate-[315deg] saturate-[600%] brightness-75"; // Noir crimson tone
    case "PLAN_TO_WATCH":
      return "opacity-60 blur-[0.6px]"; // Soft frosted & semi-transparent
    default:
      return "";
  }
}

/**
 * Returns status indicator dot color and label.
 */
function getStatusBadge(status: WatchStatus): { label: string; color: string } {
  switch (status) {
    case "COMPLETED":
      return { label: "İzlendi", color: "bg-emerald-500" };
    case "WATCHING":
      return { label: "İzleniyor", color: "bg-blue-500" };
    case "DROPPED":
      return { label: "Bırakıldı", color: "bg-red-500" };
    case "PLAN_TO_WATCH":
      return { label: "İzlenecek", color: "bg-amber-400" };
    default:
      return { label: "Raf", color: "bg-neutral-500" };
  }
}

export const BoxItem: React.FC<BoxItemProps> = ({ item, onClick }) => {
  const { playHover } = useSoundEffects();
  const [isHovered, setIsHovered] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [isExpandedMobile, setIsExpandedMobile] = useState(false);
  const [mousePos, setMousePos] = useState({ x: 50, y: 50 });
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  // Collapse open box on mobile when tapping outside
  useEffect(() => {
    if (!isExpandedMobile) return;
    const handleOutsideTap = (e: MouseEvent | TouchEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setIsExpandedMobile(false);
      }
    };
    document.addEventListener("mousedown", handleOutsideTap);
    document.addEventListener("touchstart", handleOutsideTap);
    return () => {
      document.removeEventListener("mousedown", handleOutsideTap);
      document.removeEventListener("touchstart", handleOutsideTap);
    };
  }, [isExpandedMobile]);

  const isExpanded = isMobile ? isExpandedMobile : isHovered;

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!boxRef.current || isMobile) return;
    const rect = boxRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(100, ((e.clientX - rect.left) / rect.width) * 100));
    const y = Math.max(0, Math.min(100, ((e.clientY - rect.top) / rect.height) * 100));
    setMousePos({ x, y });
  };

  const handleCardClick = (e: React.MouseEvent) => {
    if (isMobile) {
      // On mobile (<768px): Tap toggles expansion between 85px and 280px
      if (!isExpandedMobile) {
        setIsExpandedMobile(true);
        playHover();
      } else {
        setIsExpandedMobile(false);
      }
    } else {
      // On desktop: click directly opens detail modal
      onClick(item);
    }
  };

  const statusFilterClass = getStatusFilterClass(item.status);
  const statusBadge = getStatusBadge(item.status);
  const posterUrl = formatPosterUrl(item.poster_url);
  const displayScore = item.user_score ? item.user_score.toFixed(1) : item.base_score ? item.base_score.toFixed(1) : "—";

  // Source icon
  const SourceIcon =
    item.source === "TMDB_MOVIE"
      ? Film
      : item.source === "TMDB_SERIES"
      ? Tv
      : Clapperboard;

  return (
    <motion.div
      ref={boxRef}
      layout
      transition={{
        type: "spring",
        stiffness: 320,
        damping: 26,
        mass: 0.8,
      }}
      onMouseEnter={() => {
        if (!isMobile) {
          setIsHovered(true);
          playHover();
        }
      }}
      onMouseLeave={() => {
        if (!isMobile) {
          setIsHovered(false);
          setMousePos({ x: 50, y: 50 });
        }
      }}
      onMouseMove={handleMouseMove}
      onClick={handleCardClick}
      className={`relative h-[340px] flex-shrink-0 cursor-pointer select-none rounded-xl overflow-hidden transition-all duration-300 group snap-start ${
        isExpanded
          ? "w-[280px] z-30 shadow-[0_20px_45px_rgba(0,0,0,0.85)] ring-1 ring-white/20"
          : "w-[85px] z-10 shadow-[0_8px_20px_rgba(0,0,0,0.6)] hover:z-20 border border-white/10"
      }`}
      style={{
        transformOrigin: "center left",
      }}
    >
      {/* 1. Underlying Poster Background with Status Filter */}
      <div className="absolute inset-0 w-full h-full bg-neutral-900 pointer-events-none">
        <img
          src={posterUrl}
          alt={item.title}
          loading="lazy"
          onError={(e) => {
            (e.currentTarget as HTMLImageElement).src =
              "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500";
          }}
          className={`w-full h-full object-cover transition-transform duration-500 ease-out ${statusFilterClass} ${
            isExpanded ? "scale-105" : "scale-100"
          }`}
        />
        {/* Subtle darkening tint for spine readability when collapsed */}
        <div
          className={`absolute inset-0 bg-gradient-to-b from-black/70 via-black/35 to-black/80 transition-opacity duration-300 pointer-events-none ${
            isExpanded ? "opacity-0" : "opacity-100"
          }`}
        />
      </div>

      {/* 2. Holographic Pokémon foil layer for Gold Box Favorites */}
      {item.is_favorite && (
        <HoloOverlay
          mouseX={mousePos.x}
          mouseY={mousePos.y}
          isHovered={isExpanded}
        />
      )}

      {/* 3. COLLAPSED SPINE VIEW (85px wide, NO ROTATED TEXT!) */}
      <AnimatePresence>
        {!isExpanded && (
          <motion.div
            key="spine-content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="absolute inset-0 p-2.5 flex flex-col justify-between items-center text-center z-10 pointer-events-none"
          >
            {/* Top Header: Source Icon & Score */}
            <div className="w-full flex flex-col items-center gap-1">
              <div className="w-7 h-7 rounded-lg bg-black/50 backdrop-blur-md border border-white/10 flex items-center justify-center text-neutral-300 shadow-sm">
                <SourceIcon className="w-3.5 h-3.5 text-indigo-400" />
              </div>
              <div className="flex items-center gap-0.5 px-1.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-400/30 text-amber-300 text-[10px] font-bold">
                <Star className="w-2.5 h-2.5 fill-amber-300 text-amber-300" />
                <span>{displayScore}</span>
              </div>
            </div>

            {/* Middle: Horizontal Natural Word-Wrapped Title (No 90deg rotation!) */}
            <div className="w-full my-auto px-1 py-2 flex items-center justify-center">
              <p className="text-[11px] font-bold text-neutral-100 leading-[1.25] tracking-tight break-words line-clamp-5 max-w-[75px] drop-shadow-[0_2px_4px_rgba(0,0,0,0.9)]">
                {item.title}
              </p>
            </div>

            {/* Bottom: Year and Status Dot */}
            <div className="w-full flex flex-col items-center gap-1 pt-1 border-t border-white/10">
              <span className="text-[10px] font-medium text-neutral-400">
                {item.release_year || "—"}
              </span>
              <div className="flex items-center gap-1">
                <span className={`w-2 h-2 rounded-full ${statusBadge.color} shadow-sm animate-pulse`} />
                <span className="text-[9px] font-medium text-neutral-300 truncate max-w-[60px]">
                  {statusBadge.label}
                </span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 4. EXPANDED VIEW (280px wide on Hover/Tap: Clean Poster Revealed + Minimal Bottom Card Overlay) */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            key="expanded-content"
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.2, delay: 0.05 }}
            className="absolute inset-0 flex flex-col justify-between p-3.5 z-10 pointer-events-none"
          >
            {/* Top Floating Badges */}
            <div className="flex items-center justify-between w-full">
              <span className="px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-white/15 text-[11px] font-semibold text-white flex items-center gap-1.5 shadow-lg">
                <SourceIcon className="w-3.5 h-3.5 text-indigo-400" />
                <span>{item.source === "ANILIST" ? "Anime" : item.source === "TMDB_SERIES" ? "Dizi" : "Film"}</span>
              </span>

              <div className="flex items-center gap-1.5">
                {item.is_favorite && (
                  <span className="px-2 py-0.5 rounded-full bg-amber-500/30 border border-amber-400/60 text-amber-300 text-[10px] font-extrabold flex items-center gap-1 shadow-md">
                    <Sparkles className="w-3 h-3 fill-amber-300" />
                    <span>ALTIN KUTU</span>
                  </span>
                )}
                <span className="px-2 py-1 rounded-lg bg-black/70 backdrop-blur-md border border-amber-400/30 text-amber-300 text-[11px] font-bold flex items-center gap-1 shadow-lg">
                  <Star className="w-3 h-3 fill-amber-300 text-amber-300" />
                  <span>{displayScore}</span>
                </span>
              </div>
            </div>

            {/* Bottom Gradient Card Information */}
            <div className="w-full rounded-xl bg-gradient-to-t from-black via-black/85 to-transparent p-3 pt-6 flex flex-col gap-1.5 backdrop-blur-[2px]">
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${statusBadge.color}`} />
                <span className="text-[11px] font-medium text-neutral-300">{statusBadge.label}</span>
                {item.release_year && (
                  <>
                    <span className="text-neutral-500">•</span>
                    <span className="text-[11px] text-neutral-400">{item.release_year}</span>
                  </>
                )}
              </div>

              <h4 className="text-sm font-bold text-white line-clamp-2 leading-snug drop-shadow-md">
                {item.title}
              </h4>

              {/* Genres Pills */}
              {item.genres && item.genres.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-0.5">
                  {item.genres.slice(0, 3).map((g) => (
                    <span
                      key={g}
                      className="px-1.5 py-0.5 rounded bg-white/10 text-[9px] font-medium text-neutral-300"
                    >
                      {g}
                    </span>
                  ))}
                </div>
              )}

              {/* Click to Edit Prompt */}
              <div
                onClick={(e) => {
                  e.stopPropagation();
                  onClick(item);
                }}
                className="flex items-center justify-between mt-2 pt-2 border-t border-white/10 text-[10px] text-indigo-300 font-medium cursor-pointer pointer-events-auto hover:text-indigo-200 active:scale-95 transition-transform"
              >
                <span className="flex items-center gap-1">
                  <Edit3 className="w-3 h-3" /> Düzenle / Puan Ver
                </span>
                <span className="text-neutral-400">Tıkla &gt;</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
