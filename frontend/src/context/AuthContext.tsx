"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  ReactNode,
} from "react";
import { UserDTO } from "@/types";
import {
  getCurrentUserApi,
  getAuthToken,
  loginApi,
  registerApi,
  googleAuthApi,
  setAuthToken,
  removeAuthToken,
} from "@/services/api";

type AuthMode = "login" | "register";

interface AuthContextType {
  user: UserDTO | null;
  token: string | null;
  isLoading: boolean;
  isAuthModalOpen: boolean;
  authModalMode: AuthMode;
  openAuthModal: (mode?: AuthMode | unknown) => void;
  closeAuthModal: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const USER_CACHE_KEY = "shelflick_user";
const TOKEN_KEY = "shelflick_token";

/** Decodes the JWT payload (no signature check) to read `exp`. */
function isTokenExpired(token: string): boolean {
  try {
    const part = token.split(".")[1];
    const json = JSON.parse(atob(part.replace(/-/g, "+").replace(/_/g, "/")));
    return typeof json.exp === "number" && json.exp * 1000 <= Date.now();
  } catch {
    return true;
  }
}

function readCachedUser(): UserDTO | null {
  try {
    const raw = localStorage.getItem(USER_CACHE_KEY);
    return raw ? (JSON.parse(raw) as UserDTO) : null;
  } catch {
    return null;
  }
}

function writeCachedUser(user: UserDTO | null) {
  try {
    if (user) localStorage.setItem(USER_CACHE_KEY, JSON.stringify(user));
    else localStorage.removeItem(USER_CACHE_KEY);
  } catch {
    /* ignore quota / privacy mode errors */
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserDTO | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authModalMode, setAuthModalMode] = useState<AuthMode>("login");

  const clearSession = useCallback(() => {
    removeAuthToken();
    writeCachedUser(null);
    setToken(null);
    setUser(null);
  }, []);

  const applySession = useCallback((accessToken: string, profile: UserDTO) => {
    setAuthToken(accessToken);
    writeCachedUser(profile);
    setToken(accessToken);
    setUser(profile);
    setIsAuthModalOpen(false);
  }, []);

  // Initialize from localStorage on client mount
  useEffect(() => {
    const existingToken = getAuthToken();
    if (!existingToken || isTokenExpired(existingToken)) {
      if (existingToken) clearSession();
      setIsLoading(false);
      return;
    }

    setToken(existingToken);
    // Optimistic: show cached user immediately, then validate in background
    const cached = readCachedUser();
    if (cached) setUser(cached);

    getCurrentUserApi()
      .then((profile) => {
        if (profile) {
          setUser(profile);
          writeCachedUser(profile);
        } else {
          // Token rejected by server (401/403)
          clearSession();
        }
      })
      .catch((err) => {
        // Network / server error: keep the session, don't log the user out.
        console.warn("Oturum doğrulanamadı (sunucuya ulaşılamadı):", err);
      })
      .finally(() => setIsLoading(false));
  }, [clearSession]);

  // Keep multiple tabs in sync (login/logout in another tab)
  useEffect(() => {
    const onStorage = (e: StorageEvent) => {
      if (e.key !== TOKEN_KEY) return;
      if (!e.newValue) {
        setToken(null);
        setUser(null);
      } else {
        setToken(e.newValue);
        setUser(readCachedUser());
      }
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  const openAuthModal = useCallback((mode?: AuthMode | unknown) => {
    // Accepts being used directly as an onClick handler (event arg ignored)
    setAuthModalMode(mode === "register" ? "register" : "login");
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => setIsAuthModalOpen(false), []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await loginApi(email, password);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      const res = await registerApi(email, password, name);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const loginWithGoogle = useCallback(
    async (credential: string) => {
      const res = await googleAuthApi(credential);
      applySession(res.access_token, res.user);
    },
    [applySession]
  );

  const logout = useCallback(() => {
    clearSession();
    try {
      // Prevent Google One Tap from auto-selecting the same account again
      (window as unknown as { google?: { accounts?: { id?: { disableAutoSelect?: () => void } } } })
        .google?.accounts?.id?.disableAutoSelect?.();
    } catch {
      /* ignore */
    }
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      token,
      isLoading,
      isAuthModalOpen,
      authModalMode,
      openAuthModal,
      closeAuthModal,
      login,
      register,
      loginWithGoogle,
      logout,
    }),
    [user, token, isLoading, isAuthModalOpen, authModalMode, openAuthModal, closeAuthModal, login, register, loginWithGoogle, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
