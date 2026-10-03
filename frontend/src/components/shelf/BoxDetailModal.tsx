"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Star,
  Sparkles,
  Trash2,
  Save,
  CheckCircle2,
  PlayCircle,
  Clock,
  XCircle,
  MessageSquare,
  AlertTriangle,
} from "lucide-react";
import { LibraryItemDTO, WatchStatus, UnifiedMediaDTO } from "@/types";
import { addToLibrary, deleteLibraryItem, formatPosterUrl, DEMO_USER_ID } from "@/services/api";
import { useSoundEffects } from "@/hooks/useSoundEffects";
import { useAuth } from "@/context/AuthContext";

interface BoxDetailModalProps {
  item: LibraryItemDTO | null;
  isOpen: boolean;
  onClose: () => void;
  onItemUpdated: (updatedItem: LibraryItemDTO) => void;
  onItemDeleted: (itemId: string) => void;
}

const STATUS_OPTIONS: { id: WatchStatus; label: string; icon: React.ReactNode; color: string }[] = [
  {
    id: "COMPLETED",
    label: "İzlendi / Tamamlandı",
    icon: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
    color: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300",
  },
  {
    id: "WATCHING",
    label: "Şu An İzleniyor",
    icon: <PlayCircle className="w-4 h-4 text-blue-400" />,
    color: "border-blue-500/40 bg-blue-500/10 text-blue-300",
  },
  {
    id: "PLAN_TO_WATCH",
    label: "İzlenecek (Rafımda)",
    icon: <Clock className="w-4 h-4 text-amber-400" />,
    color: "border-amber-500/40 bg-amber-500/10 text-amber-300",
  },
  {
    id: "DROPPED",
    label: "Yarıda Bırakıldı",
    icon: <XCircle className="w-4 h-4 text-red-400" />,
    color: "border-red-500/40 bg-red-500/10 text-red-300",
  },
];

export const BoxDetailModal: React.FC<BoxDetailModalProps> = ({
  item,
  isOpen,
  onClose,
  onItemUpdated,
  onItemDeleted,
}) => {
  const { user } = useAuth();
  const { playChime, playThud } = useSoundEffects();
  const [status, setStatus] = useState<WatchStatus>("PLAN_TO_WATCH");
  const [isFavorite, setIsFavorite] = useState(false);
  const [userScore, setUserScore] = useState<number>(8.0);
  const [notes, setNotes] = useState("");
  const [dropReason, setDropReason] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Sync internal state when item changes
  useEffect(() => {
    if (item) {
      setStatus(item.status);
      setIsFavorite(item.is_favorite);
      setUserScore(item.user_score || item.base_score || 7.5);
      setNotes(item.personal_notes || "");
      setDropReason(item.drop_reason || "");
    }
  }, [item]);

  if (!isOpen || !item) return null;

  const currentUserId = user?.id || DEMO_USER_ID;

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const mediaPayload: UnifiedMediaDTO = {
        external_id: item.external_id,
        source: item.source as any,
        title: item.title,
        original_title: item.original_title,
        release_year: item.release_year,
        poster_url: item.poster_url,
        synopsis: "",
        genres: item.genres,
        themes: item.themes,
        base_score: item.base_score,
        vote_count: 0,
      };

      const updated = await addToLibrary({
        user_id: currentUserId,
        media: mediaPayload,
        status: status,
        is_favorite: isFavorite,
        user_score: userScore,
        personal_notes: notes.trim() || undefined,
        drop_reason: status === "DROPPED" ? dropReason.trim() || "Zaman kaybı / Beklentiyi karşılamadı" : undefined,
      });

      if (updated) {
        onItemUpdated(updated);
        onClose();
      }
    } catch (err) {
      console.error("Save error:", err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm(`"${item.title}" yapımını rafından silmek istediğine emin misin?`)) {
      return;
    }
    setIsDeleting(true);
    try {
      const ok = await deleteLibraryItem(item.id, currentUserId);
      if (ok) {
        onItemDeleted(item.id);
        onClose();
      } else {
        alert("Silme işlemi başarısız oldu. Sunucu bağlantısını kontrol edin.");
      }
    } catch (err) {
      console.error("Delete error:", err);
      alert("Silme işlemi sırasında bir hata oluştu.");
    } finally {
      setIsDeleting(false);
    }
  };

  const posterUrl = formatPosterUrl(item.poster_url);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-black/80 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 20 }}
          transition={{ type: "spring", stiffness: 350, damping: 28 }}
          className="relative w-full max-w-2xl bg-neutral-900 border border-white/15 rounded-3xl shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]"
        >
          {/* Top Header Bar */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-black/40">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
              <h3 className="text-base font-bold text-white tracking-wide">Kutu & Koleksiyon Düzenle</h3>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-neutral-400 hover:text-white transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Modal Body */}
          <div className="p-6 space-y-6 overflow-y-auto custom-scrollbar">
            {/* 1. Media Preview Hero */}
            <div className="flex gap-4 sm:gap-6 items-start">
              <div className="relative w-24 sm:w-28 flex-shrink-0 aspect-[2/3] rounded-2xl overflow-hidden shadow-lg border border-white/10">
                <img
                  src={posterUrl}
                  alt={item.title}
                  onError={(e) => {
                    (e.currentTarget as HTMLImageElement).src =
                      "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=500";
                  }}
                  className="w-full h-full object-cover"
                />
                {isFavorite && (
                  <div className="absolute top-1 right-1 p-1 rounded-full bg-amber-400 text-neutral-950 shadow-md">
                    <Sparkles className="w-3 h-3 fill-neutral-950" />
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="px-2 py-0.5 rounded-md bg-white/10 text-[10px] font-semibold text-neutral-300">
                    {item.source === "ANILIST" ? "Anime" : item.source === "TMDB_SERIES" ? "Dizi" : "Film"}
                  </span>
                  {item.release_year && (
                    <span className="text-xs text-neutral-400">{item.release_year}</span>
                  )}
                </div>

                <h2 className="text-lg sm:text-xl font-black text-white leading-tight mb-1 truncate">
                  {item.title}
                </h2>
                {item.original_title && item.original_title !== item.title && (
                  <p className="text-xs text-neutral-400 italic mb-2 truncate">
                    {item.original_title}
                  </p>
                )}

                {/* Altın Kutu (Favorite) Toggle Button */}
                <button
                  type="button"
                  onClick={() => {
                    const nextFav = !isFavorite;
                    setIsFavorite(nextFav);
                    if (nextFav) {
                      playChime();
                    }
                  }}
                  className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer shadow-md ${
                    isFavorite
                      ? "bg-gradient-to-r from-amber-500 to-yellow-400 text-neutral-950 border border-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.4)]"
                      : "bg-white/5 hover:bg-white/10 text-neutral-300 border border-white/10"
                  }`}
                >
                  <Sparkles className={`w-3.5 h-3.5 ${isFavorite ? "fill-neutral-950" : "text-amber-400"}`} />
                  <span>{isFavorite ? "⭐ Altın Kutu Aktif (Hologramlı)" : "Altın Kutuya Ekle (Favori)"}</span>
                </button>
              </div>
            </div>

            {/* 2. Rating Score (1.0 to 10.0) */}
            <div className="space-y-2 p-4 rounded-2xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                  <span>Kişisel Puanın</span>
                </label>
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-black text-amber-400">{userScore.toFixed(1)}</span>
                  <span className="text-xs text-neutral-400">/ 10</span>
                </div>
              </div>
              <input
                type="range"
                min="1.0"
                max="10.0"
                step="0.5"
                value={userScore}
                onChange={(e) => setUserScore(parseFloat(e.target.value))}
                className="w-full h-2 bg-neutral-800 rounded-lg appearance-none cursor-pointer accent-amber-400"
              />
              <div className="flex justify-between text-[10px] text-neutral-400 font-mono">
                <span>1.0 (Kötü)</span>
                <span>5.0 (Ortalama)</span>
                <span>8.0 (Çok İyi)</span>
                <span>10.0 (Başyapıt)</span>
              </div>
            </div>

            {/* 3. Status Selection Grid */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-neutral-300">
                İzleme Durumu & Efekt
              </label>
              <div className="grid grid-cols-2 gap-2 sm:gap-2.5">
                {STATUS_OPTIONS.map((opt) => {
                  const isSelected = status === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => {
                        setStatus(opt.id);
                        if (opt.id === "DROPPED") {
                          playThud();
                        }
                      }}
                      className={`flex items-center gap-2.5 p-3 rounded-2xl border text-xs font-semibold transition-all cursor-pointer text-left ${
                        isSelected
                          ? `${opt.color} ring-1 ring-white/20 shadow-md`
                          : "border-white/5 bg-white/[0.02] text-neutral-400 hover:bg-white/[0.05]"
                      }`}
                    >
                      {opt.icon}
                      <span className="truncate">{opt.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 4. Drop Reason (shown if status is DROPPED) */}
            <AnimatePresence>
              {status === "DROPPED" && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="space-y-2 p-4 rounded-2xl bg-red-950/20 border border-red-500/30 overflow-hidden"
                >
                  <label className="text-xs font-semibold text-red-300 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                    <span>Bırakma Sebebi (Kırmızı Listeye Not)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="Örn: 4. bölümde çok baydı, klişeler ve yavaş tempo..."
                    value={dropReason}
                    onChange={(e) => setDropReason(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-black/50 border border-red-500/20 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-red-500/60"
                  />
                </motion.div>
              )}
            </AnimatePresence>

            {/* 5. Personal Notes */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                <span>Kişisel Notun & Yorumun</span>
              </label>
              <textarea
                rows={3}
                placeholder="Bu yapım hakkındaki düşüncelerin, hatırlamak istediğin detaylar..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-2xl bg-white/[0.04] border border-white/10 text-xs text-white placeholder-neutral-500 focus:outline-none focus:border-indigo-500/50 resize-none leading-relaxed"
              />
            </div>
          </div>

          {/* Modal Footer Actions */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-white/10 bg-black/40">
            <button
              type="button"
              onClick={handleDelete}
              disabled={isDeleting || isSaving}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-red-950/40 hover:bg-red-900/60 border border-red-500/30 text-red-300 text-xs font-medium transition-colors cursor-pointer disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>{isDeleting ? "Siliniyor..." : "Kaldır"}</span>
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-white/5 hover:bg-white/10 text-neutral-300 text-xs font-medium transition-colors cursor-pointer"
              >
                Vazgeç
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                className="flex items-center gap-1.5 px-5 py-2 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold transition-all shadow-glow cursor-pointer disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{isSaving ? "Kaydediliyor..." : "Kaydet"}</span>
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
};
