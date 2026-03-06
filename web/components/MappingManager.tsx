"use client";

import { useState } from "react";

import { getMapping, runMapping } from "@/lib/api";
import type { MappingResult } from "@/lib/types";
import { MappingMatrix } from "@/components/MappingMatrix";

type MappingManagerProps = {
  projectId: number;
  initialResult: MappingResult;
};

export function MappingManager({ projectId, initialResult }: MappingManagerProps) {
  const [result, setResult] = useState(initialResult);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const rows = result.mappings.map((mapping) => {
    const evaluationItem = result.evaluation_items.find((item) => item.id === mapping.evaluation_item_id);
    return {
      code: evaluationItem?.score || "N/A",
      evaluationTitle: evaluationItem?.item ?? "Unknown",
      sectionTitle: mapping.section_title ?? "미매핑",
      strengthLabel: mapping.strength_label,
      strengthScore: mapping.strength_score,
      rationaleText: mapping.rationale_text
    };
  });

  async function refreshCurrent() {
    try {
      setError(null);
      const latest = await getMapping(projectId);
      setResult(latest);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : "매핑 결과를 불러오지 못했습니다.");
    }
  }

  async function handleRun() {
    try {
      setIsRunning(true);
      setError(null);
      const next = await runMapping(projectId, { strategy: "rules" });
      setResult(next);
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "매핑 실행에 실패했습니다.");
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Mapping Run</p>
            <h2 className="card-title">평가항목 매핑 검증</h2>
            <p className="page-copy">
              현재 draft 내용과 평가항목 키워드 겹침을 기준으로 strong/weak/missing을 계산합니다.
            </p>
          </div>
          <div className="action-row">
            <button className="button" disabled={isRunning} onClick={() => void handleRun()} type="button">
              {isRunning ? "실행 중..." : "매핑 재실행"}
            </button>
            <button className="secondary-button" onClick={() => void refreshCurrent()} type="button">
              현재 결과 새로고침
            </button>
          </div>
        </div>
        <div className="status-row">
          <span className="status-pill ok">{result.evaluation_items.length} items</span>
          <span className={`status-pill ${result.warnings.length > 0 ? "warn" : "ok"}`}>
            {result.warnings.length} warnings
          </span>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      {rows.length > 0 ? (
        <MappingMatrix rows={rows} />
      ) : (
        <section className="content-panel">
          <p className="page-copy">아직 저장된 매핑 결과가 없습니다. 매핑 재실행을 눌러 결과를 생성하세요.</p>
        </section>
      )}

      <section className="content-panel">
        <p className="eyebrow">Warnings</p>
        <h2 className="card-title">누락/약함 경고</h2>
        {result.warnings.length === 0 ? (
          <p className="page-copy">현재 경고가 없습니다.</p>
        ) : (
          <div className="stack-list">
            {result.warnings.map((warning) => (
              <article key={warning.id} className="mini-card system-notice">
                <div className="status-row" style={{ marginTop: 0 }}>
                  <span className="status-pill warn">{warning.type}</span>
                </div>
                <p className="card-copy">{warning.message}</p>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
