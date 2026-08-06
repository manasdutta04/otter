"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api, REFRESH_INTERVAL_MS, type Intelligence, type Repository } from "../lib/api";

type RepositoryContextValue = {
  repositoryId: string;
  repository: Repository | null;
  intelligence: Intelligence | null;
  authenticated: boolean | null;
  loading: boolean;
  error: string;
  refresh: () => Promise<void>;
  isReady: boolean;
  getTabCache: <T>(key: string) => T | undefined;
  setTabCache: <T>(key: string, value: T) => void;
};

const RepositoryContext = createContext<RepositoryContextValue | null>(null);

export function RepositoryProvider({
  repositoryId,
  children,
}: {
  repositoryId: string;
  children: ReactNode;
}) {
  const [repository, setRepository] = useState<Repository | null>(null);
  const [intelligence, setIntelligence] = useState<Intelligence | null>(null);
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const tabCacheRef = useRef<Map<string, unknown>>(new Map());
  const intelligenceLoaded = useRef(false);

  const getTabCache = useCallback(<T,>(key: string): T | undefined => {
    return tabCacheRef.current.get(key) as T | undefined;
  }, []);

  const setTabCache = useCallback(<T,>(key: string, value: T) => {
    tabCacheRef.current.set(key, value);
  }, []);

  const refresh = useCallback(async (opts?: { quiet?: boolean }) => {
    if (!repositoryId) return;
    try {
      const repo = await api.getRepository(repositoryId);
      setRepository(repo);
      setAuthenticated(true);
      setError("");
      if (repo.status === "ready" && !intelligenceLoaded.current) {
        try {
          const intel = await api.getIntelligence(repositoryId);
          setIntelligence(intel);
          intelligenceLoaded.current = true;
        } catch {
          setIntelligence(null);
        }
      }
      if (repo.status !== "ready") {
        intelligenceLoaded.current = false;
        setIntelligence(null);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setAuthenticated(false);
        setRepository(null);
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to load repository");
    } finally {
      if (!opts?.quiet) setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    tabCacheRef.current.clear();
    intelligenceLoaded.current = false;
    setLoading(true);
    void refresh();
  }, [repositoryId, refresh]);

  // Poll only while import is still in progress — not on every tab switch / forever.
  useEffect(() => {
    const status = repository?.status;
    if (!status || status === "ready" || status === "failed") return;
    const interval = window.setInterval(() => {
      void refresh({ quiet: true });
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [repository?.status, refresh]);

  const value = useMemo(
    () => ({
      repositoryId,
      repository,
      intelligence,
      authenticated,
      loading,
      error,
      refresh: () => refresh(),
      isReady: repository?.status === "ready",
      getTabCache,
      setTabCache,
    }),
    [repositoryId, repository, intelligence, authenticated, loading, error, refresh, getTabCache, setTabCache],
  );

  return <RepositoryContext.Provider value={value}>{children}</RepositoryContext.Provider>;
}

export function useRepository() {
  const ctx = useContext(RepositoryContext);
  if (!ctx) {
    throw new Error("useRepository must be used within RepositoryProvider");
  }
  return ctx;
}
