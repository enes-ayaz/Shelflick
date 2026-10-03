"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  BookOpen,
  Star,
  Film,
  Tv,
  CheckCircle2,
  Clock,
  Bookmark,
  Calendar,
  Sparkles,
  ExternalLink,
} from "lucide-react";
import { LibraryItemDTO, WatchStatus } from "@/types";
import { formatPosterUrl } from "@/services/api";


interface ShelfDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  items: LibraryItemDTO[];
  isLoading?: boolean;
}

const TABS: { id: "ALL" | WatchStatus; label: string; icon: React.ElementType }[] = [
  { id: "ALL", label: "Tümü", icon: BookOpen },
  { id: "PLAN_TO_WATCH", label: "İzlenecekler", icon: Bookmark },
  { id: "WATCHING", label: "İzleniyor", icon: Clock },
  { id: "COMPLETED", label: "Tamamlananlar", icon: CheckCircle2 },
];

export const ShelfDrawer: React.FC<ShelfDrawerProps> = ({
  isOpen,
  onClose,
  items,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<"ALL" | WatchStatus>("ALL");

  const filteredItems = items.filter((item) => {
    if (activeTab === "ALL") return true;
    return item.status === activeTab;
  });

  const getSourceIcon = (source: string) => {
    if (source === "ANILIST") return <span className="text-[10px] font-bold text-pink-400">ANIME</span>;
    if (source === "TMDB_SERIES") return <Tv className="w-3 h-3 text-emerald-400" />;
    return <Film className="w-3 h-3 text-blue-400" />;
  };

  const getStatusBadge = (status: WatchStatus) => {
    switch (status) {
      case "COMPLETED":
        return <span className="text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded text-[10px] font-medium">İzlendi</span>;
      case "WATCHING":
        return <span className="text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded text-[10px] font-medium">İzleniyor</span>;
      case "PLAN_TO_WATCH":
        return <span className="text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded text-[10px] font-medium">İzlenecek</span>;
      default:
        return null;
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 28, stiffness: 280 }}
            className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-md bg-[#0e0e13]/95 border-l border-white/10 shadow-2xl flex flex-col backdrop-blur-xl"
          >
            {/* Header */}
            <div className="px-6 py-5 border-b border-white/10 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                  <BookOpen className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
                    Kişisel Rafım
                    <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-neutral-300 font-semibold">
                      {items.length}
                    </span>
                  </h3>
                  <p className="text-[11px] text-neutral-400">Kaydettiğin ve izlediğin yapımlar</p>
                </div>
              </div>

              <button
                type="button"
                onClick={onClose}
                className="p-2 rounded-xl text-neutral-400 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Filter Tabs */}
            <div className="px-6 py-3 border-b border-white/5 flex gap-1.5 overflow-x-auto no-scrollbar">
              {TABS.map((tab) => {
                const count = tab.id === "ALL" ? items.length : items.filter((i) => i.status === tab.id).length;
                const Icon = tab.icon;
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-all whitespace-nowrap ${
                      isActive
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/20"
                        : "bg-white/[0.03] text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.08]"
                    }`}
                  >
                    <Icon className="w-3 h-3" />
                    <span>{tab.label}</span>
                    <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${isActive ? "bg-white/20 text-white" : "bg-white/5 text-neutral-400"}`}>
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Items List */}
            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
              {isLoading ? (
                <div className="flex flex-col items-center justify-center h-48 text-neutral-400 text-sm gap-2">
                  <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                  <span>Raf yükleniyor...</span>
                </div>
              ) : filteredItems.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 text-center px-4">
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.03] border border-white/10 flex items-center justify-center text-neutral-400 mb-3">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <h4 className="text-sm font-semibold text-white">Bu kategoride yapım yok</h4>
                  <p className="text-xs text-neutral-400 mt-1 max-w-xs">
                    Öneri kartlarındaki "Listeme Ekle" butonuna basarak rafını zenginleştirebilirsin.
                  </p>
                </div>
              ) : (
                filteredItems.map((item) => (
                  <div
                    key={item.id}
                    className="flex gap-3.5 p-3 rounded-2xl bg-white/[0.03] border border-white/5 hover:border-white/10 hover:bg-white/[0.05] transition-all group"
                  >
                    {/* Poster Thumbnail */}
                    <div className="w-14 h-20 rounded-xl overflow-hidden bg-neutral-900 flex-shrink-0 border border-white/10 relative">
                      <img
                        src={formatPosterUrl(item.poster_url)}
                        alt={item.title}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      />
                    </div>


                    {/* Metadata */}
                    <div className="flex-1 min-w-0 flex flex-col justify-between py-0.5">
                      <div>
                        <div className="flex items-start justify-between gap-1">
                          <h4 className="text-sm font-semibold text-white truncate leading-snug">
                            {item.title}
                          </h4>
                          {item.base_score > 0 && (
                            <div className="flex items-center gap-1 text-amber-400 text-xs font-bold flex-shrink-0">
                              <Star className="w-3 h-3 fill-amber-400" />
                              <span>{item.base_score.toFixed(1)}</span>
                            </div>
                          )}
                        </div>

                        <div className="flex items-center gap-2 mt-1 text-[11px] text-neutral-400">
                          <div className="flex items-center gap-1">
                            {getSourceIcon(item.source)}
                          </div>
                          {item.release_year && (
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {item.release_year}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="flex items-center justify-between gap-2 mt-2">
                        {getStatusBadge(item.status)}
                        {item.genres && item.genres.length > 0 && (
                          <span className="text-[10px] text-neutral-400 truncate max-w-[150px]">
                            {item.genres.slice(0, 2).join(", ")}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 bg-black/40 text-center">
              <p className="text-[11px] text-neutral-400">
                Kaydedilen yapımlar "Şansıma Güveniyorum" havuzundan otomatik filtrelenir.
              </p>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
