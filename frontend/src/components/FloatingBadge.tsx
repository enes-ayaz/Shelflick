"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ThumbsUp, Clock, ThumbsDown, X, Sparkles, Check } from "lucide-react";
import { sendUserFeedback } from "@/services/api";

interface FloatingBadgeProps {
  mediaTitle?: string | null;
  mediaId?: string | null;
  onAction?: (action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS") => void;
}

export const FloatingBadge: React.FC<FloatingBadgeProps> = ({
  mediaTitle,
  mediaId,
  onAction,
}) => {
  const [isVisible, setIsVisible] = useState(true);
  const [feedbackGiven, setFeedbackGiven] = useState<string | null>(null);

  if (!mediaTitle || !isVisible) {
    return null;
  }

  const handleAction = async (action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS") => {
    if (action === "DISMISS") {
      setIsVisible(false);
      onAction?.(action);
      return;
    }

    const labels: Record<string, string> = {
      LIKE: "Beğendin! Altın Kutu'ya eklendi ✨",
      WATCHING: "Devam ediyorsun, iyi seyirler ⏳",
      DISLIKE: "Kırmızı Liste'ye not alındı 👎",
    };

    setFeedbackGiven(labels[action] || "Kaydedildi");
    if (mediaId) {
      await sendUserFeedback(mediaId, action);
    }
    onAction?.(action);

    // Auto-close after 1.8 seconds with smooth exit
    setTimeout(() => {
      setIsVisible(false);
    }, 1800);
  };

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -15, scale: 0.9, transition: { duration: 0.25 } }}
          className="flex items-center gap-2 px-3.5 py-1.5 rounded-full glass-panel border border-indigo-500/30 text-white shadow-lg text-xs md:text-sm select-none"
        >
          {feedbackGiven ? (
            <motion.div
              initial={{ opacity: 0, x: 5 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-1.5 text-indigo-300 font-medium py-0.5 px-2"
            >
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>{feedbackGiven}</span>
            </motion.div>
          ) : (
            <>
              {/* Question Label */}
              <div className="flex items-center gap-1.5 text-neutral-300 pr-1">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="font-semibold text-white">{mediaTitle}</span>
                <span className="hidden sm:inline text-neutral-400">nasıl gidiyor?</span>
              </div>

              {/* Action Buttons: [👍] [⏳] [👎] [✕] */}
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => handleAction("LIKE")}
                  className="p-1.5 rounded-full hover:bg-emerald-500/20 text-neutral-400 hover:text-emerald-400 transition-colors"
                  title="Harika gidiyor! (Beğen)"
                >
                  <ThumbsUp className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => handleAction("WATCHING")}
                  className="p-1.5 rounded-full hover:bg-amber-500/20 text-neutral-400 hover:text-amber-400 transition-colors"
                  title="İzlemeye devam ediyorum"
                >
                  <Clock className="w-3.5 h-3.5" />
                </button>

                <button
                  type="button"
                  onClick={() => handleAction("DISLIKE")}
                  className="p-1.5 rounded-full hover:bg-red-500/20 text-neutral-400 hover:text-red-400 transition-colors"
                  title="Sarmadı / Terk ettim"
                >
                  <ThumbsDown className="w-3.5 h-3.5" />
                </button>

                <div className="w-[1px] h-3 bg-white/10 mx-0.5" />

                <button
                  type="button"
                  onClick={() => handleAction("DISMISS")}
                  className="p-1.5 rounded-full hover:bg-white/10 text-neutral-400 hover:text-neutral-200 transition-colors"
                  title="Kapat"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
};
