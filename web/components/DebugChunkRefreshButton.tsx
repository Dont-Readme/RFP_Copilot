"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { rebuildDebugRfpChunks } from "@/lib/api";

type DebugChunkRefreshButtonProps = {
  projectId: number;
};

export function DebugChunkRefreshButton({ projectId }: DebugChunkRefreshButtonProps) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  async function handleRefresh() {
    try {
      setIsRefreshing(true);
      setError(null);
      await rebuildDebugRfpChunks(projectId);
      router.refresh();
    } catch (refreshError) {
      setError(
        refreshError instanceof Error ? refreshError.message : "청크 재생성에 실패했습니다."
      );
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <div className="action-row" style={{ justifyContent: "space-between", alignItems: "center" }}>
      <button
        className="secondary-button"
        disabled={isRefreshing}
        onClick={() => void handleRefresh()}
        type="button"
      >
        {isRefreshing ? "청크 재생성 중..." : "RFP 청크 재생성"}
      </button>
      {error ? <p className="error-text">{error}</p> : null}
    </div>
  );
}
