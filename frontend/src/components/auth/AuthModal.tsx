"use client";

import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { GoogleLogin } from "@react-oauth/google";
import { useAuth } from "@/context/AuthContext";
import {
  X,
  Mail,
  Lock,
  User as UserIcon,
  Loader2,
  Sparkles,
  AlertCircle,
  Eye,
  EyeOff,
} from "lucide-react";

const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "";
const GOOGLE_ENABLED =
  GOOGLE_CLIENT_ID.endsWith(".apps.googleusercontent.com") && !GOOGLE_CLIENT_ID.includes("placeholder");

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function AuthModal() {
  const { isAuthModalOpen, authModalMode, closeAuthModal, login, register, loginWithGoogle } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const emailRef = useRef<HTMLInputElement>(null);

  // Reset form every time the modal opens
  useEffect(() => {
    if (!isAuthModalOpen) return;
    setMode(authModalMode);
    setPassword("");
    setShowPassword(false);
    setError(null);
    setIsSubmitting(false);
    submittingRef.current = false;
    const t = setTimeout(() => emailRef.current?.focus(), 50);
    return () => clearTimeout(t);
  }, [isAuthModalOpen, authModalMode]);

  // ESC to close + lock background scroll
  useEffect(() => {
    if (!isAuthModalOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !submittingRef.current) closeAuthModal();
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isAuthModalOpen, closeAuthModal]);

  const switchMode = (next: "login" | "register") => {
    setMode(next);
    setError(null);
  };

  const run = async (fn: () => Promise<void>, fallback: string) => {
    if (submittingRef.current) return; // guard against double submit
    submittingRef.current = true;
    setError(null);
    setIsSubmitting(true);
    try {
      await fn();
      setPassword("");
    } catch (err: unknown) {
      setError(err instanceof Error && err.message ? err.message : fallback);
    } finally {
      submittingRef.current = false;
      setIsSubmitting(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanEmail = email.trim();

    if (!EMAIL_RE.test(cleanEmail)) {
      setError("Geçerli bir e-posta adresi girin.");
      return;
    }
    if (mode === "register") {
      if (!name.trim()) {
        setError("Lütfen adınızı veya takma adınızı girin.");
        return;
      }
      if (password.length < 6) {
        setError("Şifre en az 6 karakter olmalıdır.");
        return;
      }
    } else if (!password) {
      setError("Lütfen şifrenizi girin.");
      return;
    }

    run(
      () => (mode === "login" ? login(cleanEmail, password) : register(cleanEmail, password, name.trim())),
      mode === "login" ? "Giriş yapılamadı." : "Kayıt olunamadı."
    );
  };

  const handleGoogleSuccess = (credential: string) =>
    run(() => loginWithGoogle(credential), "Google ile giriş başarısız oldu.");

  const handleClose = () => {
    if (!submittingRef.current) closeAuthModal();
  };

  const inputClass =
    "w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pl-10 pr-4 text-sm text-white placeholder-zinc-500 outline-none transition focus:border-amber-500/60 focus:bg-white/10 focus:ring-1 focus:ring-amber-500/60 disabled:opacity-60";

  return (
    <AnimatePresence>
      {isAuthModalOpen && (
        <div
          key="auth-modal"
          className="fixed inset-0 z-[100] flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
          aria-labelledby="auth-modal-title"
        >
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={handleClose}
            className="fixed inset-0 bg-black/80 backdrop-blur-md"
          />

          {/* Modal Window */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 15 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="relative w-full max-w-md max-h-[calc(100vh-2rem)] overflow-y-auto rounded-2xl border border-white/10 bg-gradient-to-b from-[#18181f]/95 to-[#0e0e13]/95 p-6 md:p-8 shadow-2xl backdrop-blur-xl"
          >
            {/* Subtle Ambient Glow */}
            <div className="pointer-events-none absolute -top-24 left-1/2 h-48 w-48 -translate-x-1/2 rounded-full bg-amber-500/15 blur-3xl" />

            {/* Close Button */}
            <button
              type="button"
              onClick={handleClose}
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
              <h2 id="auth-modal-title" className="text-2xl font-bold text-white tracking-tight">
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
                role="alert"
                className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-500/20 bg-red-500/10 p-3 text-xs text-red-300"
              >
                <AlertCircle className="h-4 w-4 shrink-0 text-red-400 mt-0.5" />
                <span>{error}</span>
              </motion.div>
            )}

            {/* 1. Google One-Click Login */}
            {GOOGLE_ENABLED && (
              <>
                <div
                  className={`flex w-full justify-center py-1 min-h-[44px] ${
                    isSubmitting ? "pointer-events-none opacity-50" : ""
                  }`}
                >
                  <GoogleLogin
                    onSuccess={(res) => {
                      if (res.credential) handleGoogleSuccess(res.credential);
                      else setError("Google'dan kimlik bilgisi alınamadı. Lütfen tekrar deneyin.");
                    }}
                    onError={() => {
                      setError(
                        "Google ile oturum açılamadı. Açılır pencere engellenmiş olabilir veya bu adres Google Console'da yetkili değil."
                      );
                    }}
                    theme="filled_black"
                    shape="rectangular"
                    text={mode === "login" ? "signin_with" : "signup_with"}
                    width="340"
                  />
                </div>

                {/* 2. Divider ("VEYA") */}
                <div className="my-5 flex items-center gap-3">
                  <div className="h-[1px] flex-1 bg-white/10" />
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">VEYA</span>
                  <div className="h-[1px] flex-1 bg-white/10" />
                </div>
              </>
            )}

            {/* 3. Email & Password Form */}
            <form onSubmit={handleSubmit} className="space-y-3.5" noValidate>
              {mode === "register" && (
                <div>
                  <label htmlFor="auth-name" className="block text-xs font-medium text-zinc-300 mb-1">
                    Ad Soyad
                  </label>
                  <div className="relative">
                    <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                    <input
                      id="auth-name"
                      type="text"
                      autoComplete="name"
                      maxLength={255}
                      placeholder="Adınız veya Rumuzunuz"
                      value={name}
                      disabled={isSubmitting}
                      onChange={(e) => setName(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                </div>
              )}

              <div>
                <label htmlFor="auth-email" className="block text-xs font-medium text-zinc-300 mb-1">
                  E-posta
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <input
                    id="auth-email"
                    ref={emailRef}
                    type="email"
                    autoComplete="email"
                    inputMode="email"
                    placeholder="ornek@shelflick.com"
                    value={email}
                    disabled={isSubmitting}
                    onChange={(e) => setEmail(e.target.value)}
                    className={inputClass}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="auth-password" className="block text-xs font-medium text-zinc-300 mb-1">
                  Şifre
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
                  <input
                    id="auth-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={mode === "login" ? "current-password" : "new-password"}
                    maxLength={128}
                    placeholder={mode === "login" ? "Şifreniz" : "En az 6 karakter"}
                    value={password}
                    disabled={isSubmitting}
                    onChange={(e) => setPassword(e.target.value)}
                    className={`${inputClass} pr-11`}
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-zinc-500 hover:text-zinc-300"
                    aria-label={showPassword ? "Şifreyi gizle" : "Şifreyi göster"}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
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
                    onClick={() => switchMode("register")}
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
                    onClick={() => switchMode("login")}
                    className="font-medium text-amber-400 hover:text-amber-300 hover:underline"
                  >
                    Giriş Yap
                  </button>
                </p>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
