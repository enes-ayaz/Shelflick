"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, ArrowLeft, Star, Film, CheckCircle2, Clock, AlertCircle, Info, LogIn, LogOut } from "lucide-react";
import { BackgroundWall } from "@/components/BackgroundWall";
import { ShelfView } from "@/components/shelf/ShelfView";
import { fetchLibraryItems, DEMO_USER_ID } from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import { LibraryItemDTO } from "@/types";

export default function LibraryPage() {
  const { user, openAuthModal, logout } = useAuth();
  const [items, setItems] = useState<LibraryItemDTO[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [toast, setToast] = useState<{ message: string; type: "info" | "error" } | null>(null);

  const showToast = (message: string, type: "info" | "error" = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  useEffect(() => {
    async function loadShelf() {
      setIsLoading(true);
      try {
        const data = await fetchLibraryItems(user?.id);
        setItems(data);
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
    showToast(`"${updatedItem.title}" güncellendi! ✨`);
  };

  const handleItemDeleted = (itemId: string) => {
    setItems((prev) => prev.filter((i) => i.id !== itemId));
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
      <header className="fixed top-0 left-0 right-0 z-40 px-4 md:px-8 py-4 flex items-center justify-between pointer-events-auto backdrop-blur-md bg-[#0a0a0c]/70 border-b border-white/[0.04]">
        <Link
          href="/"
          className="flex items-center gap-2.5 group cursor-pointer focus:outline-none"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center font-black tracking-tighter text-white text-base shadow-glow group-hover:scale-105 transition-transform duration-300">
            <span className="font-mono tracking-tighter text-sm font-black">||&gt;</span>
          </div>
          <div className="flex flex-col text-left">
            <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-400 transition-colors">
              Shelflick
            </span>
            <span className="text-[10px] text-neutral-400 font-medium -mt-1 tracking-wider uppercase">
              Kişisel Rafım & Koleksiyonum
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-3">
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
