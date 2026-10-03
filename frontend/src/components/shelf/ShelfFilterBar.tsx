"use client";

import React from "react";
import { motion } from "framer-motion";
import { Star, CheckCircle2, PlayCircle, Clock, XCircle, Layers } from "lucide-react";
import { LibraryItemDTO, WatchStatus } from "@/types";

export type ShelfFilterType = "ALL" | "FAVORITES" | WatchStatus;

interface ShelfFilterBarProps {
  currentFilter: ShelfFilterType;
  onFilterChange: (filter: ShelfFilterType) => void;
  items: LibraryItemDTO[];
}

export const ShelfFilterBar: React.FC<ShelfFilterBarProps> = ({
  currentFilter,
  onFilterChange,
  items,
}) => {
  // Count items per filter
  const counts = {
    ALL: items.length,
    FAVORITES: items.filter((i) => i.is_favorite).length,
    WATCHING: items.filter((i) => i.status === "WATCHING").length,
    COMPLETED: items.filter((i) => i.status === "COMPLETED").length,
    PLAN_TO_WATCH: items.filter((i) => i.status === "PLAN_TO_WATCH").length,
    DROPPED: items.filter((i) => i.status === "DROPPED").length,
  };

  const tabs: { id: ShelfFilterType; label: string; icon: React.ReactNode; color: string }[] = [
    {
      id: "ALL",
      label: "Tümü",
      icon: <Layers className="w-3.5 h-3.5" />,
      color: "text-indigo-400",
    },
    {
      id: "FAVORITES",
      label: "Favoriler",
      icon: <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />,
      color: "text-amber-300",
    },
    {
      id: "WATCHING",
      label: "İzleniyor",
      icon: <PlayCircle className="w-3.5 h-3.5 text-blue-400" />,
      color: "text-blue-400",
    },
    {
      id: "COMPLETED",
      label: "İzlendi",
      icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
      color: "text-emerald-400",
    },
    {
      id: "PLAN_TO_WATCH",
      label: "İzlenecek",
      icon: <Clock className="w-3.5 h-3.5 text-amber-400" />,
      color: "text-amber-400",
    },
    {
      id: "DROPPED",
      label: "Bırakılanlar",
      icon: <XCircle className="w-3.5 h-3.5 text-red-400" />,
      color: "text-red-400",
    },
  ];

  return (
    <div className="w-full flex items-center justify-start sm:justify-center overflow-x-auto py-2 no-scrollbar">
      <div className="flex items-center gap-1.5 p-1.5 rounded-2xl bg-neutral-900/80 border border-white/10 backdrop-blur-xl shadow-lg">
        {tabs.map((tab) => {
          const isActive = currentFilter === tab.id;
          const count = counts[tab.id];

          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => onFilterChange(tab.id)}
              className={`relative flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold transition-all duration-200 cursor-pointer select-none whitespace-nowrap ${
                isActive ? "text-white" : "text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.04]"
              }`}
            >
              {/* Active animated sliding background pill */}
              {isActive && (
                <motion.div
                  layoutId="activeFilterTab"
                  className="absolute inset-0 rounded-xl bg-white/[0.12] border border-white/15 shadow-sm"
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}

              <span className="relative z-10 flex items-center gap-1.5">
                {tab.icon}
                <span>{tab.label}</span>
              </span>

              {/* Counter Badge */}
              <span
                className={`relative z-10 px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold transition-colors ${
                  isActive
                    ? "bg-white/20 text-white"
                    : "bg-white/[0.05] text-neutral-400"
                }`}
              >
                {count}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
