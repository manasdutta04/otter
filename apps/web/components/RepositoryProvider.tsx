"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
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

  const refresh = useCallback(async () => {
    if (!repositoryId) return;
    try {
      const repo = await api.getRepository(repositoryId);
      setRepository(repo);
      setAuthenticated(true);
      setError("");
      if (repo.status === "ready") {
        try {
          const intel = await api.getIntelligence(repositoryId);
          setIntelligence(intel);
        } catch {
          setIntelligence(null);
        }
      } else {
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
      setLoading(false);
    }
  }, [repositoryId]);

  useEffect(() => {
    void refresh();
    const interval = window.setInterval(() => {
      void refresh();
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(interval);
  }, [refresh]);

  const value = useMemo(
    () => ({
      repositoryId,
      repository,
      intelligence,
      authenticated,
      loading,
      error,
      refresh,
      isReady: repository?.status === "ready",
    }),
    [repositoryId, repository, intelligence, authenticated, loading, error, refresh],
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
