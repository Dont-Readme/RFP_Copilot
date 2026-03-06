"use client";

import Link from "next/link";
import { useState } from "react";

import { generateDraft, getCitations, runSearch, saveOutline } from "@/lib/api";
import type { Citation, OutlineSection } from "@/lib/types";

type OutlineManagerProps = {
  projectId: number;
  initialSections: OutlineSection[];
  initialCitations: Citation[];
};

type OutlineRow = {
  id?: number;
  localId: string;
  parent_id: number | null;
  sort_order: number;
  title: string;
  needs_search: boolean;
};

function buildLocalKey(sectionId?: number) {
  return sectionId ? `section-${sectionId}` : `draft-${Math.random().toString(36).slice(2, 10)}`;
}

function toRows(sections: OutlineSection[]): OutlineRow[] {
  return sections.map((section) => ({
    id: section.id,
    localId: buildLocalKey(section.id),
    parent_id: section.parent_id,
    sort_order: section.sort_order,
    title: section.title,
    needs_search: section.needs_search
  }));
}

export function OutlineManager({
  projectId,
  initialSections,
  initialCitations
}: OutlineManagerProps) {
  const [sections, setSections] = useState<OutlineRow[]>(toRows(initialSections));
  const [citations, setCitations] = useState(initialCitations);
  const [busyAction, setBusyAction] = useState<"save" | "search" | "generate" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateRow(localId: string, patch: Partial<OutlineRow>) {
    setSections((current) =>
      current.map((section) => (section.localId === localId ? { ...section, ...patch } : section))
    );
  }

  function addSection() {
    setSections((current) => [
      ...current,
      {
        localId: buildLocalKey(),
        parent_id: null,
        sort_order: current.length + 1,
        title: `새 섹션 ${current.length + 1}`,
        needs_search: false
      }
    ]);
  }

  function removeSection(localId: string) {
    setSections((current) =>
      current
        .filter((section) => section.localId !== localId)
        .map((section, index) => ({ ...section, sort_order: index + 1 }))
    );
  }

  function moveSection(localId: string, direction: -1 | 1) {
    setSections((current) => {
      const index = current.findIndex((section) => section.localId === localId);
      const nextIndex = index + direction;
      if (index < 0 || nextIndex < 0 || nextIndex >= current.length) {
        return current;
      }

      const next = [...current];
      const [target] = next.splice(index, 1);
      next.splice(nextIndex, 0, target);
      return next.map((section, rowIndex) => ({ ...section, sort_order: rowIndex + 1 }));
    });
  }

  async function refreshCitations() {
    const latest = await getCitations(projectId);
    setCitations(latest);
  }

  async function handleSave() {
    if (sections.some((section) => !section.title.trim())) {
      setError("모든 섹션 제목을 입력해 주세요.");
      return;
    }

    try {
      setBusyAction("save");
      setError(null);
      setMessage(null);
      const saved = await saveOutline(projectId, {
        sections: sections.map((section, index) => ({
          id: section.id,
          parent_id: section.parent_id,
          sort_order: index + 1,
          title: section.title.trim(),
          needs_search: section.needs_search
        }))
      });
      setSections(toRows(saved));
      await refreshCitations();
      setMessage("목차를 저장했습니다.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "목차 저장에 실패했습니다.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleSearch() {
    const targetIds = sections.filter((section) => section.needs_search && section.id).map((section) => section.id as number);
    if (targetIds.length === 0) {
      setError("먼저 `검색 필요`가 켜진 섹션을 하나 이상 저장해 주세요.");
      return;
    }

    try {
      setBusyAction("search");
      setError(null);
      setMessage(null);
      await runSearch(projectId, { section_ids: targetIds });
      await refreshCitations();
      setMessage("저장된 RFP/연결 자료를 기준으로 인용을 갱신했습니다.");
    } catch (searchError) {
      setError(searchError instanceof Error ? searchError.message : "검색 실행에 실패했습니다.");
    } finally {
      setBusyAction(null);
    }
  }

  async function handleGenerateDraft() {
    try {
      setBusyAction("generate");
      setError(null);
      setMessage(null);
      const result = await generateDraft(projectId, { mode: "full" });
      setMessage(
        `목차 기반 초안을 생성했습니다. 질문 ${result.questions.length}건이 갱신되었습니다.`
      );
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "초안 생성에 실패했습니다.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Outline CRUD</p>
            <h2 className="card-title">목차와 검색 필요 플래그</h2>
            <p className="page-copy">
              현재 검색은 외부 웹이 아니라 저장된 RFP와 프로젝트 연결 자료를 대상으로 실행합니다.
            </p>
          </div>
          <div className="status-row">
            <span className="status-pill ok">{sections.length} sections</span>
            <span className="status-pill warn">
              {sections.filter((section) => section.needs_search).length} needs_search
            </span>
          </div>
        </div>

        <div className="stack-list">
          {sections.map((section, index) => {
            const sectionCitations = section.id
              ? citations.filter((citation) => citation.outline_section_id === section.id)
              : [];

            return (
              <article key={section.localId} className="mini-card">
                <div className="toolbar">
                  <div style={{ width: "100%" }}>
                    <div className="status-row" style={{ marginTop: 0 }}>
                      <span className="code-badge">#{index + 1}</span>
                      <span className={`status-pill ${section.needs_search ? "warn" : "ok"}`}>
                        {section.needs_search ? "search" : "manual"}
                      </span>
                      <span className="status-pill ok">{sectionCitations.length} citations</span>
                    </div>
                    <label className="field" style={{ marginTop: 12 }}>
                      <span>섹션 제목</span>
                      <input
                        value={section.title}
                        onChange={(event) => updateRow(section.localId, { title: event.target.value })}
                      />
                    </label>
                    <label className="checkbox-row" style={{ marginTop: 14 }}>
                      <input
                        checked={section.needs_search}
                        onChange={(event) =>
                          updateRow(section.localId, { needs_search: event.target.checked })
                        }
                        type="checkbox"
                      />
                      <span>
                        <strong>검색 필요</strong>
                        <span className="subtle-copy">
                          {" "}
                          체크된 섹션만 `search/run` 대상이 됩니다.
                        </span>
                      </span>
                    </label>
                  </div>
                  <div className="action-row">
                    <button
                      className="secondary-button"
                      onClick={() => moveSection(section.localId, -1)}
                      type="button"
                    >
                      위로
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => moveSection(section.localId, 1)}
                      type="button"
                    >
                      아래로
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() => removeSection(section.localId)}
                      type="button"
                    >
                      삭제
                    </button>
                  </div>
                </div>

                {sectionCitations.length > 0 ? (
                  <div className="stack-list" style={{ marginTop: 16 }}>
                    {sectionCitations.map((citation) => (
                      <div key={citation.id} className="preview-box">
                        <p className="eyebrow">Citation</p>
                        <h3 className="card-title">{citation.source_title}</h3>
                        <p className="card-copy">{citation.snippet}</p>
                        <p className="subtle-copy mono">{citation.source_url}</p>
                      </div>
                    ))}
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>

        <div className="action-row">
          <button className="secondary-button" onClick={addSection} type="button">
            섹션 추가
          </button>
          <button className="button" disabled={busyAction === "save"} onClick={() => void handleSave()} type="button">
            {busyAction === "save" ? "저장 중..." : "목차 저장"}
          </button>
          <button
            className="secondary-button"
            disabled={busyAction === "search"}
            onClick={() => void handleSearch()}
            type="button"
          >
            {busyAction === "search" ? "검색 중..." : "검색 실행"}
          </button>
          <button
            className="button"
            disabled={busyAction === "generate"}
            onClick={() => void handleGenerateDraft()}
            type="button"
          >
            {busyAction === "generate" ? "생성 중..." : "초안 재생성"}
          </button>
          <Link className="secondary-button" href={`/projects/${projectId}/draft`}>
            Draft 열기
          </Link>
        </div>
        {message ? <p className="page-copy">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </section>
  );
}
