"use client";

import React, { useState, useEffect, useRef } from "react";
import { BookOpen, LogIn, LogOut, Radar, Sparkles, Clock, Calendar, ChevronRight, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { FloatingBadge } from "./FloatingBadge";
import { BrandLogo } from "./BrandLogo";
import { useAuth } from "@/context/AuthContext";
import { getLibraryStats, formatPosterUrl } from "@/services/api";
import { LibraryItemDTO } from "@/types";
import Link from "next/link";

interface HeaderProps {
  onReset: () => void;
  onOpenShelf?: () => void;
  shelfCount: number;
  activeWatchingItem?: { title: string; id?: string; external_id?: string } | null;
  onWatchingFeedback?: (action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS") => void;
}

function formatRadarInfo(item: LibraryItemDTO): { text: string; subtext?: string; isSoon: boolean } {
  const info = item.next_airing_info;
  if (info) {
    // AniList format: { airingAt: 1729000000, episode: 8 }
    if (typeof info === "object" && info.airingAt) {
      const airDate = new Date(info.airingAt * 1000);
      const diffMs = airDate.getTime() - Date.now();
      const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
      const epNum = info.episode || "";
      const dateStr = airDate.toLocaleDateString("tr-TR", { day: "numeric", month: "short" });

      if (diffDays <= 0) {
        return { text: `Bölüm ${epNum} Yayında!`, subtext: "Bugün", isSoon: true };
      } else if (diffDays === 1) {
        return { text: `Bölüm ${epNum} Yarın`, subtext: dateStr, isSoon: true };
      } else if (diffDays <= 7) {
        return { text: `Bölüm ${epNum} • ${diffDays} Gün Kaldı`, subtext: dateStr, isSoon: true };
      } else {
        return { text: `Bölüm ${epNum}`, subtext: dateStr, isSoon: false };
      }
    }

    // TMDB format: { air_date: "2026-10-18", episode_number: 8 }
    if (typeof info === "object" && (info.air_date || info.episode_number)) {
      const epNum = info.episode_number || "";
      if (info.air_date) {
        const airDate = new Date(info.air_date);
        const diffMs = airDate.getTime() - Date.now();
        const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
        const dateStr = !isNaN(airDate.getTime())
          ? airDate.toLocaleDateString("tr-TR", { day: "numeric", month: "short" })
          : info.air_date;

        if (diffDays > 0 && diffDays <= 7) {
          return { text: `Bölüm ${epNum} • ${diffDays} Gün Kaldı`, subtext: dateStr, isSoon: true };
        } else if (diffDays === 0) {
          return { text: `Bölüm ${epNum} Yayında!`, subtext: "Bugün", isSoon: true };
        }
        return { text: `Bölüm ${epNum}`, subtext: dateStr, isSoon: false };
      }
      return { text: `Yeni Bölüm #${epNum}`, isSoon: false };
    }
  }

  // Fallback to airing_status string
  const rawStatus = (item.airing_status || "").trim();
  if (rawStatus.toLowerCase() === "returning series") {
    return { text: "Yeni Sezon Onaylandı", subtext: "Devam Ediyor", isSoon: false };
  }
  if (rawStatus.toLowerCase() === "releasing") {
    return { text: "Yeni Bölümler Yayında", subtext: "Haftalık Yayın", isSoon: true };
  }
  if (rawStatus.toLowerCase() === "in production") {
    return { text: "Yapım Aşamasında", subtext: "Yakında", isSoon: false };
  }

  return { text: rawStatus || "Yeni Sezon Radarda", isSoon: false };
}

export const Header: React.FC<HeaderProps> = ({
  onReset,
  onOpenShelf,
  shelfCount,
  activeWatchingItem,
  onWatchingFeedback,
}) => {
  const { user, openAuthModal, logout } = useAuth();
  const [radarItems, setRadarItems] = useState<LibraryItemDTO[]>([]);
  const [isRadarOpen, setIsRadarOpen] = useState(false);
  const radarRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    async function loadRadar() {
      try {
        const stats = await getLibraryStats(user?.id);
        if (stats && stats.radar_items) {
          setRadarItems(stats.radar_items);
        }
      } catch (err) {
        console.warn("Could not load radar items:", err);
      }
    }
    loadRadar();
  }, [user?.id, shelfCount]);

  // Click outside to close radar popover
  useEffect(() => {
    if (!isRadarOpen) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (radarRef.current && !radarRef.current.contains(e.target as Node)) {
        setIsRadarOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isRadarOpen]);

  const userInitial = user?.name
    ? user.name.trim().charAt(0).toUpperCase()
    : user?.email
    ? user.email.charAt(0).toUpperCase()
    : "U";

  return (
    <header className="fixed top-0 left-0 right-0 z-40 px-4 md:px-8 py-4 flex items-center justify-between pointer-events-auto backdrop-blur-md bg-[#0a0a0c]/60 border-b border-white/[0.04]">
      {/* Top-Left: Shelflick Logo (||> icon + typography) */}
      <Link
        href="/"
        onClick={onReset}
        className="flex items-center gap-2.5 group cursor-pointer focus:outline-none"
        title="Ana Sayfaya Dön / Aramayı Sıfırla"
      >
        <BrandLogo />
        <div className="flex flex-col text-left">
          <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-400 transition-colors">
            Shelflick
          </span>
          <span className="text-[10px] text-neutral-400 font-medium -mt-1 tracking-wider uppercase">
            MediaPulse Engine
          </span>
        </div>
      </Link>

      {/* Top-Right: Radar, Rafım Button, Feedback, and User Auth / Profile */}
      <div className="flex items-center gap-2 md:gap-3">
        {/* FloatingBadge active mood feedback: Only renders if user is currently watching an item */}
        {activeWatchingItem && (
          <div className="hidden lg:block">
            <FloatingBadge
              mediaTitle={activeWatchingItem.title}
              mediaId={activeWatchingItem.external_id || activeWatchingItem.id}
              onAction={onWatchingFeedback}
            />
          </div>
        )}

        {/* [ 📡 Sezon Radarı ] Popover Button */}
        <div className="relative" ref={radarRef}>
          <button
            type="button"
            onClick={() => setIsRadarOpen((prev) => !prev)}
            className={`relative flex items-center gap-1.5 px-3 py-1.5 md:py-2 rounded-xl border text-xs md:text-sm font-medium transition-all duration-200 cursor-pointer ${
              isRadarOpen
                ? "bg-amber-500/20 border-amber-400/40 text-amber-200 shadow-[0_0_15px_rgba(245,158,11,0.25)]"
                : "bg-white/[0.05] hover:bg-white/[0.1] border-white/10 hover:border-amber-400/40 text-neutral-200 hover:text-white"
            }`}
            title="Yeni Sezon & Bölüm Radarı"
          >
            <Radar className={`w-4 h-4 ${radarItems.length > 0 ? "text-amber-400 animate-pulse" : "text-neutral-400"}`} />
            <span className="hidden sm:inline">Radar</span>
            {radarItems.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-neutral-950 text-[10px] font-black shadow-sm">
                {radarItems.length}
              </span>
            )}
          </button>

          {/* Radar Popover Dropdown Panel */}
          <AnimatePresence>
            {isRadarOpen && (
              <motion.div
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 8, scale: 0.95 }}
                transition={{ type: "spring", stiffness: 380, damping: 28 }}
                className="absolute right-0 mt-2.5 w-80 sm:w-96 rounded-3xl bg-neutral-950/95 border border-white/15 backdrop-blur-2xl shadow-2xl p-4 z-50 overflow-hidden flex flex-col gap-3"
              >
                {/* Panel Header */}
                <div className="flex items-center justify-between pb-2.5 border-b border-white/10">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-amber-500/20 border border-amber-400/30 flex items-center justify-center text-amber-400">
                      <Radar className="w-4 h-4 animate-pulse" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-white tracking-wide flex items-center gap-1.5">
                        Yeni Sezon & Bölüm Radarı
                        <span className="px-1.5 py-0.2 rounded-full bg-amber-400/20 text-amber-300 text-[10px]">
                          {radarItems.length}
                        </span>
                      </h4>
                      <p className="text-[10px] text-neutral-400">Takip ettiğin yapımlardan haberler</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsRadarOpen(false)}
                    className="p-1 rounded-lg hover:bg-white/10 text-neutral-400 hover:text-white"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Radar Items List */}
                <div className="max-h-72 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                  {radarItems.length === 0 ? (
                    <div className="py-8 text-center text-xs text-neutral-400 space-y-1">
                      <p>📡 Radarda bekleyen yeni sezon veya bölüm bulunmuyor.</p>
                      <p className="text-[10px] text-neutral-500">
                        Rafına devam eden diziler ekledikçe burada görünecek.
                      </p>
                    </div>
                  ) : (
                    radarItems.map((item) => {
                      const radarInfo = formatRadarInfo(item);
                      return (
                        <div
                          key={item.id}
                          className="flex items-center gap-3 p-2 rounded-2xl bg-white/[0.03] hover:bg-white/[0.06] border border-white/5 hover:border-white/10 transition-all group"
                        >
                          <img
                            src={formatPosterUrl(item.poster_url)}
                            alt={item.title}
                            className="w-11 h-16 rounded-xl object-cover flex-shrink-0 border border-white/10 group-hover:scale-105 transition-transform"
                          />
                          <div className="flex-1 min-w-0">
                            <h5 className="text-xs font-bold text-white truncate group-hover:text-amber-300 transition-colors">
                              {item.title}
                            </h5>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="px-1.5 py-0.2 rounded bg-white/5 text-[9px] font-semibold text-neutral-300">
                                {item.status === "WATCHING"
                                  ? "İzleniyor"
                                  : item.status === "PLAN_TO_WATCH"
                                  ? "Rafımda"
                                  : "Tamamlandı"}
                              </span>
                              {item.source === "ANILIST" ? (
                                <span className="text-[9px] text-pink-400 font-bold">Anime</span>
                              ) : (
                                <span className="text-[9px] text-emerald-400 font-bold">Dizi</span>
                              )}
                            </div>
                            <div className="mt-1 flex items-center justify-between text-[11px]">
                              <span
                                className={`font-semibold ${
                                  radarInfo.isSoon
                                    ? "text-amber-300 font-bold"
                                    : "text-neutral-300"
                                }`}
                              >
                                {radarInfo.text}
                              </span>
                              {radarInfo.subtext && (
                                <span className="text-[10px] text-neutral-500 font-mono">
                                  {radarInfo.subtext}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>

                {/* Panel Footer */}
                <div className="pt-2 border-t border-white/10 text-center">
                  <Link
                    href="/library"
                    onClick={() => setIsRadarOpen(false)}
                    className="inline-flex items-center gap-1 text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold transition-colors"
                  >
                    <span>Kişisel Rafına Git</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* [ 📚 Rafım ] Button */}
        <Link
          href="/library"
          className="flex items-center gap-2 px-3.5 py-1.5 md:px-4 md:py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 hover:border-indigo-500/40 text-neutral-200 hover:text-white transition-all duration-200 cursor-pointer text-xs md:text-sm font-medium shadow-sm group"
        >
          <BookOpen className="w-4 h-4 text-indigo-400 group-hover:scale-110 transition-transform" />
          <span>Rafım</span>
          <span className="px-2 py-0.5 rounded-full bg-indigo-600/60 border border-indigo-400/30 text-white text-[11px] font-bold">
            {shelfCount}
          </span>
        </Link>

        {/* User Auth Section */}
        {user ? (
          <div className="flex items-center gap-2">
            <div
              className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-neutral-900/80 border border-white/10 text-neutral-200 text-xs font-medium"
              title={user.email}
            >
              <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-white text-[11px] font-bold">
                {userInitial}
              </div>
              <span className="hidden sm:inline font-medium max-w-[120px] truncate">
                {user.name || user.email.split("@")[0]}
              </span>
            </div>
            <button
              onClick={logout}
              title="Çıkış Yap"
              className="p-2 rounded-xl bg-white/[0.05] hover:bg-red-500/10 border border-white/10 hover:border-red-500/30 text-zinc-400 hover:text-red-400 transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={openAuthModal}
            className="flex items-center gap-2 px-3.5 py-1.5 md:px-4 md:py-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-black font-semibold text-xs md:text-sm hover:brightness-110 shadow-md shadow-amber-500/10 transition-all active:scale-[0.98]"
          >
            <LogIn className="w-4 h-4" />
            <span>Giriş Yap</span>
          </button>
        )}
      </div>
    </header>
  );
};
