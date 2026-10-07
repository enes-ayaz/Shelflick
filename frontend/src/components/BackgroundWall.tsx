"use client";

import React, { useMemo, useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";
import { formatPosterUrl } from "@/services/api";

// ─── Poster catalogue with metadata for click-to-search ──────────────────────
interface PosterEntry {
  url: string;
  title: string;
  query: string; // exact query forwarded to the recommendation engine
  id: string; // TMDB ID for direct navigation
}

const POSTER_COLLECTION: PosterEntry[] = [
  {
    url: "https://image.tmdb.org/t/p/w500/f89U3ADr1oiB1s9GkdPOEpXUk5H.jpg",
    title: "The Matrix",
    query: "Matrix gibi distopik siber-punk bilim kurgu",
    id: "603",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/qJ2tW6WMUDux911r6m7haRef0WH.jpg",
    title: "The Dark Knight",
    query: "The Dark Knight gibi karanlık kahraman filmi",
    id: "155",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/gEU2QniE6E77NI6lCU6MxlNBvIx.jpg",
    title: "Interstellar",
    query: "Interstellar gibi uzay ve zaman bükücü bilim kurgu",
    id: "157336",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/xlaY2zyzMfkhk0HSC5VUwzoZPU1.jpg",
    title: "Inception",
    query: "Inception gibi zihin bükücü rüya gerilimi",
    id: "27205",
  },
  {
    url: "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx19-gtMC64182sm4.jpg",
    title: "Monster",
    query: "Monster gibi derin psikolojik suç gerilimi anime",
    id: "3374",
  },
  {
    url: "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx16498-C6FPmWm59CyP.jpg",
    title: "Attack on Titan",
    query: "Attack on Titan gibi epik fantezi aksiyon anime",
    id: "1429",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/bptfVGEQuv6vDTIMVCHjJ9Dz8PX.jpg",
    title: "Fight Club",
    query: "Fight Club gibi kimlik buhranı ve çarpıcı twist içeren film",
    id: "550",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/ggFHVNu6YYI5L9pCfOacjizRGt.jpg",
    title: "Breaking Bad",
    query: "Breaking Bad gibi ahlaki çöküş hikayesi dizi",
    id: "1396",
  },
  {
    url: "https://s4.anilist.co/file/anilistcdn/media/anime/cover/large/bx9253-tIUXF2gfU8Sg.jpg",
    title: "Steins;Gate",
    query: "Steins;Gate gibi zaman yolculuğu ve bilimsel gerilim anime",
    id: "34398",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/d5NXSklXo0qyIYkgV94XAgMIckC.jpg",
    title: "Dune",
    query: "Dune gibi epik evren kurgusu olan bilim kurgu",
    id: "438148",
  },
  {
    url: "https://image.tmdb.org/t/p/w500/fqldf2t8ztc9aiwn3k6mlX3tvRT.jpg",
    title: "Arcane",
    query: "Arcane gibi görsel açıdan muhteşem animasyon dizisi",
    id: "94605",
  },
  {
    url: "https://s4.anilist.co/file/anilistcdn/media/anime/cover/medium/bx1-GCsPm7waJ4kS.png",
    title: "Cowboy Bebop",
    query: "Cowboy Bebop gibi melankoli ve cazlı uzay western anime",
    id: "30991",
  },
];

// ─── Individual poster card ───────────────────────────────────────────────────
interface PosterCardProps {
  entry: PosterEntry;
  onPosterClick: (query: string, title: string) => void;
}

const PosterCard: React.FC<PosterCardProps> = ({ entry, onPosterClick }) => {
  const [hovered, setHovered] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };
    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const proxied = formatPosterUrl(entry.url);

  return (
    <motion.div
      className="relative w-full aspect-[2/3] rounded-lg overflow-hidden bg-neutral-900 cursor-pointer flex-shrink-0 touch-manipulation"
      onHoverStart={() => {
        if (!isMobile) setHovered(true);
      }}
      onHoverEnd={() => {
        if (!isMobile) setHovered(false);
      }}
      onClick={() => router.push(`/media/${entry.id}`)}
      animate={{
        scale: hovered ? 1.08 : 1,
        filter: isMobile
          ? hovered
            ? "blur(0px) brightness(1.2) saturate(1.3)"
            : "blur(0px) brightness(0.65) saturate(0.85)"
          : hovered
          ? "blur(0px) brightness(1.15) saturate(1.3)"
          : "blur(1.5px) brightness(0.55) saturate(0.7)",
        zIndex: hovered ? 20 : 1,
      }}
      whileTap={{
        scale: 1.08,
        filter: "blur(0px) brightness(1.25) saturate(1.3)",
      }}
      transition={{ type: "spring", stiffness: 280, damping: 22 }}
      style={{ position: "relative" }}
    >
      <img
        src={proxied}
        alt={entry.title}
        loading="lazy"
        onError={(e) => {
          (e.currentTarget as HTMLImageElement).src =
            "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500";
        }}
        className="w-full h-full object-cover"
      />

      {/* Hover reveal: title tooltip at the bottom */}
      <motion.div
        className="absolute inset-x-0 bottom-0 px-2 pb-2 pt-6 pointer-events-none"
        style={{
          background:
            "linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 100%)",
        }}
        initial={{ opacity: 0 }}
        animate={{ opacity: hovered ? 1 : 0 }}
        transition={{ duration: 0.18 }}
      >
        <p className="text-white text-[11px] font-semibold leading-tight drop-shadow text-center">
          {entry.title}
        </p>
        <p className="text-indigo-300 text-[9px] text-center mt-0.5 font-medium">
          Tıkla → Detaylara git
        </p>
      </motion.div>

      {/* Outer glow ring on hover */}
      {hovered && (
        <div className="absolute inset-0 rounded-lg ring-2 ring-indigo-400/70 shadow-[0_0_20px_rgba(99,102,241,0.6)] pointer-events-none" />
      )}
    </motion.div>
  );
};

// ─── Scrolling column ─────────────────────────────────────────────────────────
interface ScrollColumnProps {
  posters: PosterEntry[];
  reverse: boolean;
  duration: number;
  onPosterClick: (query: string, title: string) => void;
  className?: string;
}

const ScrollColumn: React.FC<ScrollColumnProps> = ({
  posters,
  reverse,
  duration,
  onPosterClick,
  className,
}) => {
  const [paused, setPaused] = useState(false);

  // Triplicate for seamless infinite loop
  const looped = useMemo(() => [...posters, ...posters, ...posters], [posters]);

  return (
    <div
      className={`flex flex-col gap-4 flex-1 overflow-hidden ${className || ""}`}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
    >
      <motion.div
        className="flex flex-col gap-4"
        animate={
          paused
            ? false
            : {
                y: reverse ? ["0%", "-33.333%"] : ["-33.333%", "0%"],
              }
        }
        transition={{
          repeat: Infinity,
          repeatType: "loop",
          duration,
          ease: "linear",
        }}
      >
        {looped.map((entry, idx) => (
          <PosterCard
            key={`${entry.title}-${idx}`}
            entry={entry}
            onPosterClick={onPosterClick}
          />
        ))}
      </motion.div>
    </div>
  );
};

// ─── Main BackgroundWall ──────────────────────────────────────────────────────
export interface BackgroundWallProps {
  onPosterClick?: (query: string, title: string) => void;
}

export const BackgroundWall: React.FC<BackgroundWallProps> = ({
  onPosterClick,
}) => {
  const COL_COUNT = 5;

  // Distribute posters across columns
  const columns = useMemo<PosterEntry[][]>(() => {
    const cols: PosterEntry[][] = Array.from({ length: COL_COUNT }, () => []);
    POSTER_COLLECTION.forEach((entry, idx) => {
      cols[idx % COL_COUNT].push(entry);
    });
    return cols;
  }, []);

  const handleClick = useCallback(
    (query: string, title: string) => {
      onPosterClick?.(query, title);
    },
    [onPosterClick]
  );

  return (
    <div
      aria-hidden="true"
      className="fixed inset-0 z-0 overflow-hidden select-none"
    >
      {/* Poster columns — pointer events ON so hover/click work */}
      <div className="absolute inset-0 flex justify-between gap-2 md:gap-3 px-2 md:px-3 opacity-100">
        {columns.map((col, colIdx) => (
          <ScrollColumn
            key={colIdx}
            posters={col}
            reverse={colIdx % 2 === 1}
            duration={55 + colIdx * 9}
            onPosterClick={handleClick}
            className={colIdx >= 3 ? "hidden sm:flex" : "flex"}
          />
        ))}
      </div>

      {/* Dark vignette — pointer-events-none so clicks pass through to posters */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#0a0a0c]/85 via-[#0a0a0c]/80 to-[#0a0a0c] pointer-events-none" />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(99,102,241,0.07)_0%,transparent_68%)] pointer-events-none" />
    </div>
  );
};
