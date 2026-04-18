"use client";

import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
} from "react";
import { clearTokens, getAccessToken, saveTokens } from "@/lib/api";
import { logger } from "@/lib/logger";
import type { UserProfile } from "@/types";
import Cookies from "js-cookie";

interface AuthContextValue {
  user: UserProfile | null;
  isLoading: boolean;
  setAuth: (user: UserProfile, access: string, refresh: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Rehydrate from cookie on mount
  useEffect(() => {
    logger.info(
      "Auth.Context",
      "Initializing AuthContext, checking for existing session",
    );
    const stored = Cookies.get("user_profile");
    if (stored && getAccessToken()) {
      try {
        const profile = JSON.parse(stored);
        setUser(profile);
        logger.info(
          "Auth.Context",
          `Session restored for user: ${profile.username}`,
        );
      } catch (err) {
        logger.warn(
          "Auth.Context",
          "Corrupt user_profile cookie, skipping restoration",
          err,
        );
      }
    } else {
      logger.info("Auth.Context", "No existing session found");
    }
    setIsLoading(false);
  }, []);

  const setAuth = useCallback(
    (u: UserProfile, access: string, refresh: string) => {
      logger.info("Auth.Context", `Setting auth for user: ${u.username}`, {
        userId: u.id,
      });
      setUser(u);
      saveTokens(access, refresh);
      Cookies.set("user_profile", JSON.stringify(u), { expires: 7 });
      logger.info(
        "Auth.Context",
        `User profile saved to cookies for ${u.username}`,
      );
    },
    [],
  );

  const logout = useCallback(() => {
    const currentUser = user?.username || "unknown";
    logger.info("Auth.Context", `Logging out user: ${currentUser}`);
    setUser(null);
    clearTokens();
    Cookies.remove("user_profile");
    logger.info("Auth.Context", "Logout complete, redirecting to login");
    window.location.href = "/auth/login";
  }, [user]);

  return (
    <AuthContext.Provider
      value={{ user, isLoading, setAuth, logout, isAuthenticated: !!user }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
