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
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isMobileRadarExpanded, setIsMobileRadarExpanded] = useState(false);
  const radarRef = useRef<HTMLDivElement>(null);

  // Lock body scroll when mobile drawer is open
  useEffect(() => {
    if (!isMobileMenuOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [isMobileMenuOpen]);

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
    <>
      <header className="fixed top-0 left-0 right-0 z-40 px-4 md:px-8 py-3.5 md:py-4 flex items-center justify-between pointer-events-auto backdrop-blur-md bg-[#0a0a0c]/60 border-b border-white/[0.04]">
        {/* Top-Left: Shelflick Logo (||> icon + typography) */}
        <Link
          href="/"
          onClick={() => {
            setIsMobileMenuOpen(false);
            onReset();
          }}
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

        {/* Mobile Only: Animated 3-Line Hamburger Trigger */}
        <button
          type="button"
          onClick={() => setIsMobileMenuOpen((prev) => !prev)}
          aria-label={isMobileMenuOpen ? "Menüyü Kapat" : "Menüyü Aç"}
          aria-expanded={isMobileMenuOpen}
          className="relative flex md:hidden items-center justify-center w-10 h-10 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 active:scale-95 transition-all cursor-pointer"
        >
          {/* Notification Dot if Radar has items */}
          {!isMobileMenuOpen && radarItems.length > 0 && (
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.9)] animate-pulse" />
          )}

          <div className="w-5 h-4 flex flex-col justify-between items-center relative">
            <motion.span
              animate={
                isMobileMenuOpen
                  ? { rotate: 45, y: 7, backgroundColor: "#a78bfa" }
                  : { rotate: 0, y: 0, backgroundColor: "#f5f5f5" }
              }
              transition={{ type: "spring", stiffness: 360, damping: 26 }}
              className="w-5 h-[2px] rounded-full block origin-center"
            />
            <motion.span
              animate={
                isMobileMenuOpen
                  ? { opacity: 0, x: 10, scaleX: 0.4 }
                  : { opacity: 1, x: 0, scaleX: 1 }
              }
              transition={{ duration: 0.2 }}
              className="w-3.5 h-[2px] bg-indigo-400 rounded-full block self-end"
            />
            <motion.span
              animate={
                isMobileMenuOpen
                  ? { rotate: -45, y: -7, backgroundColor: "#a78bfa" }
                  : { rotate: 0, y: 0, backgroundColor: "#f5f5f5" }
              }
              transition={{ type: "spring", stiffness: 360, damping: 26 }}
              className="w-5 h-[2px] rounded-full block origin-center"
            />
          </div>
        </button>

        {/* Desktop Only Top-Right: Radar, Rafım Button, Feedback, and User Auth / Profile */}
        <div className="hidden md:flex items-center gap-2 md:gap-3">
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

      {/* Mobile Navigation & Action Drawer (Only visible on < md) */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-50 md:hidden">
            {/* Blurred Dark Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setIsMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/75 backdrop-blur-md"
            />

            {/* Sliding Glassmorphism Drawer Panel */}
            <motion.aside
              initial={{ x: "100%", opacity: 0.6 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0.6 }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              className="fixed top-0 right-0 bottom-0 w-[85%] max-w-[340px] bg-[#0b0b10]/95 border-l border-white/10 backdrop-blur-2xl shadow-[0_0_50px_rgba(0,0,0,0.9)] flex flex-col justify-between overflow-hidden z-10"
            >
              {/* Ambient Decorative Glows */}
              <div className="pointer-events-none absolute -top-20 -right-20 w-56 h-56 rounded-full bg-indigo-600/20 blur-3xl" />
              <div className="pointer-events-none absolute bottom-10 -left-20 w-48 h-48 rounded-full bg-purple-600/15 blur-3xl" />

              {/* Drawer Top Header */}
              <div className="relative z-10 px-5 py-4 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <BrandLogo />
                  <div className="flex flex-col">
                    <span className="text-base font-bold text-white tracking-tight">
                      Shelflick
                    </span>
                    <span className="text-[9px] text-indigo-300/80 font-semibold uppercase tracking-widest -mt-0.5">
                      Hızlı Erişim Menüsü
                    </span>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsMobileMenuOpen(false)}
                  aria-label="Menüyü Kapat"
                  className="p-2 rounded-xl bg-white/[0.05] hover:bg-white/10 border border-white/10 text-neutral-400 hover:text-white transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Drawer Body with Staggered Animated Items */}
              <motion.div
                initial="hidden"
                animate="visible"
                variants={{
                  hidden: { opacity: 0 },
                  visible: {
                    opacity: 1,
                    transition: { staggerChildren: 0.06, delayChildren: 0.05 },
                  },
                }}
                className="relative z-10 flex-1 overflow-y-auto px-5 py-5 space-y-4 custom-scrollbar"
              >
                {/* 1. User Profile / Auth Card */}
                <motion.div
                  variants={{
                    hidden: { opacity: 0, y: 12 },
                    visible: { opacity: 1, y: 0 },
                  }}
                >
                  {user ? (
                    <div className="p-3.5 rounded-2xl bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-white text-sm font-black shadow-md flex-shrink-0">
                          {userInitial}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-white truncate">
                            {user.name || user.email.split("@")[0]}
                          </p>
                          <p className="text-[11px] text-neutral-400 truncate">
                            {user.email}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setIsMobileMenuOpen(false);
                          logout();
                        }}
                        title="Çıkış Yap"
                        className="p-2.5 rounded-xl bg-red-500/10 hover:bg-red-500/20 border border-red-500/25 text-red-400 transition-colors flex-shrink-0"
                      >
                        <LogOut className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-500/10 via-indigo-500/5 to-transparent border border-amber-500/25 space-y-3">
                      <div className="flex items-center gap-2 text-amber-300 text-xs font-semibold">
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>Kişisel Rafını Senkronize Et</span>
                      </div>
                      <p className="text-[11px] text-neutral-400 leading-relaxed">
                        İzleme listeni ve yapay zeka zevk profilini kaydetmek için hesabına giriş yap.
                      </p>
                      <button
                        type="button"
                        onClick={() => {
                          setIsMobileMenuOpen(false);
                          openAuthModal();
                        }}
                        className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 text-black font-bold text-xs shadow-lg shadow-amber-500/15 active:scale-[0.98] transition-all"
                      >
                        <LogIn className="w-4 h-4" />
                        <span>Giriş Yap / Kayıt Ol</span>
                      </button>
                    </div>
                  )}
                </motion.div>

                {/* 2. [ 📚 Rafım ] Primary Navigation Card */}
                <motion.div
                  variants={{
                    hidden: { opacity: 0, y: 12 },
                    visible: { opacity: 1, y: 0 },
                  }}
                >
                  <Link
                    href="/library"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-indigo-600/20 via-purple-600/15 to-indigo-600/10 hover:from-indigo-600/30 hover:to-purple-600/25 border border-indigo-500/30 text-white transition-all group shadow-lg shadow-indigo-950/30"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/25 border border-indigo-400/30 flex items-center justify-center text-indigo-300 group-hover:scale-105 transition-transform">
                        <BookOpen className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white flex items-center gap-2">
                          <span>Kişisel Rafım</span>
                        </div>
                        <p className="text-[11px] text-indigo-200/70">
                          3D Koleksiyon & İzleme Listesi
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2.5 py-1 rounded-full bg-indigo-600 border border-indigo-400/40 text-white text-xs font-black shadow-sm">
                        {shelfCount}
                      </span>
                      <ChevronRight className="w-4 h-4 text-indigo-300 group-hover:translate-x-0.5 transition-transform" />
                    </div>
                  </Link>
                </motion.div>

                {/* 3. [ 📡 Sezon & Bölüm Radarı ] Expandable Section */}
                <motion.div
                  variants={{
                    hidden: { opacity: 0, y: 12 },
                    visible: { opacity: 1, y: 0 },
                  }}
                  className="rounded-2xl bg-white/[0.03] border border-white/10 overflow-hidden"
                >
                  <button
                    type="button"
                    onClick={() => setIsMobileRadarExpanded((prev) => !prev)}
                    className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.03] transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-400/30 flex items-center justify-center text-amber-400">
                        <Radar className={`w-5 h-5 ${radarItems.length > 0 ? "animate-pulse" : ""}`} />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white flex items-center gap-2">
                          <span>Sezon & Bölüm Radarı</span>
                        </div>
                        <p className="text-[11px] text-neutral-400">
                          Takip ettiğin yapımlardan haberler
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-0.5 rounded-full bg-amber-500/20 border border-amber-400/30 text-amber-300 text-xs font-black">
                        {radarItems.length}
                      </span>
                      <ChevronRight
                        className={`w-4 h-4 text-neutral-400 transition-transform duration-200 ${
                          isMobileRadarExpanded ? "rotate-90 text-amber-300" : ""
                        }`}
                      />
                    </div>
                  </button>

                  <AnimatePresence initial={false}>
                    {isMobileRadarExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.22 }}
                        className="overflow-hidden border-t border-white/10 bg-black/30"
                      >
                        <div className="p-3 space-y-2 max-h-60 overflow-y-auto custom-scrollbar">
                          {radarItems.length === 0 ? (
                            <div className="py-5 text-center text-xs text-neutral-400 space-y-1">
                              <p>📡 Radarda bekleyen yeni bölüm yok.</p>
                              <p className="text-[10px] text-neutral-500">
                                Rafına devam eden diziler ekledikçe burada görünür.
                              </p>
                            </div>
                          ) : (
                            radarItems.map((item) => {
                              const radarInfo = formatRadarInfo(item);
                              return (
                                <div
                                  key={item.id}
                                  className="flex items-center gap-2.5 p-2 rounded-xl bg-white/[0.03] border border-white/5"
                                >
                                  <img
                                    src={formatPosterUrl(item.poster_url)}
                                    alt={item.title}
                                    className="w-10 h-14 rounded-lg object-cover flex-shrink-0 border border-white/10"
                                  />
                                  <div className="flex-1 min-w-0">
                                    <h5 className="text-xs font-bold text-white truncate">
                                      {item.title}
                                    </h5>
                                    <div className="mt-1 flex items-center justify-between text-[11px]">
                                      <span
                                        className={
                                          radarInfo.isSoon
                                            ? "text-amber-300 font-bold"
                                            : "text-neutral-300 font-medium"
                                        }
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
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>

                {/* 4. Active Watching Feedback (if user is currently watching something) */}
                {activeWatchingItem && (
                  <motion.div
                    variants={{
                      hidden: { opacity: 0, y: 12 },
                      visible: { opacity: 1, y: 0 },
                    }}
                    className="pt-1"
                  >
                    <FloatingBadge
                      mediaTitle={activeWatchingItem.title}
                      mediaId={activeWatchingItem.external_id || activeWatchingItem.id}
                      onAction={onWatchingFeedback}
                    />
                  </motion.div>
                )}
              </motion.div>

              {/* Drawer Footer */}
              <div className="relative z-10 px-5 py-3.5 border-t border-white/10 bg-black/40 text-center">
                <p className="text-[10px] text-neutral-500 font-medium">
                  Shelflick &bull; MediaPulse Engine
                </p>
              </div>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};
