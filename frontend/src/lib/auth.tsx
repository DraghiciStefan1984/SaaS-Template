import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, configureAuthTokenHandlers } from "./api";
import type { User } from "./types";

const USER_KEY = "saas_core_user";
const LEGACY_ACCESS_TOKEN_KEY = "saas_core_access_token";

type AuthContextValue = {
  accessToken: string;
  user: User | null;
  isAuthenticated: boolean;
  isBootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    name: string;
    organization_name: string;
  }) => Promise<void>;
  updateProfile: (payload: { name: string }) => Promise<User>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredUser(): User | null {
  const rawUser = sessionStorage.getItem(USER_KEY);
  if (!rawUser) {
    return null;
  }
  try {
    return JSON.parse(rawUser) as User;
  } catch {
    sessionStorage.removeItem(USER_KEY);
    return null;
  }
}

function persistUser(user: User) {
  sessionStorage.setItem(USER_KEY, JSON.stringify(user));
}

function clearSession() {
  sessionStorage.removeItem(LEGACY_ACCESS_TOKEN_KEY);
  sessionStorage.removeItem(USER_KEY);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredUser());
  const [accessToken, setAccessToken] = useState("");
  const [shouldRestoreSession] = useState(() => Boolean(user));
  const [isBootstrapping, setIsBootstrapping] = useState(shouldRestoreSession);

  useEffect(() => {
    configureAuthTokenHandlers({
      setAccessToken(nextAccessToken) {
        setAccessToken(nextAccessToken);
      },
      clearAuth() {
        clearSession();
        setAccessToken("");
        setUser(null);
      },
    });
    return () => configureAuthTokenHandlers({});
  }, []);

  useEffect(() => {
    let isCancelled = false;

    async function restoreSession() {
      if (!shouldRestoreSession) {
        clearSession();
        setIsBootstrapping(false);
        return;
      }

      try {
        const refreshResponse = await api.refresh();
        const restoredUser = await api.me(refreshResponse.access);
        if (!isCancelled) {
          setAccessToken(refreshResponse.access);
          setUser(restoredUser);
          persistUser(restoredUser);
        }
      } catch {
        if (!isCancelled) {
          clearSession();
          setAccessToken("");
          setUser(null);
        }
      } finally {
        if (!isCancelled) {
          setIsBootstrapping(false);
        }
      }
    }

    restoreSession();
    return () => {
      isCancelled = true;
    };
  }, [shouldRestoreSession]);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      user,
      isBootstrapping,
      isAuthenticated: Boolean(accessToken && user),
      async login(email, password) {
        const response = await api.login(email, password);
        const nextAccessToken = response.access ?? response.tokens?.access ?? "";
        persistUser(response.user);
        setAccessToken(nextAccessToken);
        setUser(response.user);
      },
      async register(payload) {
        const response = await api.register(payload);
        const nextAccessToken = response.tokens?.access ?? response.access ?? "";
        persistUser(response.user);
        setAccessToken(nextAccessToken);
        setUser(response.user);
      },
      async updateProfile(payload) {
        const updatedUser = await api.updateMe(accessToken, payload);
        persistUser(updatedUser);
        setUser(updatedUser);
        return updatedUser;
      },
      async logout() {
        const token = accessToken;
        clearSession();
        setAccessToken("");
        setUser(null);
        if (token) {
          try {
            await api.logout(token);
          } catch {
            // Local logout must succeed even if the refresh cookie is already invalid.
          }
        }
      },
    }),
    [accessToken, isBootstrapping, user],
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
