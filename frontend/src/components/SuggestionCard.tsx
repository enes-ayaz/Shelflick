"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Star,
  Play,
  Bookmark,
  CheckCircle2,
  X,
  Lightbulb,
  Clock,
  Calendar,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { UnifiedMediaDTO, LibraryItemDTO, SingleRecommendation } from "@/types";
import { formatPosterUrl } from "@/services/api";

export interface SuggestionCardProps {
  recommendations?: SingleRecommendation[];
  media?: UnifiedMediaDTO;
  justification?: string;
  confidenceScore?: number;
  libraryItems?: LibraryItemDTO[];
  isSavedInLibrary?: boolean;
  isAlreadyWatched?: boolean;
  onDismiss: () => void;
  onAddToList?: (media: UnifiedMediaDTO) => void;
  onMarkWatched?: (media: UnifiedMediaDTO) => void;
}

export const SuggestionCard: React.FC<SuggestionCardProps> = ({
  recommendations,
  media,
  justification,
  confidenceScore = 0.95,
  libraryItems,
  isSavedInLibrary = false,
  isAlreadyWatched = false,
  onDismiss,
  onAddToList,
  onMarkWatched,
}) => {
  // Normalize recommendations into a unified array
  const items = useMemo<SingleRecommendation[]>(() => {
    if (recommendations && recommendations.length > 0) {
      return recommendations;
    }
    if (media && justification) {
      return [
        {
          media,
          justification,
          confidence_score: confidenceScore ?? 0.95,
        },
      ];
    }
    return [];
  }, [recommendations, media, justification, confidenceScore]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [direction, setDirection] = useState(0);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Reset index when recommendation array changes
  useEffect(() => {
    setCurrentIndex(0);
    setDirection(0);
  }, [recommendations]);

  const count = items.length;
  const safeIndex = Math.min(Math.max(currentIndex, 0), Math.max(count - 1, 0));
  const currentItem = items[safeIndex];

  const currentMedia = currentItem?.media;
  const currentJustification = currentItem?.justification || "";
  const currentScore = currentItem?.confidence_score ?? confidenceScore ?? 0.95;

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3000);
  };

  const handlePrev = useCallback(() => {
    if (count <= 1) return;
    setDirection(-1);
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : count - 1));
  }, [count]);

  const handleNext = useCallback(() => {
    if (count <= 1) return;
    setDirection(1);
    setCurrentIndex((prev) => (prev < count - 1 ? prev + 1 : 0));
  }, [count]);

  const handleDotClick = useCallback(
    (index: number) => {
      if (index === safeIndex) return;
      setDirection(index > safeIndex ? 1 : -1);
      setCurrentIndex(index);
    },
    [safeIndex]
  );

  // Keyboard navigation support (ArrowLeft / ArrowRight)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") handlePrev();
      else if (e.key === "ArrowRight") handleNext();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handlePrev, handleNext]);

  if (!currentMedia) return null;

  // Determine bookmark and watched state for currently active item
  const isBookmarked = libraryItems
    ? libraryItems.some((i) => i.external_id === currentMedia.external_id)
    : isSavedInLibrary;

  const isWatched = libraryItems
    ? libraryItems.some(
        (i) => i.external_id === currentMedia.external_id && i.status === "COMPLETED"
      )
    : isAlreadyWatched;

  const handleBookmark = () => {
    if (!isBookmarked) {
      showToast(`"${currentMedia.title}" Rafına eklendi! 🔖`);
    } else {
      showToast("Listeden kaldırıldı");
    }
    if (onAddToList) onAddToList(currentMedia);
  };

  const handleWatched = () => {
    if (!isWatched) {
      showToast("İzlediklerim arasına kaydedildi 👁️");
    } else {
      showToast("İzlendi işareti kaldırıldı");
    }
    if (onMarkWatched) onMarkWatched(currentMedia);
  };

  const handleTrailer = () => {
    const query = encodeURIComponent(
      `${currentMedia.title} ${currentMedia.release_year || ""} trailer fragman`
    );
    window.open(`https://www.youtube.com/results?search_query=${query}`, "_blank");
  };

  const getSourceBadge = () => {
    switch (currentMedia.source) {
      case "ANILIST":
        return { label: "Anime", color: "bg-pink-500/20 text-pink-300 border-pink-500/30" };
      case "TMDB_MOVIE":
        return { label: "Film", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" };
      case "TMDB_SERIES":
        return { label: "Dizi", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" };
      default:
        return { label: "Medya", color: "bg-neutral-500/20 text-neutral-300 border-neutral-500/30" };
    }
  };

  const sourceBadge = getSourceBadge();

  // Slide animation variants for AnimatePresence
  const slideVariants = {
    enter: (dir: number) => ({
      x: dir > 0 ? 40 : dir < 0 ? -40 : 0,
      opacity: 0,
    }),
    center: {
      x: 0,
      opacity: 1,
      transition: {
        x: { type: "spring", stiffness: 350, damping: 32 },
        opacity: { duration: 0.22 },
      },
    },
    exit: (dir: number) => ({
      x: dir > 0 ? -40 : dir < 0 ? 40 : 0,
      opacity: 0,
      transition: {
        x: { type: "spring", stiffness: 350, damping: 32 },
        opacity: { duration: 0.18 },
      },
    }),
  };

  return (
    <div className="w-full max-w-4xl mx-auto relative group">
      {/* Toast Feedback */}
      <AnimatePresence>
        {toastMessage && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="absolute top-4 right-4 z-40 px-4 py-2 rounded-xl bg-indigo-600/90 text-white text-xs font-medium shadow-lg backdrop-blur-md flex items-center gap-2"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>{toastMessage}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Minimalist Navigation Arrows */}
      {count > 1 && (
        <>
          <button
            type="button"
            onClick={handlePrev}
            className="absolute -left-3 md:-left-5 top-1/2 -translate-y-1/2 z-30 p-2 md:p-3 rounded-full bg-neutral-900/90 hover:bg-indigo-600 text-white/80 hover:text-white border border-white/15 backdrop-blur-xl transition-all duration-200 shadow-2xl hover:scale-110 active:scale-95 cursor-pointer"
            title="Önceki Öneri (←)"
            aria-label="Önceki Öneri"
          >
            <ChevronLeft className="w-5 h-5" />
          </button>

          <button
            type="button"
            onClick={handleNext}
            className="absolute -right-3 md:-right-5 top-1/2 -translate-y-1/2 z-30 p-2 md:p-3 rounded-full bg-neutral-900/90 hover:bg-indigo-600 text-white/80 hover:text-white border border-white/15 backdrop-blur-xl transition-all duration-200 shadow-2xl hover:scale-110 active:scale-95 cursor-pointer"
            title="Sonraki Öneri (→)"
            aria-label="Sonraki Öneri"
          >
            <ChevronRight className="w-5 h-5" />
          </button>
        </>
      )}

      {/* Main Card Shell */}
      <div className="glass-panel rounded-3xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
        {/* Animated Slide Content */}
        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={currentMedia.external_id || safeIndex}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
          >
            <div className="flex flex-col md:flex-row gap-6 md:gap-8 items-start">
              {/* Left: Poster Image with source & score badges */}
              <div className="relative w-full md:w-64 flex-shrink-0 aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl border border-white/10 bg-neutral-900 group/poster">
                <img
                  src={formatPosterUrl(currentMedia.poster_url)}
                  alt={currentMedia.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover/poster:scale-105"
                />

                {/* Quick source badge */}
                <div className="absolute top-3 left-3">
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold uppercase tracking-wider border backdrop-blur-md ${sourceBadge.color}`}
                  >
                    {sourceBadge.label}
                  </span>
                </div>

                {/* Score Badge */}
                <div className="absolute bottom-3 right-3 flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-black/80 backdrop-blur-md border border-amber-500/30 text-amber-400 font-bold text-sm shadow-gold">
                  <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                  <span>
                    {currentMedia.base_score ? currentMedia.base_score.toFixed(1) : "N/A"}
                  </span>
                </div>
              </div>

              {/* Right: Content & Metadata */}
              <div className="flex-1 flex flex-col justify-between w-full h-full">
                <div>
                  {/* Top Bar: Carousel index indicator, Title & Dismiss */}
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      {count > 1 && (
                        <div className="mb-2">
                          <span className="text-[11px] font-semibold tracking-wider uppercase px-2.5 py-1 rounded-full bg-indigo-500/15 text-indigo-300 border border-indigo-500/25">
                            Öneri {safeIndex + 1} / {count}
                          </span>
                        </div>
                      )}
                      <h2 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight leading-tight">
                        {currentMedia.title}
                      </h2>
                      {currentMedia.original_title &&
                        currentMedia.original_title !== currentMedia.title && (
                          <p className="text-neutral-400 text-sm mt-0.5 font-medium italic">
                            {currentMedia.original_title}
                          </p>
                        )}
                    </div>

                    <button
                      type="button"
                      onClick={onDismiss}
                      className="text-neutral-400 hover:text-white p-2 rounded-xl hover:bg-white/5 transition-colors"
                      title="Kapat / Pas Geç"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </div>

                  {/* Metadata: Year, Runtime, Match Confidence */}
                  <div className="flex flex-wrap items-center gap-4 text-xs md:text-sm text-neutral-400 mt-3">
                    {currentMedia.release_year && (
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4 text-neutral-400" />
                        <span>{currentMedia.release_year}</span>
                      </span>
                    )}
                    {currentMedia.runtime_minutes && (
                      <span className="flex items-center gap-1.5">
                        <Clock className="w-4 h-4 text-neutral-400" />
                        <span>{currentMedia.runtime_minutes} dk</span>
                      </span>
                    )}
                    <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-medium">
                      🎯 %{Math.round(currentScore * 100)} Eşleşme
                    </span>
                  </div>

                  {/* Genres & Themes */}
                  <div className="flex flex-wrap gap-1.5 mt-4">
                    {currentMedia.genres.map((genre) => (
                      <span
                        key={genre}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium bg-white/[0.04] text-neutral-300 border border-white/5"
                      >
                        {genre}
                      </span>
                    ))}
                    {currentMedia.themes.slice(0, 4).map((theme) => (
                      <span
                        key={theme}
                        className="px-2.5 py-1 rounded-lg text-xs font-medium bg-indigo-500/10 text-indigo-300/80 border border-indigo-500/20"
                      >
                        #{theme}
                      </span>
                    ))}
                  </div>

                  {/* "💡 Neden Bu?" Highlight Box */}
                  <div className="mt-5 p-4 md:p-5 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-purple-950/20 to-neutral-900/60 border border-indigo-500/30 relative">
                    <div className="flex items-center gap-2 text-indigo-300 font-semibold text-xs tracking-wider uppercase mb-1.5">
                      <Lightbulb className="w-4 h-4 text-amber-400" />
                      <span>Neden Bu? (Kişisel Gerekçe)</span>
                    </div>
                    <p className="text-neutral-200 text-sm md:text-base leading-relaxed font-normal">
                      {currentJustification}
                    </p>
                  </div>
                </div>

                {/* Quick Actions Row */}
                <div className="flex flex-wrap items-center gap-2.5 mt-6 pt-5 border-t border-white/5">
                  <button
                    type="button"
                    onClick={handleTrailer}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs md:text-sm font-medium text-white bg-white/10 hover:bg-white/15 border border-white/10 transition-colors cursor-pointer"
                  >
                    <Play className="w-3.5 h-3.5 text-red-400 fill-red-400" />
                    <span>Fragman İzle</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleBookmark}
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs md:text-sm font-medium transition-colors border cursor-pointer ${
                      isBookmarked
                        ? "bg-indigo-600 text-white border-indigo-500 shadow-md shadow-indigo-600/30"
                        : "bg-white/5 text-neutral-300 hover:bg-white/10 hover:text-white border-white/10"
                    }`}
                  >
                    <Bookmark
                      className={`w-3.5 h-3.5 ${isBookmarked ? "fill-white" : ""}`}
                    />
                    <span>{isBookmarked ? "✓ Listede" : "Listeme Ekle"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleWatched}
                    className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs md:text-sm font-medium transition-colors border cursor-pointer ${
                      isWatched
                        ? "bg-emerald-600 text-white border-emerald-500"
                        : "bg-white/5 text-neutral-300 hover:bg-white/10 hover:text-white border-white/10"
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>{isWatched ? "İzlendi" : "Zaten İzledim"}</span>
                  </button>

                  <button
                    type="button"
                    onClick={onDismiss}
                    className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs md:text-sm font-medium text-neutral-400 hover:text-neutral-200 hover:bg-white/5 ml-auto transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Pas Geç</span>
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </AnimatePresence>

        {/* 5 Dot Indicators at the bottom */}
        {count > 1 && (
          <div className="flex items-center justify-center gap-2.5 mt-6 pt-4 border-t border-white/5">
            {items.map((_, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleDotClick(idx)}
                className={`w-2.5 h-2.5 rounded-full transition-all duration-300 cursor-pointer ${
                  idx === safeIndex
                    ? "bg-white scale-125 shadow-[0_0_8px_rgba(255,255,255,0.8)] opacity-100"
                    : "bg-white/35 hover:bg-white/60 hover:scale-110"
                }`}
                title={`Öneri ${idx + 1}`}
                aria-label={`Öneri ${idx + 1}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
