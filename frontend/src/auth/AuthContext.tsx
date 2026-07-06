import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { authFetch, configureApiClient } from "../lib/api";

export type AuthRole = "SUPER_ADMIN" | "COMPANY_ADMIN" | "Super Admin" | "Admin" | "IT Admin" | "Viewer";

export interface AuthUser {
  id: number;
  email: string;
  username: string;
  displayName: string;
  role: AuthRole;
  companyId?: number | null;
  externalProvider?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isAuthLoading: boolean;
  login: (username: string, password: string) => Promise<AuthUser>;
  logout: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const REFRESH_TOKEN_KEY = "sentinel_refresh_token";
const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);
  const accessTokenRef = useRef<string | null>(null);
  const refreshInFlight = useRef<Promise<string | null> | null>(null);

  const clearSession = useCallback(() => {
    accessTokenRef.current = null;
    setAccessToken(null);
    setUser(null);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem("sentinel_active_session");
  }, []);

  const refreshAccessToken = useCallback(async () => {
    if (refreshInFlight.current) return refreshInFlight.current;

    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!refreshToken) return null;

    refreshInFlight.current = authFetch("/api/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refreshToken }),
    })
      .then(async (response) => {
        if (!response.ok) throw new Error("Refresh failed");
        const payload = await response.json();
        accessTokenRef.current = payload.accessToken;
        setAccessToken(payload.accessToken);
        setUser(payload.user);
        return payload.accessToken as string;
      })
      .catch(() => {
        clearSession();
        return null;
      })
      .finally(() => {
        refreshInFlight.current = null;
      });

    return refreshInFlight.current;
  }, [clearSession]);

  const getAccessToken = useCallback(async () => {
    return accessTokenRef.current || refreshAccessToken();
  }, [refreshAccessToken]);

  useEffect(() => {
    configureApiClient(getAccessToken, async () => {
      const token = await refreshAccessToken();
      if (!token) clearSession();
      return token;
    });
  }, [clearSession, getAccessToken, refreshAccessToken]);

  useEffect(() => {
    let active = true;
    refreshAccessToken().finally(() => {
      if (active) setIsAuthLoading(false);
    });
    return () => {
      active = false;
    };
  }, [refreshAccessToken]);

  const login = useCallback(async (username: string, password: string) => {
    const response = await authFetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (!response.ok) {
      throw new Error(response.status === 401 ? "Invalid username or password." : "Authentication service unavailable.");
    }
    const payload = await response.json();
    localStorage.setItem(REFRESH_TOKEN_KEY, payload.refreshToken);
    localStorage.setItem("sentinel_active_session", payload.user.email || payload.user.username);
    accessTokenRef.current = payload.accessToken;
    setAccessToken(payload.accessToken);
    setUser(payload.user);
    return payload.user as AuthUser;
  }, []);

  const logout = useCallback(async () => {
    const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    clearSession();
    if (refreshToken) {
      await authFetch("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refreshToken }),
      }).catch(() => undefined);
    }
  }, [clearSession]);

  const value = useMemo<AuthContextValue>(() => ({
    user,
    accessToken,
    isAuthenticated: !!user,
    isAuthLoading,
    login,
    logout,
    getAccessToken,
  }), [accessToken, getAccessToken, isAuthLoading, login, logout, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
};
