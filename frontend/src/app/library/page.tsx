"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowLeft, Star, Film, CheckCircle2, Clock, AlertCircle, Info, LogIn, LogOut, X, ChevronRight } from "lucide-react";
import { BackgroundWall } from "@/components/BackgroundWall";
import { BrandLogo } from "@/components/BrandLogo";
import { ShelfView } from "@/components/shelf/ShelfView";
import { fetchLibraryItems, getLibraryStats, DEMO_USER_ID } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import { LibraryItemDTO, LibraryStats } from "@/types";

export default function LibraryPage() {
  const { user, openAuthModal, logout } = useAuth();
  const [items, setItems] = useState<LibraryItemDTO[]>([]);
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "info" | "error" } | null>(null);

  useEffect(() => {
    if (!isMobileMenuOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [isMobileMenuOpen]);

  const showToast = (message: string, type: "info" | "error" = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const refreshStats = async () => {
    try {
      const s = await getLibraryStats(user?.id);
      setStats(s);
    } catch (e) {
      console.warn("Failed to update stats:", e);
    }
  };

  useEffect(() => {
    async function loadShelf() {
      setIsLoading(true);
      try {
        const [data, statsData] = await Promise.all([
          fetchLibraryItems(user?.id),
          getLibraryStats(user?.id),
        ]);
        setItems(data);
        setStats(statsData);
      } catch (err) {
        console.error("Error loading library items:", err);
        showToast("Raf verileri yüklenirken bir sorun oluştu.", "error");
      } finally {
        setIsLoading(false);
      }
    }
    loadShelf();
  }, [user?.id]);

  const handleItemUpdated = (updatedItem: LibraryItemDTO) => {
    setItems((prev) =>
      prev.map((i) => (i.id === updatedItem.id ? updatedItem : i))
    );
    refreshStats();
    showToast(`"${updatedItem.title}" güncellendi! ✨`);
  };

  const handleItemDeleted = (itemId: string) => {
    setItems((prev) => prev.filter((i) => i.id !== itemId));
    refreshStats();
    showToast("Yapım rafından kaldırıldı.");
  };

  // Stats
  const favoriteCount = items.filter((i) => i.is_favorite).length;
  const completedCount = items.filter((i) => i.status === "COMPLETED").length;
  const watchingCount = items.filter((i) => i.status === "WATCHING").length;

  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-x-hidden bg-[#0a0a0c]">
      {/* Background wallpaper with subtle dimming */}
      <BackgroundWall />

      {/* Top Navbar */}
      <header className="fixed top-0 left-0 right-0 z-40 px-4 md:px-8 py-3.5 md:py-4 flex items-center justify-between pointer-events-auto backdrop-blur-md bg-[#0a0a0c]/70 border-b border-white/[0.04]">
        <Link
          href="/"
          onClick={() => setIsMobileMenuOpen(false)}
          className="flex items-center gap-2.5 group cursor-pointer focus:outline-none"
        >
          <BrandLogo />
          <div className="flex flex-col text-left">
            <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-400 transition-colors">
              Shelflick
            </span>
            <span className="text-[10px] text-neutral-400 font-medium -mt-1 tracking-wider uppercase">
              Kişisel Rafım & Koleksiyonum
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

        {/* Desktop Only Actions */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-2 px-3.5 py-1.5 md:px-4 md:py-2 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/10 hover:border-indigo-500/40 text-neutral-200 hover:text-white transition-all text-xs md:text-sm font-medium shadow-sm group"
          >
            <ArrowLeft className="w-4 h-4 text-indigo-400 group-hover:-translate-x-1 transition-transform" />
            <span>Keşfe Dön</span>
          </Link>

          {user ? (
            <div className="flex items-center gap-2">
              <div
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-neutral-900/80 border border-white/10 text-neutral-200 text-xs font-medium"
                title={user.email}
              >
                <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-amber-500 to-indigo-600 flex items-center justify-center text-white text-[11px] font-bold">
                  {user.name ? user.name.trim().charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
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

      {/* Mobile Drawer (Only visible on < md) */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <div className="fixed inset-0 z-50 md:hidden">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.25 }}
              onClick={() => setIsMobileMenuOpen(false)}
              className="fixed inset-0 bg-black/75 backdrop-blur-md"
            />

            <motion.aside
              initial={{ x: "100%", opacity: 0.6 }}
              animate={{ x: 0, opacity: 1 }}
              exit={{ x: "100%", opacity: 0.6 }}
              transition={{ type: "spring", stiffness: 320, damping: 32 }}
              className="fixed top-0 right-0 bottom-0 w-[85%] max-w-[340px] bg-[#0b0b10]/95 border-l border-white/10 backdrop-blur-2xl shadow-[0_0_50px_rgba(0,0,0,0.9)] flex flex-col justify-between overflow-hidden z-10"
            >
              <div className="pointer-events-none absolute -top-20 -right-20 w-56 h-56 rounded-full bg-indigo-600/20 blur-3xl" />
              <div className="pointer-events-none absolute bottom-10 -left-20 w-48 h-48 rounded-full bg-purple-600/15 blur-3xl" />

              {/* Drawer Header */}
              <div className="relative z-10 px-5 py-4 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                  <BrandLogo />
                  <div className="flex flex-col">
                    <span className="text-base font-bold text-white tracking-tight">
                      Shelflick
                    </span>
                    <span className="text-[9px] text-indigo-300/80 font-semibold uppercase tracking-widest -mt-0.5">
                      Kişisel Raf Menüsü
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

              {/* Drawer Body */}
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
                {/* User Auth Card */}
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
                          {user.name ? user.name.trim().charAt(0).toUpperCase() : user.email.charAt(0).toUpperCase()}
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
                        İzleme listeni her cihazdan yönetmek için giriş yap.
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

                {/* Back to Discovery Navigation Card */}
                <motion.div
                  variants={{
                    hidden: { opacity: 0, y: 12 },
                    visible: { opacity: 1, y: 0 },
                  }}
                >
                  <Link
                    href="/"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className="flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-indigo-600/20 via-purple-600/15 to-indigo-600/10 hover:from-indigo-600/30 hover:to-purple-600/25 border border-indigo-500/30 text-white transition-all group shadow-lg shadow-indigo-950/30"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-indigo-500/25 border border-indigo-400/30 flex items-center justify-center text-indigo-300 group-hover:-translate-x-0.5 transition-transform">
                        <ArrowLeft className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="text-sm font-bold text-white">
                          <span>Keşfe Dön</span>
                        </div>
                        <p className="text-[11px] text-indigo-200/70">
                          Yapay Zeka Öneri Motoru
                        </p>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-indigo-300" />
                  </Link>
                </motion.div>
              </motion.div>

              {/* Drawer Footer */}
              <div className="relative z-10 px-5 py-3.5 border-t border-white/10 bg-black/40 text-center">
                <p className="text-[10px] text-neutral-500 font-medium">
                  Shelflick &bull; Kişisel Medya Koleksiyonu
                </p>
              </div>
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      {/* Floating Toast Notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.95 }}
            className={`fixed top-20 z-50 px-4 py-2.5 rounded-2xl glass-panel shadow-2xl flex items-center gap-2.5 text-xs md:text-sm font-medium border ${
              toast.type === "error"
                ? "border-red-500/30 text-red-200 bg-red-950/40"
                : "border-indigo-500/30 text-indigo-200 bg-indigo-950/40"
            }`}
          >
            {toast.type === "error" ? (
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-indigo-400 flex-shrink-0" />
            )}
            <span>{toast.message}</span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Container */}
      <div className="relative z-10 flex-1 flex flex-col items-center px-4 pt-28 pb-12 w-full max-w-7xl mx-auto">
        {/* Header Hero Title & Stats Banner */}
        <div className="w-full max-w-5xl mb-8 flex flex-col md:flex-row md:items-end justify-between gap-6 border-b border-white/10 pb-6">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-400/20 text-amber-300 text-xs font-medium mb-2.5">
              <Sparkles className="w-3.5 h-3.5 fill-amber-300" />
              <span>Dikey Kutu Kütüphanesi & Vitrin</span>
            </div>
            <h1 className="text-3xl md:text-5xl font-black text-white tracking-tight">
              Kişisel Medya Rafım
            </h1>
            <p className="text-neutral-400 text-xs md:text-sm mt-1.5 max-w-md">
              Kutuların üzerine gelerek orijinal afişleri açığa çıkarabilir, tıklayarak puan ve notlarını güncelleyebilirsin kanka.
            </p>
          </div>

          {/* Quick Stats Badges */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Watch Time Summary Counter Badge */}
            {stats && stats.total_watch_time_minutes > 0 && (
              <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-2xl bg-gradient-to-r from-amber-500/15 via-yellow-500/10 to-amber-600/15 border border-amber-400/40 text-amber-200 shadow-[0_0_15px_rgba(245,158,11,0.15)] backdrop-blur-md">
                <Clock className="w-4 h-4 text-amber-300 animate-pulse flex-shrink-0" />
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <span className="text-neutral-400 font-normal hidden sm:inline">Toplam Ekran Süresi:</span>
                  <span className="font-extrabold text-white font-mono">
                    {stats.total_watch_time_formatted.days > 0 && `${stats.total_watch_time_formatted.days} Gün `}
                    {`${stats.total_watch_time_formatted.hours} Saat`}
                    {stats.total_watch_time_formatted.days === 0 && ` ${stats.total_watch_time_formatted.minutes} Dk`}
                  </span>
                  <span className="text-amber-400/60">•</span>
                  <span className="text-amber-300 font-bold">
                    {stats.total_episodes_watched} Bölüm
                  </span>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-white/[0.04] border border-white/10 text-xs font-medium">
              <Film className="w-4 h-4 text-indigo-400" />
              <span className="text-neutral-400">Toplam:</span>
              <span className="text-white font-bold">{items.length}</span>
            </div>

            <div className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-amber-500/10 border border-amber-400/30 text-xs font-medium text-amber-300">
              <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
              <span>Altın Kutu:</span>
              <span className="font-extrabold text-amber-200">{favoriteCount}</span>
            </div>

            <div className="flex items-center gap-2 px-3.5 py-2 rounded-2xl bg-emerald-500/10 border border-emerald-400/20 text-xs font-medium text-emerald-300">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>İzlendi:</span>
              <span className="font-bold text-white">{completedCount}</span>
            </div>
          </div>
        </div>

        {/* Shelf Content / Skeleton */}
        {isLoading ? (
          <div className="w-full max-w-5xl py-12 flex flex-col items-center justify-center gap-4">
            <div className="w-10 h-10 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-neutral-400 font-mono">Rafındaki kutular diziliyor...</p>
          </div>
        ) : (
          <ShelfView
            items={items}
            onItemUpdated={handleItemUpdated}
            onItemDeleted={handleItemDeleted}
          />
        )}
      </div>

      {/* Footer */}
      <footer className="relative z-10 py-6 text-center text-xs text-neutral-400 border-t border-white/5 select-none pointer-events-none">
        <p>Shelflick &copy; 2026 — Dikey Kutu Koleksiyon Vitrini</p>
      </footer>
    </main>
  );
}
