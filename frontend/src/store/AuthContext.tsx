import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, authStore, type User } from "../api/client";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthState>({
  user: null,
  loading: true,
  login: async () => {},
  logout: () => {},
  refreshUser: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (authStore.token) {
        try {
          setUser(await api.me());
        } catch {
          authStore.clear();
        }
      }
      setLoading(false);
    })();
  }, []);

  const login = async (email: string, password: string) => {
    const tokens = await api.login(email, password);
    authStore.set(tokens);
    setUser(await api.me());
  };

  const logout = () => {
    authStore.clear();
    setUser(null);
  };

  const refreshUser = async () => {
    setUser(await api.me());
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
