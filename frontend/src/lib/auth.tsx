import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

import { api } from "./api";
import type { AuthTokens, User } from "./types";

const ACCESS_TOKEN_KEY = "saas_core_access_token";
const REFRESH_TOKEN_KEY = "saas_core_refresh_token";
const USER_KEY = "saas_core_user";

type AuthContextValue = {
  accessToken: string;
  refreshToken: string;
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    organization_name: string;
  }) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  const rawUser = localStorage.getItem(USER_KEY);
  if (!rawUser) {
    return null;
  }
  try {
    return JSON.parse(rawUser) as User;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

function persistSession(user: User, tokens: AuthTokens) {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState(
    () => localStorage.getItem(ACCESS_TOKEN_KEY) ?? "",
  );
  const [refreshToken, setRefreshToken] = useState(
    () => localStorage.getItem(REFRESH_TOKEN_KEY) ?? "",
  );
  const [user, setUser] = useState<User | null>(() => readStoredUser());

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      refreshToken,
      user,
      isAuthenticated: Boolean(accessToken && user),
      async login(email, password) {
        const response = await api.login(email, password);
        const tokens = {
          access: response.access ?? response.tokens?.access ?? "",
          refresh: response.refresh ?? response.tokens?.refresh ?? "",
        };
        persistSession(response.user, tokens);
        setAccessToken(tokens.access);
        setRefreshToken(tokens.refresh);
        setUser(response.user);
      },
      async register(payload) {
        const response = await api.register(payload);
        const tokens = {
          access: response.tokens?.access ?? response.access ?? "",
          refresh: response.tokens?.refresh ?? response.refresh ?? "",
        };
        persistSession(response.user, tokens);
        setAccessToken(tokens.access);
        setRefreshToken(tokens.refresh);
        setUser(response.user);
      },
      async logout() {
        const token = accessToken;
        const refresh = refreshToken;
        clearSession();
        setAccessToken("");
        setRefreshToken("");
        setUser(null);
        if (token && refresh) {
          try {
            await api.logout(token, refresh);
          } catch {
            // Local logout must succeed even if the refresh token is already invalid.
          }
        }
      },
    }),
    [accessToken, refreshToken, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
