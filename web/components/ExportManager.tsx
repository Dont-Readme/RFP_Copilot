"use client";

import { useState } from "react";

import { createExportSession, getExportPreview } from "@/lib/api";
import { ExportPreviewPanel } from "@/components/ExportPreviewPanel";
import type { ExportPreview } from "@/lib/types";

const AVAILABLE_FORMATS = ["md", "txt", "docx", "xlsx"] as const;

type ExportManagerProps = {
  projectId: number;
};

export function ExportManager({ projectId }: ExportManagerProps) {
  const [selectedFormats, setSelectedFormats] = useState<Array<(typeof AVAILABLE_FORMATS)[number]>>([
    "md",
    "txt",
    "docx",
    "xlsx"
  ]);
  const [preview, setPreview] = useState<ExportPreview | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleFormat(format: (typeof AVAILABLE_FORMATS)[number]) {
    setSelectedFormats((current) =>
      current.includes(format) ? current.filter((item) => item !== format) : [...current, format]
    );
  }

  async function handleGenerate() {
    if (selectedFormats.length === 0) {
      setError("최소 한 개 이상의 포맷을 선택해 주세요.");
      return;
    }

    try {
      setIsGenerating(true);
      setError(null);
      const session = await createExportSession(projectId, { formats: selectedFormats });
      const nextPreview = await getExportPreview(projectId, session.id);
      setPreview(nextPreview);
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "Export 생성에 실패했습니다.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <p className="eyebrow">Export Run</p>
        <h2 className="card-title">미리보기 생성</h2>
        <p className="page-copy">
          현재 draft, 질문 상태, 매핑 경고를 묶어서 preview를 만들고 선택한 포맷으로 파일을 생성합니다.
        </p>
        <div className="checkbox-list">
          {AVAILABLE_FORMATS.map((format) => (
            <label key={format} className="checkbox-row">
              <input
                checked={selectedFormats.includes(format)}
                onChange={() => toggleFormat(format)}
                type="checkbox"
              />
              <span>
                <strong>{format}</strong>
              </span>
            </label>
          ))}
        </div>
        <div className="action-row">
          <button className="button" disabled={isGenerating} onClick={() => void handleGenerate()} type="button">
            {isGenerating ? "생성 중..." : "Export 생성"}
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      {preview ? (
        <ExportPreviewPanel
          exportSessionId={preview.export_session_id}
          formats={preview.formats}
          previewMd={preview.preview_md}
          projectId={projectId}
        />
      ) : (
        <section className="content-panel">
          <p className="page-copy">아직 생성된 export preview가 없습니다. 위에서 생성 버튼을 누르세요.</p>
        </section>
      )}
    </section>
  );
}
