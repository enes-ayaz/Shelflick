"use client";

import React, { useState, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronLeft, ChevronRight, Sparkles, BookOpen, Layers } from "lucide-react";
import { LibraryItemDTO } from "@/types";
import { BoxItem } from "./BoxItem";
import { ShelfFilterBar, ShelfFilterType } from "./ShelfFilterBar";
import { BoxDetailModal } from "./BoxDetailModal";

interface ShelfViewProps {
  items: LibraryItemDTO[];
  onItemUpdated: (updatedItem: LibraryItemDTO) => void;
  onItemDeleted: (itemId: string) => void;
}

export const ShelfView: React.FC<ShelfViewProps> = ({
  items,
  onItemUpdated,
  onItemDeleted,
}) => {
  const [filter, setFilter] = useState<ShelfFilterType>("ALL");
  const [selectedItem, setSelectedItem] = useState<LibraryItemDTO | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const shelfScrollRef = useRef<HTMLDivElement>(null);

  // Filter items
  const filteredItems = useMemo(() => {
    return items.filter((item) => {
      if (filter === "ALL") return true;
      if (filter === "FAVORITES") return item.is_favorite;
      return item.status === filter;
    });
  }, [items, filter]);

  // Split filtered items into shelf rows of up to 12 items for realistic bookcase look
  const shelfRows = useMemo(() => {
    if (filteredItems.length === 0) return [];
    const rows: LibraryItemDTO[][] = [];
    const chunkSize = 12;
    for (let i = 0; i < filteredItems.length; i += chunkSize) {
      rows.push(filteredItems.slice(i, i + chunkSize));
    }
    return rows;
  }, [filteredItems]);

  const handleBoxClick = (item: LibraryItemDTO) => {
    setSelectedItem(item);
    setIsModalOpen(true);
  };

  const handleScroll = (direction: "left" | "right") => {
    if (shelfScrollRef.current) {
      const scrollAmount = direction === "left" ? -400 : 400;
      shelfScrollRef.current.scrollBy({ left: scrollAmount, behavior: "smooth" });
    }
  };

  return (
    <div className="w-full flex flex-col items-center select-none pb-20">
      {/* 1. Shelf Filter Bar */}
      <div className="w-full max-w-5xl px-4 mb-8">
        <ShelfFilterBar
          currentFilter={filter}
          onFilterChange={setFilter}
          items={items}
        />
      </div>

      {/* 2. Empty State */}
      {filteredItems.length === 0 && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="w-full max-w-md mx-auto text-center py-16 px-6 glass-panel rounded-3xl border border-white/10"
        >
          <div className="w-14 h-14 mx-auto mb-4 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <BookOpen className="w-7 h-7" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Bu filtrede yapım bulunamadı</h3>
          <p className="text-neutral-400 text-xs leading-relaxed max-w-xs mx-auto">
            {filter === "ALL"
              ? "Rafın henüz bomboş kanka! Ana sayfaya dönüp beğendiğin veya izleyeceğin yapımları rafına dizebilirsin."
              : "Bu kategoride henüz bir kutu yok. Diğer filtreleri inceleyebilir veya yeni yapımlar ekleyebilirsin."}
          </p>
        </motion.div>
      )}

      {/* 3. Bookcase Shelves Display */}
      {shelfRows.length > 0 && (
        <div className="w-full max-w-6xl space-y-16 px-2 sm:px-6">
          {shelfRows.map((row, rowIndex) => (
            <div key={`shelf-row-${rowIndex}`} className="relative flex flex-col">
              {/* Shelf Level Label */}
              <div className="flex items-center justify-between px-3 mb-2">
                <span className="text-xs font-mono font-semibold text-neutral-400 flex items-center gap-1.5 uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                  Raf {rowIndex + 1} ({row.length} Kutu)
                </span>
                <span className="text-[11px] text-neutral-400 hidden md:inline">
                  Genişletmek için fareyi kutunun üzerine getir
                </span>
                <span className="text-[11px] text-indigo-400/80 md:hidden flex items-center gap-1">
                  Dokun: Genişlet • Kaydır: ➔
                </span>
              </div>

              {/* Horizontal Boxes Rail Container (Touch Swipe + Snap-X + Scrollbar-Hide) */}
              <div
                className="relative w-full overflow-x-auto overflow-y-visible px-3 sm:px-4 pt-4 pb-2 scrollbar-hide no-scrollbar flex items-end min-h-[360px] snap-x snap-mandatory touch-pan-x"
                style={{ scrollBehavior: "smooth", WebkitOverflowScrolling: "touch" }}
              >
                <div className="flex items-end gap-3 pb-1 w-max min-w-full">
                  {row.map((item) => (
                    <BoxItem
                      key={item.id}
                      item={item}
                      onClick={handleBoxClick}
                    />
                  ))}
                </div>
              </div>

              {/* Realistic Metallic / Oak Wood Shelf Plank & Reflection Floor */}
              <div className="relative w-full z-10 -mt-1 pointer-events-none">
                {/* 1. Specular top highlight line */}
                <div className="w-full h-[2px] bg-gradient-to-r from-transparent via-amber-200/25 to-transparent" />

                {/* 2. Top wooden/metallic shelf beam */}
                <div className="w-full h-4 bg-gradient-to-b from-[#222126] via-[#161519] to-[#0d0c0f] border-t border-white/20 shadow-[0_8px_16px_rgba(0,0,0,0.8)] rounded-sm" />

                {/* 3. Deep under-shelf drop shadow */}
                <div className="w-full h-6 bg-gradient-to-b from-black/90 via-black/40 to-transparent" />

                {/* 4. Subtle ambient reflection mirror effect */}
                <div className="w-full h-8 opacity-25 bg-gradient-to-b from-indigo-500/10 via-purple-500/5 to-transparent blur-sm -mt-5" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 4. Detail & Rating Modal */}
      <BoxDetailModal
        item={selectedItem}
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedItem(null);
        }}
        onItemUpdated={(updated) => {
          onItemUpdated(updated);
          setSelectedItem(updated);
        }}
        onItemDeleted={(id) => {
          onItemDeleted(id);
          setIsModalOpen(false);
          setSelectedItem(null);
        }}
      />
    </div>
  );
};
