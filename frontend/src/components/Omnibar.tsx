"use client";

import React, { useState, useEffect, useRef, FormEvent, KeyboardEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Sparkles,
  Dices,
  Film,
  Tv,
  Compass,
  Star,
  Loader2,
  X,
} from "lucide-react";
import { MediaTypeFilter, LiveSearchResultItem } from "@/types";
import { useDebounce } from "@/hooks/useDebounce";
import { fetchLiveSearch, formatPosterUrl } from "@/services/api";

interface OmnibarProps {
  onSearch: (query: string, filter: MediaTypeFilter) => void;
  onRandom: (filter?: MediaTypeFilter) => void;
  onSelectLiveResult?: (item: LiveSearchResultItem) => void;
  isLoading?: boolean;
  compact?: boolean;
}

const FILTERS: { label: string; value: MediaTypeFilter; icon: React.ReactNode }[] = [
  { label: "Tümü", value: "ALL", icon: <Compass className="w-3.5 h-3.5" /> },
  { label: "Anime", value: "ANIME", icon: <Sparkles className="w-3.5 h-3.5" /> },
  { label: "Film", value: "MOVIE", icon: <Film className="w-3.5 h-3.5" /> },
  { label: "Dizi", value: "SERIES", icon: <Tv className="w-3.5 h-3.5" /> },
];

export const Omnibar: React.FC<OmnibarProps> = ({
  onSearch,
  onRandom,
  onSelectLiveResult,
  isLoading = false,
  compact = false,
}) => {
  const [query, setQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<MediaTypeFilter>("ALL");

  // Live autocomplete state
  const [liveResults, setLiveResults] = useState<LiveSearchResultItem[]>([]);
  const [isSearchingLive, setIsSearchingLive] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // 300ms Debounce hook
  const debouncedQuery = useDebounce(query, 300);

  // Trigger live search when debounced query updates
  useEffect(() => {
    const trimmed = debouncedQuery.trim();
    if (trimmed.length < 2) {
      setLiveResults([]);
      setIsSearchingLive(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    async function searchLive() {
      setIsSearchingLive(true);
      try {
        const results = await fetchLiveSearch(trimmed, controller.signal);
        setLiveResults(results.slice(0, 5));
        setIsDropdownOpen(results.length > 0);
      } catch (err) {
        console.warn("Live search error:", err);
      } finally {
        setIsSearchingLive(false);
      }
    }

    searchLive();

    return () => {
      controller.abort();
    };
  }, [debouncedQuery]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSubmit = (e?: FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim() || isLoading) return;
    setIsDropdownOpen(false);
    onSearch(query.trim(), activeFilter);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    } else if (e.key === "Escape") {
      setIsDropdownOpen(false);
    }
  };

  const handleSelectLiveItem = (item: LiveSearchResultItem) => {
    setIsDropdownOpen(false);
    setQuery(item.title);
    if (onSelectLiveResult) {
      onSelectLiveResult(item);
    } else {
      onSearch(item.title, activeFilter);
    }
  };

  const handleClear = () => {
    setQuery("");
    setLiveResults([]);
    setIsDropdownOpen(false);
  };

  return (
    <motion.div
      layout
      transition={{ type: "spring", stiffness: 300, damping: 30 }}
      className={`w-full max-w-2xl mx-auto flex flex-col items-center transition-all ${
        compact ? "pt-2 pb-4" : "py-8"
      }`}
      ref={containerRef}
    >
      <form onSubmit={handleSubmit} className="w-full relative group">
        {/* Glow backdrop on focus */}
        <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500/30 via-purple-500/30 to-pink-500/20 rounded-2xl blur-lg opacity-40 group-focus-within:opacity-100 transition duration-500 pointer-events-none" />

        {/* Input container */}
        <div className="relative flex items-center w-full glass-input rounded-2xl px-5 py-4 text-white shadow-2xl transition duration-300 border border-white/10 group-focus-within:border-indigo-500/60 z-10">
          <Search className="w-5 h-5 text-neutral-400 mr-3 flex-shrink-0 group-focus-within:text-indigo-400 transition-colors" />

          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (e.target.value.trim().length >= 2 && liveResults.length > 0) {
                setIsDropdownOpen(true);
              }
            }}
            onFocus={() => {
              if (liveResults.length > 0) setIsDropdownOpen(true);
            }}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Nasıl bir yapım arıyorsun? (örn: Fight Club veya karanlık anime)"
            className="w-full bg-transparent text-white placeholder-neutral-400 text-base md:text-lg focus:outline-none disabled:opacity-50 tracking-wide"
          />

          {/* Real-time Searching Spinner or Clear Icon */}
          <div className="flex items-center gap-1.5 ml-2">
            {isSearchingLive && (
              <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
            )}

            {query.trim().length > 0 && (
              <button
                type="button"
                onClick={handleClear}
                className="text-neutral-400 hover:text-white p-1 rounded-md hover:bg-white/10 transition-colors cursor-pointer"
                title="Temizle"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Autocomplete Dropdown List */}
        <AnimatePresence>
          {isDropdownOpen && liveResults.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.98 }}
              transition={{ duration: 0.18 }}
              className="absolute top-full left-0 right-0 mt-2 z-50 glass-panel rounded-2xl p-2 shadow-2xl border border-white/10 backdrop-blur-2xl bg-neutral-950/95 overflow-hidden"
            >
              <div className="px-3 py-1.5 text-[11px] font-semibold tracking-wider uppercase text-neutral-400 border-b border-white/5 flex items-center justify-between">
                <span>Canlı Eşleşmeler</span>
                <span className="text-[10px] text-indigo-400 font-normal">Hızlı Seçim</span>
              </div>

              <div className="divide-y divide-white/[0.04] mt-1">
                {liveResults.map((item) => {
                  const typeLabel =
                    item.type === "ANIME"
                      ? "Anime"
                      : item.type === "SERIES"
                      ? "Dizi"
                      : "Film";

                  const typeColor =
                    item.type === "ANIME"
                      ? "bg-pink-500/20 text-pink-300 border-pink-500/30"
                      : item.type === "SERIES"
                      ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/30"
                      : "bg-blue-500/20 text-blue-300 border-blue-500/30";

                  return (
                    <button
                      key={`${item.type}-${item.id}`}
                      type="button"
                      onClick={() => handleSelectLiveItem(item)}
                      className="w-full flex items-center gap-3.5 p-2.5 rounded-xl hover:bg-white/10 transition-all text-left group/item cursor-pointer"
                    >
                      {/* Thumbnail Poster */}
                      <div className="w-9 h-12 rounded-lg overflow-hidden flex-shrink-0 bg-neutral-800 border border-white/10 relative shadow-sm">
                        {item.poster_path ? (
                          <img
                            src={formatPosterUrl(item.poster_path)}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover/item:scale-105 transition-transform duration-300"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-neutral-500 text-[9px] text-center p-0.5">
                            Görsel
                          </div>
                        )}
                      </div>

                      {/* Title & Metadata */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white truncate group-hover/item:text-indigo-300 transition-colors">
                            {item.title}
                          </p>
                          <span
                            className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded border backdrop-blur-sm ${typeColor}`}
                          >
                            {typeLabel}
                          </span>
                        </div>

                        <div className="flex items-center gap-2.5 text-xs text-neutral-400 mt-1">
                          {item.release_year && (
                            <span>{item.release_year}</span>
                          )}
                          {item.base_score ? (
                            <span className="flex items-center gap-1 text-amber-400 font-medium">
                              <Star className="w-3 h-3 fill-amber-400" />
                              <span>{item.base_score.toFixed(1)}</span>
                            </span>
                          ) : null}
                          {item.genres && item.genres.length > 0 && (
                            <span className="text-neutral-500 truncate text-[11px]">
                              • {item.genres.slice(0, 2).join(", ")}
                            </span>
                          )}
                        </div>
                      </div>
                    </button>
                  );
                })}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </form>

      {/* Format Filter Pills */}
      <div className="flex flex-wrap items-center justify-center gap-2 mt-4 select-none">
        {FILTERS.map((item) => {
          const isActive = activeFilter === item.value;
          return (
            <button
              key={item.value}
              type="button"
              onClick={() => setActiveFilter(item.value)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs md:text-sm font-medium transition-all duration-200 border cursor-pointer ${
                isActive
                  ? "bg-indigo-600/30 text-indigo-300 border-indigo-500/50 shadow-glow"
                  : "bg-white/[0.03] text-neutral-400 border-white/5 hover:bg-white/[0.08] hover:text-neutral-200"
              }`}
            >
              {item.icon}
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      {/* Action Buttons: [ Öneri Getir ] & [ 🎲 Şansıma Güveniyorum ] */}
      <div className="flex flex-wrap items-center justify-center gap-3 mt-6">
        <button
          type="button"
          onClick={() => handleSubmit()}
          disabled={!query.trim() || isLoading}
          className="relative inline-flex items-center justify-center px-6 py-2.5 rounded-xl font-medium text-sm text-white bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:hover:bg-indigo-600 transition duration-200 shadow-glow cursor-pointer disabled:cursor-not-allowed group overflow-hidden"
        >
          {isLoading ? (
            <span className="flex items-center gap-2">
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              <span>Analiz Ediliyor...</span>
            </span>
          ) : (
            <span className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-indigo-200 group-hover:scale-110 transition-transform" />
              <span>Öneri Getir</span>
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => onRandom(activeFilter)}
          disabled={isLoading}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-medium text-sm text-neutral-300 bg-white/[0.05] hover:bg-white/[0.1] hover:text-white border border-white/10 transition duration-200 cursor-pointer disabled:opacity-50"
        >
          <Dices className="w-4 h-4 text-amber-400 animate-spin-hover" />
          <span>Şansıma Güveniyorum</span>
        </button>
      </div>
    </motion.div>
  );
};
