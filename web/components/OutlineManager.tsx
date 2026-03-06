"use client";

import { useState } from "react";

import { saveOutline } from "@/lib/api";
import type { OutlineSection } from "@/lib/types";

type OutlineManagerProps = {
  projectId: number;
  initialSections: OutlineSection[];
};

type OutlineRow = {
  id?: number;
  localId: string;
  sort_order: number;
  depth: number;
  display_label: string;
  title: string;
};

function buildLocalKey(sectionId?: number) {
  return sectionId ? `section-${sectionId}` : `draft-${Math.random().toString(36).slice(2, 10)}`;
}

function toRows(sections: OutlineSection[]): OutlineRow[] {
  return sections.map((section) => ({
    id: section.id,
    localId: buildLocalKey(section.id),
    sort_order: section.sort_order,
    depth: section.depth,
    display_label: section.display_label,
    title: section.title
  }));
}

function clampDepth(depth: number) {
  return Math.max(1, Math.min(6, depth));
}

function normalizeRows(rows: OutlineRow[]): OutlineRow[] {
  const counters = [0, 0, 0, 0, 0, 0];
  let previousDepth = 0;

  return rows.map((row, index) => {
    const desiredDepth = clampDepth(row.depth);
    const normalizedDepth =
      previousDepth === 0 ? 1 : Math.min(desiredDepth, Math.min(6, previousDepth + 1));

    counters[normalizedDepth - 1] += 1;
    for (let position = normalizedDepth; position < counters.length; position += 1) {
      counters[position] = 0;
    }

    previousDepth = normalizedDepth;

    return {
      ...row,
      sort_order: index + 1,
      depth: normalizedDepth,
      display_label: counters.slice(0, normalizedDepth).join(".")
    };
  });
}

function renderPreview(row: OutlineRow) {
  return `${row.display_label} ${row.title}`.trim();
}

export function OutlineManager({ projectId, initialSections }: OutlineManagerProps) {
  const [sections, setSections] = useState<OutlineRow[]>(normalizeRows(toRows(initialSections)));
  const [busyAction, setBusyAction] = useState<"save" | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function updateRow(localId: string, patch: Partial<OutlineRow>) {
    setSections((current) =>
      normalizeRows(
        current.map((section) => (section.localId === localId ? { ...section, ...patch } : section))
      )
    );
  }

  function addSection() {
    setSections((current) =>
      normalizeRows([
        ...current,
        {
          localId: buildLocalKey(),
          sort_order: current.length + 1,
          depth: 1,
          display_label: "",
          title: `새 목차 ${current.length + 1}`
        }
      ])
    );
  }

  function suggestInsertedDepth(index: number, current: OutlineRow[]) {
    const previous = current[index - 1];
    const next = current[index];
    if (previous && next && previous.depth === next.depth) {
      return previous.depth;
    }
    if (previous) {
      return previous.depth;
    }
    if (next) {
      return next.depth;
    }
    return 1;
  }

  function insertSectionAt(index: number) {
    setSections((current) => {
      const next = [...current];
      next.splice(index, 0, {
        localId: buildLocalKey(),
        sort_order: index + 1,
        depth: suggestInsertedDepth(index, current),
        display_label: "",
        title: `새 목차 ${current.length + 1}`
      });
      return normalizeRows(next);
    });
  }

  function removeSection(localId: string) {
    setSections((current) => normalizeRows(current.filter((section) => section.localId !== localId)));
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
      return normalizeRows(next);
    });
  }

  function changeDepth(localId: string, delta: -1 | 1) {
    setSections((current) =>
      normalizeRows(
        current.map((section) =>
          section.localId === localId
            ? { ...section, depth: clampDepth(section.depth + delta) }
            : section
        )
      )
    );
  }

  async function handleSave() {
    if (sections.some((section) => !section.title.trim())) {
      setError("모든 목차 제목을 입력해 주세요.");
      return;
    }

    try {
      setBusyAction("save");
      setError(null);
      setMessage(null);
      const saved = await saveOutline(projectId, {
        sections: sections.map((section, index) => ({
          id: section.id,
          sort_order: index + 1,
          depth: section.depth,
          display_label: section.display_label.trim(),
          title: section.title.trim()
        }))
      });
      setSections(normalizeRows(toRows(saved)));
      setMessage("목차를 저장했습니다.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "목차 저장에 실패했습니다.");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Outline Builder</p>
            <h2 className="card-title">목차 구조 정의</h2>
            <p className="page-copy">
              이 화면에서는 상위/하위 목차와 제목만 정의합니다. 번호는 depth와 순서에 따라 자동으로
              계산되며, 초안 생성은 Draft Workspace에서 진행합니다.
            </p>
          </div>
          <div className="status-row">
            <span className="status-pill ok">{sections.length} sections</span>
            <span className="status-pill">번호 자동 계산</span>
          </div>
        </div>

        <div className="stack-list">
          {sections.length === 0 ? (
            <div className="outline-empty-state">
              <p className="card-title">아직 저장된 목차가 없습니다.</p>
              <p className="card-copy">
                섹션을 추가한 뒤 깊이와 제목을 입력해 주세요. 번호는 구조에 맞게 자동으로
                계산됩니다.
              </p>
            </div>
          ) : (
            <>
              {sections.map((section, index) => (
                <div key={section.localId} className="outline-row-wrap">
                  <div className="outline-insert-slot">
                    <span className="outline-insert-line" />
                    <button
                      className="outline-insert-button"
                      onClick={() => insertSectionAt(index)}
                      type="button"
                    >
                      +
                    </button>
                    <span className="outline-insert-line" />
                  </div>

                  <article className="mini-card outline-row-card">
                    <div className="outline-row-header">
                      <div className="status-row" style={{ marginTop: 0 }}>
                        <span className="code-badge">#{index + 1}</span>
                        <span className="status-pill">depth {section.depth}</span>
                      </div>
                      <p
                        className="outline-row-preview"
                        style={{ paddingLeft: `${(section.depth - 1) * 20}px` }}
                      >
                        {renderPreview(section)}
                      </p>
                    </div>

                    <div className="outline-grid">
                      <label className="field">
                        <span>깊이</span>
                        <input
                          max={6}
                          min={1}
                          type="number"
                          value={section.depth}
                          onChange={(event) =>
                            updateRow(section.localId, {
                              depth: clampDepth(Number(event.target.value) || 1)
                            })
                          }
                        />
                      </label>
                      <label className="field">
                        <span>번호</span>
                        <input readOnly value={section.display_label} />
                      </label>
                      <label className="field outline-title-field">
                        <span>목차 제목</span>
                        <input
                          placeholder="예: 사업 수행 전략"
                          value={section.title}
                          onChange={(event) => updateRow(section.localId, { title: event.target.value })}
                        />
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
                        onClick={() => changeDepth(section.localId, 1)}
                        type="button"
                      >
                        들여쓰기
                      </button>
                      <button
                        className="secondary-button"
                        onClick={() => changeDepth(section.localId, -1)}
                        type="button"
                      >
                        내어쓰기
                      </button>
                      <button
                        className="secondary-button"
                        onClick={() => removeSection(section.localId)}
                        type="button"
                      >
                        삭제
                      </button>
                    </div>
                  </article>
                </div>
              ))}

              <div className="outline-insert-slot">
                <span className="outline-insert-line" />
                <button
                  className="outline-insert-button"
                  onClick={() => insertSectionAt(sections.length)}
                  type="button"
                >
                  +
                </button>
                <span className="outline-insert-line" />
              </div>
            </>
          )}
        </div>

        <div className="action-row">
          <button className="secondary-button" onClick={addSection} type="button">
            섹션 추가
          </button>
          <button
            className="button"
            disabled={busyAction === "save"}
            onClick={() => void handleSave()}
            type="button"
          >
            {busyAction === "save" ? "저장 중..." : "목차 저장"}
          </button>
        </div>
        {message ? <p className="page-copy">{message}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </section>
  );
}
