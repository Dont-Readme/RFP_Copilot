"use client";

import { useMemo, useState } from "react";

import { syncProjectAssets } from "@/lib/api";
import type { LibraryAsset } from "@/lib/types";

type ProjectAssetManagerProps = {
  projectId: number;
  allAssets: LibraryAsset[];
  initialLinkedAssetIds: number[];
};

export function ProjectAssetManager({
  projectId,
  allAssets,
  initialLinkedAssetIds
}: ProjectAssetManagerProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>(initialLinkedAssetIds);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const selectedCount = useMemo(() => selectedIds.length, [selectedIds.length]);

  function toggle(assetId: number) {
    setSelectedIds((current) =>
      current.includes(assetId) ? current.filter((id) => id !== assetId) : [...current, assetId]
    );
  }

  async function handleSave() {
    try {
      setIsSaving(true);
      setError(null);
      const result = await syncProjectAssets(projectId, { asset_ids: selectedIds });
      setSelectedIds(result.asset_ids);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "자료 연결 저장에 실패했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="content-panel">
      <div className="toolbar">
        <div>
          <p className="eyebrow">Project Assets</p>
          <h2 className="card-title">프로젝트 연결 자료</h2>
          <p className="page-copy">체크 상태를 저장하면 현재 프로젝트의 연결 목록을 동기화합니다.</p>
        </div>
        <div className="status-row">
          <span className="status-pill ok">{selectedCount} linked</span>
        </div>
      </div>

      {allAssets.length === 0 ? (
        <p className="page-copy">라이브러리에 업로드된 자료가 없습니다. 먼저 라이브러리에서 파일을 올리세요.</p>
      ) : (
        <div className="checkbox-list">
          {allAssets.map((asset) => (
            <label key={asset.id} className="checkbox-row">
              <input
                checked={selectedIds.includes(asset.id)}
                onChange={() => toggle(asset.id)}
                type="checkbox"
              />
              <span>
                <strong>{asset.title}</strong> <span className="mono">({asset.category})</span>
                <span className="subtle-copy"> {asset.filename}</span>
              </span>
            </label>
          ))}
        </div>
      )}

      <div className="action-row">
        <button className="button" disabled={isSaving} onClick={() => void handleSave()} type="button">
          {isSaving ? "저장 중..." : "연결 상태 저장"}
        </button>
      </div>
      {error ? <p className="error-text">{error}</p> : null}
    </section>
  );
}
