"use client";

import { useMemo, useState } from "react";

import { listLibraryAssets, uploadLibraryAsset } from "@/lib/api";
import { ASSET_CATEGORIES } from "@/lib/types";
import type { LibraryAsset } from "@/lib/types";
import { FileUploader } from "@/components/FileUploader";

type LibraryManagerProps = {
  initialAssets: LibraryAsset[];
};

export function LibraryManager({ initialAssets }: LibraryManagerProps) {
  const [assets, setAssets] = useState(initialAssets);
  const [filter, setFilter] = useState<string>("전체");
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const visibleAssets = useMemo(() => {
    if (filter === "전체") {
      return assets;
    }
    return assets.filter((asset) => asset.category === filter);
  }, [assets, filter]);

  async function refresh(category?: string) {
    try {
      setIsRefreshing(true);
      const nextAssets = await listLibraryAssets(category);
      setAssets(nextAssets);
      setError(null);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "라이브러리 목록을 불러오지 못했습니다.");
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <section className="section-spacer">
      <FileUploader
        onUpload={uploadLibraryAsset}
        onUploaded={(asset) => {
          setAssets((current) => [asset, ...current]);
          setError(null);
        }}
      />

      <section className="content-panel section-spacer">
        <div className="toolbar">
          <div>
            <p className="eyebrow">자료 목록</p>
            <h2 className="card-title">업로드된 자료</h2>
          </div>
          <div className="action-row">
            <select value={filter} onChange={(event) => setFilter(event.target.value)}>
              <option value="전체">전체</option>
              {ASSET_CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
            <button
              className="secondary-button"
              disabled={isRefreshing}
              onClick={() => void refresh(filter === "전체" ? undefined : filter)}
              type="button"
            >
              {isRefreshing ? "갱신 중..." : "목록 새로고침"}
            </button>
          </div>
        </div>

        {visibleAssets.length === 0 ? (
          <p className="page-copy">현재 조건에 맞는 자료가 없습니다.</p>
        ) : (
          <div className="stack-list">
            {visibleAssets.map((asset) => (
              <article key={asset.id} className="mini-card">
                <div className="status-row" style={{ marginTop: 0 }}>
                  <span className="code-badge">#{asset.id}</span>
                  <span className="status-pill ok">{asset.category}</span>
                </div>
                <h3 style={{ marginTop: 12 }}>{asset.title}</h3>
                <p className="card-copy">
                  파일: {asset.filename} · 경로: {asset.path}
                </p>
              </article>
            ))}
          </div>
        )}
        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </section>
  );
}
