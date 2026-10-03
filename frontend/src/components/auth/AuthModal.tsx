"use client";

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";
import { X, Mail, Lock, User as UserIcon, Loader2, Sparkles, AlertCircle } from "lucide-react";

export function AuthModal() {
  const { isAuthModalOpen, closeAuthModal, login, register, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        if (!name.trim()) {
          setError("Lütfen adınızı veya takma adınızı girin.");
          setIsSubmitting(false);
          return;
        }
        await register(email, password, name);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Bir hata oluştu.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSuccess = async (credential: string) => {
    setError(null);
    setIsSubmitting(true);
    try {
      await loginWithGoogle(credential);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Google ile giriş başarısız oldu.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={closeAuthModal}
          className="fixed inset-0 bg-black/80 backdrop-blur-md"
        />

        {/* Modal Window */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="relative w-full max-w-md overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-[#18181f]/95 to-[#0e0e13]/95 p-6 md:p-8 shadow-2xl backdrop-blur-xl"
        >
          {/* Subtle Ambient Glow */}
          <div className="pointer-events-none absolute -top-24 left-1/2 h-48 w-48 -translate-x-1/2 rounded-full bg-amber-500/15 blur-3xl" />

          {/* Close Button */}
          <button
            onClick={closeAuthModal}
            className="absolute right-4 top-4 p-2 text-zinc-400 transition-colors hover:text-white"
            aria-label="Kapat"
          >
            <X className="h-5 w-5" />
          </button>

          {/* Header */}
          <div className="text-center mb-6">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 mb-2.5 rounded-full border border-amber-500/20 bg-amber-500/10 text-amber-400 text-xs font-medium tracking-wide">
              <Sparkles className="h-3 w-3" />
              <span>Shelflick Hesabı</span>
            </div>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              {mode === "login" ? "Tekrar Hoş Geldin" : "Shelflick'e Katıl"}
            </h2>
            <p className="text-xs text-zinc-400 mt-1">
              {mode === "login"
                ? "Kişisel film ve anime rafına erişmek için giriş yap."
                : "Akıllı zevk profilini oluştur ve sinematik rafını yönet."}
            </p>
          </div>

          {/* Error Banner */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300"
            >
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
              <span>{error}</span>
            </motion.div>
          )}

          {/* 1. Google One-Click Login */}
          <div className="flex flex-col items-center justify-center">
            <div className="w-full flex justify-center py-1">
              <GoogleLogin
                onSuccess={(res) => {
                  if (res.credential) handleGoogleSuccess(res.credential);
                }}
                onError={() => {
                  setError("Google ile oturum açma penceresi kapatıldı veya başarısız oldu.");
                }}
                theme="filled_black"
                shape="rectangular"
                text={mode === "login" ? "signin_with" : "signup_with"}
                width="340"
              />
            </div>
          </div>

          {/* 2. Divider ("VEYA") */}
          <div className="my-5 flex items-center gap-3">
            <div className="h-[1px] flex-1 bg-white/10" />
            <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">VEYA</span>
            <div className="h-[1px] flex-1 bg-white/10" />
          </div>

          {/* 3. Email & Password Form */}
          <form onSubmit={handleSubmit} className="space-y-3.5">
            {mode === "register" && (
              <div>
                <label className="block text-xs font-medium text-zinc-300 mb-1">Ad Soyad</label>
                <div className="relative">
                  <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <input
                    type="text"
                    required
                    placeholder="Adınız veya Rumuzunuz"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-500 outline-none transition focus:border-amber-500/60 focus:bg-white/10 focus:ring-1 focus:ring-amber-500/60"
                  />
                </div>
              </div>
            )}

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">E-posta</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="email"
                  required
                  placeholder="ornek@shelflick.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-500 outline-none transition focus:border-amber-500/60 focus:bg-white/10 focus:ring-1 focus:ring-amber-500/60"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-zinc-300 mb-1">Şifre</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                <input
                  type="password"
                  required
                  minLength={6}
                  placeholder="En az 6 karakter"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-500 outline-none transition focus:border-amber-500/60 focus:bg-white/10 focus:ring-1 focus:ring-amber-500/60"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 py-3 text-sm font-semibold text-black shadow-lg shadow-amber-500/20 transition-all hover:brightness-110 active:scale-[0.99] disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>İşleniyor...</span>
                </>
              ) : mode === "login" ? (
                "Giriş Yap"
              ) : (
                "Kayıt Ol ve Başla"
              )}
            </button>
          </form>

          {/* Toggle Login / Register */}
          <div className="mt-5 text-center text-xs text-zinc-400">
            {mode === "login" ? (
              <p>
                Hesabın yok mu?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("register");
                    setError(null);
                  }}
                  className="font-medium text-amber-400 hover:text-amber-300 hover:underline"
                >
                  Hemen Kayıt Ol
                </button>
              </p>
            ) : (
              <p>
                Zaten hesabın var mı?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setMode("login");
                    setError(null);
                  }}
                  className="font-medium text-amber-400 hover:text-amber-300 hover:underline"
                >
                  Giriş Yap
                </button>
              </p>
            )}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
