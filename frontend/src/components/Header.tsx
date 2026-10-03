"use client";

import React, { useState } from "react";
import { BookOpen, LogIn, LogOut, User as UserIcon } from "lucide-react";
import { FloatingBadge } from "./FloatingBadge";
import { useAuth } from "@/context/AuthContext";
import Link from "next/link";

interface HeaderProps {
  onReset: () => void;
  onOpenShelf?: () => void;
  shelfCount: number;
  activeWatchingItem?: { title: string; id?: string; external_id?: string } | null;
  onWatchingFeedback?: (action: "LIKE" | "WATCHING" | "DISLIKE" | "DISMISS") => void;
}

export const Header: React.FC<HeaderProps> = ({
  onReset,
  onOpenShelf,
  shelfCount,
  activeWatchingItem,
  onWatchingFeedback,
}) => {
  const { user, openAuthModal, logout } = useAuth();

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
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-500 flex items-center justify-center font-black tracking-tighter text-white text-base shadow-glow group-hover:scale-105 transition-transform duration-300">
          <span className="font-mono tracking-tighter text-sm font-black">||&gt;</span>
        </div>
        <div className="flex flex-col text-left">
          <span className="text-lg font-bold tracking-tight text-white group-hover:text-indigo-400 transition-colors">
            Shelflick
          </span>
          <span className="text-[10px] text-neutral-400 font-medium -mt-1 tracking-wider uppercase">
            MediaPulse Engine
          </span>
        </div>
      </Link>

      {/* Top-Right: Rafım Button, Feedback, and User Auth / Profile */}
      <div className="flex items-center gap-2.5 md:gap-3">
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
