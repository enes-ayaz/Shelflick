"use client";

import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { BackgroundWall } from "@/components/BackgroundWall";
import { Omnibar } from "@/components/Omnibar";
import { SuggestionCard } from "@/components/SuggestionCard";
import { Header } from "@/components/Header";
import { ShelfDrawer } from "@/components/ShelfDrawer";
import {
  fetchRandomMasterpiece,
  fetchRecommendation,
  fetchLibraryItems,
  addToLibrary,
  DEMO_USER_ID,
} from "@/services/api";
import { useAuth } from "@/context/AuthContext";
import {
  MediaTypeFilter,
  RecommendationResponse,
  UnifiedMediaDTO,
  LibraryItemDTO,
  LiveSearchResultItem,
} from "@/types";
import { Sparkles, AlertCircle, Info } from "lucide-react";

const SUGGESTED_PROMPTS = [
  "Shounen klişesi içermeyen karanlık anime",
  "David Fincher tarzı soğuk suç gerilimi",
  "Zaman paradoksu ve beyin yakan filmler",
  "Cozy, nostaljik 90'lar animesi",
];

export default function Home() {
  const { user } = useAuth();
  const [recommendation, setRecommendation] = useState<RecommendationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "info" | "error" } | null>(null);

  // Library & Shelf State
  const [libraryItems, setLibraryItems] = useState<LibraryItemDTO[]>([]);
  const [isShelfOpen, setIsShelfOpen] = useState(false);
  const [isShelfLoading, setIsShelfLoading] = useState(false);

  // Load existing user shelf on mount or when user changes
  useEffect(() => {
    async function loadShelf() {
      setIsShelfLoading(true);
      try {
        const items = await fetchLibraryItems(user?.id);
        setLibraryItems(items);
      } catch (err) {
        console.error("Could not fetch user shelf items:", err);
      } finally {
        setIsShelfLoading(false);
      }
    }
    loadShelf();
  }, [user?.id]);

  const showToast = (message: string, type: "info" | "error" = "info") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4500);
  };

  const handleSearch = async (query: string, filter: MediaTypeFilter) => {
    setIsLoading(true);
    setRecommendation(null);
    try {
      const formattedPrompt = filter !== "ALL" ? `[${filter}] ${query}` : query;
      const res = await fetchRecommendation({
        prompt: formattedPrompt,
        limit: 10,
        user_id: user?.id,
      });
      setRecommendation(res);
    } catch (error) {
      console.error("Failed to fetch recommendation:", error);
      showToast("Sunucuya bağlanırken bir sorun oluştu, yedek öneri getiriliyor.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleRandom = async (filter?: MediaTypeFilter) => {
    setIsLoading(true);
    setRecommendation(null);
    try {
      const mediaTypeParam = filter && filter !== "ALL" ? filter.toLowerCase() : undefined;
      const res = await fetchRandomMasterpiece(user?.id, mediaTypeParam);
      setRecommendation(res);
    } catch (error) {
      console.error("Failed to fetch random recommendation:", error);
      showToast("Şanslı öneri getirilirken hata oluştu.", "error");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDismiss = () => {
    setRecommendation(null);
  };

  const handleReset = () => {
    setRecommendation(null);
    setIsShelfOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  /** Called when user clicks a poster on the background wall */
  const handlePosterClick = (query: string, _title: string) => {
    handleSearch(query, "ALL");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Add to library and update state in real-time
  const handleAddToList = async (media: UnifiedMediaDTO) => {
    const isAlreadyPresent = libraryItems.some((i) => i.external_id === media.external_id);
    const result = await addToLibrary({
      media,
      status: "PLAN_TO_WATCH",
      user_id: user?.id,
    });

    if (result) {
      setLibraryItems((prev) => {
        const filtered = prev.filter((i) => i.external_id !== media.external_id);
        return [result, ...filtered];
      });
      showToast(`"${media.title}" Rafına eklendi! 🔖`);
    } else {
      showToast("Raf güncellenirken bir sorun oluştu.", "error");
    }
  };

  const handleMarkWatched = async (media: UnifiedMediaDTO) => {
    const result = await addToLibrary({
      media,
      status: "COMPLETED",
      user_id: user?.id,
    });

    if (result) {
      setLibraryItems((prev) => {
        const filtered = prev.filter((i) => i.external_id !== media.external_id);
        return [result, ...filtered];
      });
      showToast(`"${media.title}" İzlediklerine kaydedildi! 👁️`);
    } else {
      showToast("Raf güncellenirken bir sorun oluştu.", "error");
    }
  };

  // Active item user is currently watching
  const activeWatchingItem = libraryItems.find((i) => i.status === "WATCHING") || null;

  const handleWatchingFeedback = async (action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS") => {
    if (!activeWatchingItem) return;
    const mediaSource = (activeWatchingItem.source as "TMDB_MOVIE" | "TMDB_SERIES" | "ANILIST") || "TMDB_MOVIE";

    if (action === "LIKE") {
      await addToLibrary({
        media: {
          external_id: activeWatchingItem.external_id,
          source: mediaSource,
          title: activeWatchingItem.title,
          poster_url: activeWatchingItem.poster_url,
          genres: activeWatchingItem.genres,
          themes: activeWatchingItem.themes,
          base_score: activeWatchingItem.base_score,
          vote_count: 0,
          synopsis: "",
        },
        status: "WATCHING",
        is_favorite: true,
        user_id: user?.id,
      });
      setLibraryItems((prev) =>
        prev.map((i) => (i.id === activeWatchingItem.id ? { ...i, is_favorite: true } : i))
      );
      showToast(`"${activeWatchingItem.title}" Favorilere eklendi! ✨`);
    } else if (action === "DISLIKE") {
      await addToLibrary({
        media: {
          external_id: activeWatchingItem.external_id,
          source: mediaSource,
          title: activeWatchingItem.title,
          poster_url: activeWatchingItem.poster_url,
          genres: activeWatchingItem.genres,
          themes: activeWatchingItem.themes,
          base_score: activeWatchingItem.base_score,
          vote_count: 0,
          synopsis: "",
        },
        status: "DROPPED",
        user_id: user?.id,
      });
      setLibraryItems((prev) =>
        prev.map((i) => (i.id === activeWatchingItem.id ? { ...i, status: "DROPPED" } : i))
      );
      showToast(`"${activeWatchingItem.title}" Bırakılanlar listesine alındı.`);
    }
  };

  const handleSelectLiveResult = (item: LiveSearchResultItem) => {
    const mediaSource =
      (item.source as "TMDB_MOVIE" | "TMDB_SERIES" | "ANILIST") ||
      (item.type === "ANIME" ? "ANILIST" : item.type === "SERIES" ? "TMDB_SERIES" : "TMDB_MOVIE");

    const mediaDto: UnifiedMediaDTO = {
      external_id: item.id,
      source: mediaSource,
      title: item.title,
      original_title: item.title,
      release_year: item.release_year ?? undefined,
      poster_url: item.poster_path || "",
      synopsis: item.synopsis || `Canlı aramada doğrudan seçtiğin '${item.title}' yapımı.`,
      genres: item.genres || [],
      themes: [],
      base_score: item.base_score || 8.0,
      vote_count: 0,
    };

    const directJustification = `Canlı aramada doğrudan seçtiğin '${item.title}', türündeki başarısı ve yüksek seyir zevkiyle öne çıkan birincil önerimizdir.`;

    setRecommendation({
      recommendations: [
        {
          media: mediaDto,
          justification: directJustification,
          confidence_score: 1.0,
        },
      ],
      recommended_media: mediaDto,
      justification: directJustification,
      confidence_score: 1.0,
      parsed_intent: {
        is_direct_title_search: true,
        direct_title: item.title,
        media_type_filter: item.type === "ANIME" ? "ANIME" : item.type === "SERIES" ? "SERIES" : "MOVIE",
        mood_keywords: [],
        target_themes: [],
        excluded_tropes: [],
        reference_titles: [],
      },
      candidates_count: 1,
      all_candidates: [mediaDto],
    });

    showToast(`"${item.title}" açıldı ✨`);
  };

  const hasResult = recommendation !== null && recommendation.recommended_media !== null;

  const currentMediaId = recommendation?.recommended_media?.external_id;
  const isSavedInLibrary = Boolean(
    currentMediaId && libraryItems.some((i) => i.external_id === currentMediaId)
  );
  const isAlreadyWatched = Boolean(
    currentMediaId &&
      libraryItems.some((i) => i.external_id === currentMediaId && i.status === "COMPLETED")
  );

  return (
    <main className="relative min-h-screen flex flex-col justify-between overflow-x-hidden">
      {/* 1. Header with Shelflick logo and Shelf Drawer toggle */}
      <Header
        onReset={handleReset}
        onOpenShelf={() => setIsShelfOpen(true)}
        shelfCount={libraryItems.length}
        activeWatchingItem={activeWatchingItem}
        onWatchingFeedback={handleWatchingFeedback}
      />

      {/* 2. Slide-out Shelf Drawer */}
      <ShelfDrawer
        isOpen={isShelfOpen}
        onClose={() => setIsShelfOpen(false)}
        items={libraryItems}
        isLoading={isShelfLoading}
      />

      {/* 3. Infinite scrolling interactive poster wall */}
      <BackgroundWall onPosterClick={handlePosterClick} />

      {/* Main Content Area */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-4 pt-28 pb-12 w-full max-w-5xl mx-auto">
        {/* Animated Brand Header (fades or shrinks when result is active) */}
        <AnimatePresence>
          {!hasResult && (
            <motion.div
              initial={{ opacity: 0, y: -20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, height: 0 }}
              transition={{ duration: 0.3 }}
              className="text-center mb-6 select-none"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.04] border border-white/10 text-indigo-300 text-xs font-medium mb-3 backdrop-blur-md">
                <Sparkles className="w-3.5 h-3.5" />
                <span>MediaPulse Akıllı Zevk Algoritması</span>
              </div>
              <h1 className="text-4xl md:text-6xl font-black tracking-tight text-white leading-tight">
                Ne izleyeceğini <br className="hidden sm:inline" />
                <span className="bg-gradient-to-r from-indigo-400 via-purple-300 to-pink-400 bg-clip-text text-transparent">
                  tam isabetle
                </span>{" "}
                keşfet.
              </h1>
              <p className="text-neutral-400 text-sm md:text-base mt-3 max-w-lg mx-auto font-normal">
                Klişelerden uzak, zevkine özel ve sadece senin için gerekçelendirilmiş yapay zeka küratörün.
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 4. Central Omnibar (smoothly shifts position) */}
        <Omnibar
          onSearch={handleSearch}
          onRandom={handleRandom}
          onSelectLiveResult={handleSelectLiveResult}
          isLoading={isLoading}
          compact={hasResult}
        />

        {/* Suggested Prompt Inspiration Pills (when no result) */}
        {!hasResult && !isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-wrap items-center justify-center gap-2 mt-4 text-xs text-neutral-400"
          >
            <span className="text-neutral-400 font-medium">İlham Al:</span>
            {SUGGESTED_PROMPTS.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handleSearch(p, "ALL")}
                className="px-3 py-1 rounded-full bg-white/[0.03] hover:bg-white/[0.08] hover:text-neutral-200 border border-white/5 transition-colors cursor-pointer"
              >
                "{p}"
              </button>
            ))}
          </motion.div>
        )}

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

        {/* 5. Skeleton Loading Card or SuggestionCard */}
        <div className="w-full mt-6">
          <AnimatePresence mode="wait">
            {isLoading && (
              <motion.div
                key="skeleton-loader"
                initial={{ opacity: 0, y: 30, scale: 0.96 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -10, scale: 0.96 }}
                transition={{ duration: 0.25 }}
                className="w-full max-w-4xl mx-auto glass-panel rounded-3xl p-6 md:p-8 shadow-2xl border border-white/10"
              >
                <div className="flex flex-col md:flex-row gap-6 md:gap-8 items-start animate-pulse">
                  {/* Poster Skeleton */}
                  <div className="w-full md:w-64 flex-shrink-0 aspect-[2/3] rounded-2xl bg-white/[0.05] border border-white/5" />
                  {/* Content Skeleton */}
                  <div className="flex-1 w-full space-y-4">
                    <div className="h-8 bg-white/[0.08] rounded-xl w-3/4" />
                    <div className="flex gap-2">
                      <div className="h-5 bg-white/[0.05] rounded-md w-16" />
                      <div className="h-5 bg-white/[0.05] rounded-md w-24" />
                    </div>
                    <div className="flex gap-1.5 pt-2">
                      <div className="h-6 bg-white/[0.05] rounded-lg w-20" />
                      <div className="h-6 bg-white/[0.05] rounded-lg w-24" />
                      <div className="h-6 bg-white/[0.05] rounded-lg w-16" />
                    </div>
                    <div className="h-24 bg-indigo-500/[0.06] border border-indigo-500/20 rounded-2xl p-4 mt-4" />
                    <div className="flex gap-3 pt-4 border-t border-white/5">
                      <div className="h-9 bg-white/[0.06] rounded-xl w-32" />
                      <div className="h-9 bg-white/[0.06] rounded-xl w-28" />
                    </div>
                  </div>
                </div>
              </motion.div>
            )}

            {hasResult && (recommendation?.recommendations?.length || recommendation?.recommended_media) && (
              <SuggestionCard
                key="suggestion-carousel"
                recommendations={recommendation?.recommendations}
                media={recommendation?.recommended_media || undefined}
                justification={recommendation?.justification}
                confidenceScore={recommendation?.confidence_score}
                libraryItems={libraryItems}
                isSavedInLibrary={isSavedInLibrary}
                isAlreadyWatched={isAlreadyWatched}
                onDismiss={handleDismiss}
                onAddToList={handleAddToList}
                onMarkWatched={handleMarkWatched}
              />
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Footer Branding */}
      <footer className="relative z-10 py-6 text-center text-xs text-neutral-400 border-t border-white/5 select-none pointer-events-none">
        <p>Shelflick &copy; 2026 — Google Sadeliğinde Kişisel Medya Keşfi</p>
      </footer>
    </main>
  );
}
