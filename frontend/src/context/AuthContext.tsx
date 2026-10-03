"use client";

import React, { createContext, useContext, useEffect, useState, ReactNode } from "react";
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

interface AuthContextType {
  user: UserDTO | null;
  token: string | null;
  isLoading: boolean;
  isAuthModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserDTO | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);

  // Initialize from localStorage on client mount
  useEffect(() => {
    const existingToken = getAuthToken();
    if (existingToken) {
      setToken(existingToken);
      getCurrentUserApi()
        .then((profile) => {
          if (profile) {
            setUser(profile);
          } else {
            // Token expired or invalid
            removeAuthToken();
            setToken(null);
            setUser(null);
          }
        })
        .catch(() => {
          removeAuthToken();
          setToken(null);
          setUser(null);
        })
        .finally(() => {
          setIsLoading(false);
        });
    } else {
      setIsLoading(false);
    }
  }, []);

  const openAuthModal = () => setIsAuthModalOpen(true);
  const closeAuthModal = () => setIsAuthModalOpen(false);

  const login = async (email: string, password: string) => {
    const res = await loginApi(email, password);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    setIsAuthModalOpen(false);
  };

  const register = async (email: string, password: string, name?: string) => {
    const res = await registerApi(email, password, name);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    setIsAuthModalOpen(false);
  };

  const loginWithGoogle = async (credential: string) => {
    const res = await googleAuthApi(credential);
    setAuthToken(res.access_token);
    setToken(res.access_token);
    setUser(res.user);
    setIsAuthModalOpen(false);
  };

  const logout = () => {
    removeAuthToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthModalOpen,
        openAuthModal,
        closeAuthModal,
        login,
        register,
        loginWithGoogle,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
