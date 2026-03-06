"use client";

import { useEffect, useMemo, useState } from "react";

import {
  applyDraftChatMessage,
  createDraftChatTurn,
  generateDraft,
  getDraftPlan,
  updateDraftSection,
  updateQuestion
} from "@/lib/api";
import type {
  DraftChatMessage,
  DraftGeneratePayload,
  DraftPlanResult,
  DraftSection,
  OpenQuestion,
  OutlineSection
} from "@/lib/types";
import { EditorTextarea } from "@/components/EditorTextarea";
import { OpenQuestionPanel } from "@/components/OpenQuestionPanel";
import { SystemNotice } from "@/components/SystemNotice";

type DraftWorkspaceProps = {
  projectId: number;
  initialLinkedAssetCount: number;
  initialOutlineSections: OutlineSection[];
  initialRfpFileCount: number;
  initialRfpReady: boolean;
  initialSection: DraftSection;
  initialQuestions: OpenQuestion[];
  initialChatMessages: DraftChatMessage[];
};

type SelectionState = {
  start: number;
  end: number;
  text: string;
};

const DRAFT_GENERATION_PROGRESS_STEPS = [
  "저장된 목차별 생성 계획과 근거 선택 상태를 확인하고 있습니다.",
  "선택된 RFP 요구사항과 회사 자료를 섹션별 컨텍스트로 정리하고 있습니다.",
  "섹션별 초안을 생성하고 후속 질문을 정리하고 있습니다."
];

type DraftSectionSelection = {
  requirementIds: number[];
  chunkIds: number[];
};

function extractSystemNotices(content: string): string[] {
  return content
    .split("\n")
    .filter((line) => line.includes("[확인 필요(시스템)]"))
    .map((line) => line.replace("[확인 필요(시스템)]", "").trim())
    .filter(Boolean);
}

function buildSelectionState(plan: DraftPlanResult): Record<number, DraftSectionSelection> {
  return Object.fromEntries(
    plan.sections.map((section) => [
      section.section_id,
      {
        requirementIds: section.matched_requirements.map((requirement) => requirement.id),
        chunkIds: [...section.rfp_sources, ...section.library_sources].map((source) => source.chunk_id)
      }
    ])
  );
}

function toggleNumberInList(values: number[], target: number): number[] {
  if (values.includes(target)) {
    return values.filter((value) => value !== target);
  }
  return [...values, target];
}

export function DraftWorkspace({
  projectId,
  initialLinkedAssetCount,
  initialOutlineSections,
  initialRfpFileCount,
  initialRfpReady,
  initialSection,
  initialQuestions,
  initialChatMessages
}: DraftWorkspaceProps) {
  const [content, setContent] = useState(initialSection.content_md);
  const [questions, setQuestions] = useState(initialQuestions);
  const [chatMessages, setChatMessages] = useState(initialChatMessages);
  const [sectionTitle, setSectionTitle] = useState(initialSection.title);
  const [selection, setSelection] = useState<SelectionState>({ start: 0, end: 0, text: "" });
  const [chatInput, setChatInput] = useState("");
  const [statusLabel, setStatusLabel] = useState(initialSection.status);
  const [draftPlan, setDraftPlan] = useState<DraftPlanResult | null>(null);
  const [sectionSelections, setSectionSelections] = useState<Record<number, DraftSectionSelection>>({});
  const [isPrepCollapsed, setIsPrepCollapsed] = useState(false);
  const [isLoadingPlan, setIsLoadingPlan] = useState(true);
  const [isRefreshingPlan, setIsRefreshingPlan] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateProgress, setGenerateProgress] = useState(8);
  const [generateStepIndex, setGenerateStepIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [applyingMessageId, setApplyingMessageId] = useState<number | null>(null);
  const [pendingQuestionId, setPendingQuestionId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);

  const notices = useMemo(() => extractSystemNotices(content), [content]);
  const canGenerate = Boolean(draftPlan?.ready);
  const prepOutlineRows = useMemo(
    () =>
      draftPlan?.sections.map((section) => ({
        id: section.section_id,
        depth: section.depth,
        label: section.heading_text
      })) ??
      initialOutlineSections.map((section) => ({
        id: section.id,
        depth: section.depth,
        label: `${section.display_label ? `${section.display_label} ` : ""}${section.title}`
      })),
    [draftPlan, initialOutlineSections]
  );

  useEffect(() => {
    if (!isGenerating) {
      setGenerateProgress(8);
      setGenerateStepIndex(0);
      return;
    }

    const startedAt = Date.now();
    const intervalId = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const nextProgress = Math.min(92, 12 + Math.floor(elapsed / 1400) * 4);
      const nextStepIndex = Math.min(
        DRAFT_GENERATION_PROGRESS_STEPS.length - 1,
        Math.floor(elapsed / 8000)
      );
      setGenerateProgress((current) => Math.max(current, nextProgress));
      setGenerateStepIndex(nextStepIndex);
    }, 900);

    return () => window.clearInterval(intervalId);
  }, [isGenerating]);

  async function loadDraftPlan(options?: { refresh?: boolean }): Promise<DraftPlanResult | null> {
    const isRefresh = Boolean(options?.refresh);
    try {
      if (isRefresh) {
        setIsRefreshingPlan(true);
      } else {
        setIsLoadingPlan(true);
      }
      setPlanError(null);
      const nextPlan = await getDraftPlan(projectId);
      setDraftPlan(nextPlan);
      setSectionSelections(buildSelectionState(nextPlan));
      return nextPlan;
    } catch (loadError) {
      setPlanError(loadError instanceof Error ? loadError.message : "초안 생성 계획을 불러오지 못했습니다.");
      return null;
    } finally {
      setIsLoadingPlan(false);
      setIsRefreshingPlan(false);
    }
  }

  useEffect(() => {
    void loadDraftPlan();
  }, [projectId]);

  function toggleRequirement(sectionId: number, requirementId: number) {
    setSectionSelections((current) => {
      const existing = current[sectionId] ?? { requirementIds: [], chunkIds: [] };
      return {
        ...current,
        [sectionId]: {
          ...existing,
          requirementIds: toggleNumberInList(existing.requirementIds, requirementId)
        }
      };
    });
  }

  function toggleSource(sectionId: number, chunkId: number) {
    setSectionSelections((current) => {
      const existing = current[sectionId] ?? { requirementIds: [], chunkIds: [] };
      return {
        ...current,
        [sectionId]: {
          ...existing,
          chunkIds: toggleNumberInList(existing.chunkIds, chunkId)
        }
      };
    });
  }

  function buildGeneratePayload(plan: DraftPlanResult): DraftGeneratePayload {
    return {
      mode: "full",
      section_overrides: plan.sections.map((section) => {
        const fallbackRequirementIds = section.matched_requirements.map((requirement) => requirement.id);
        const fallbackChunkIds = [...section.rfp_sources, ...section.library_sources].map(
          (source) => source.chunk_id
        );
        const selectionState = sectionSelections[section.section_id];
        return {
          section_id: section.section_id,
          requirement_ids: selectionState?.requirementIds ?? fallbackRequirementIds,
          chunk_ids: selectionState?.chunkIds ?? fallbackChunkIds
        };
      })
    };
  }

  async function handleSave() {
    try {
      setIsSaving(true);
      setError(null);
      setSuccessMessage(null);
      const updated = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setStatusLabel(updated.status);
      setSectionTitle(updated.title);
      setSuccessMessage("초안을 저장했습니다.");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "초안 저장에 실패했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  async function handleResolve(questionId: string, nextStatus: "open" | "resolved") {
    try {
      setPendingQuestionId(questionId);
      setError(null);
      setSuccessMessage(null);
      const updated = await updateQuestion(projectId, questionId, { status: nextStatus });
      setQuestions((current) =>
        current.map((question) => (question.id === questionId ? updated : question))
      );
    } catch (questionError) {
      setError(questionError instanceof Error ? questionError.message : "질문 상태 변경에 실패했습니다.");
    } finally {
      setPendingQuestionId(null);
    }
  }

  async function handleSendChat() {
    if (!chatInput.trim()) {
      setError("AI에게 보낼 수정 요청을 입력해 주세요.");
      return;
    }

    try {
      setIsSendingChat(true);
      setError(null);
      setSuccessMessage(null);
      const synced = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setStatusLabel(synced.status);
      setSectionTitle(synced.title);
      const turn = await createDraftChatTurn(projectId, {
        section_id: initialSection.id,
        message: chatInput.trim(),
        selection_start: selection.text ? selection.start : null,
        selection_end: selection.text ? selection.end : null,
        selection_text: selection.text || null
      });
      setChatMessages((current) => [...current, turn.user_message, turn.assistant_message]);
      setChatInput("");
    } catch (chatError) {
      setError(chatError instanceof Error ? chatError.message : "AI 편집 요청에 실패했습니다.");
    } finally {
      setIsSendingChat(false);
    }
  }

  async function handleApplyMessage(messageId: number) {
    try {
      setApplyingMessageId(messageId);
      setError(null);
      setSuccessMessage(null);
      const response = await applyDraftChatMessage(projectId, messageId);
      setContent(response.section.content_md);
      setStatusLabel(response.section.status);
      setSectionTitle(response.section.title);
      setChatMessages((current) =>
        current.map((message) => (message.id === messageId ? response.message : message))
      );
      setSuccessMessage("AI 제안을 초안에 반영했습니다.");
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "AI 제안 적용에 실패했습니다.");
    } finally {
      setApplyingMessageId(null);
    }
  }

  async function handleGenerateDraft() {
    const plan = draftPlan ?? (await loadDraftPlan());
    if (!plan?.ready) {
      setError("RFP 추출 결과와 저장된 목차가 있어야 초안을 생성할 수 있습니다.");
      return;
    }

    try {
      setIsGenerating(true);
      setError(null);
      setSuccessMessage(null);
      const result = await generateDraft(projectId, buildGeneratePayload(plan));
      setContent(result.section.content_md);
      setQuestions(result.questions);
      setChatMessages([]);
      setSectionTitle(result.section.title);
      setStatusLabel(result.section.status);
      setSelection({ start: 0, end: 0, text: "" });
      setChatInput("");
      setSuccessMessage(
        `초안을 생성했습니다. 후속 질문 ${result.questions.length}건이 함께 갱신되었습니다.`
      );
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "초안 생성에 실패했습니다.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Draft Preparation</p>
            <h2 className="card-title">초안 생성 준비</h2>
            <p className="page-copy">
              확정된 RFP, 연결된 회사 자료, 저장된 목차를 확인한 뒤 초안을 생성합니다. 인터넷
              검색 보강은 추후 이 영역에 이어서 붙일 예정입니다.
            </p>
          </div>
          <div>
            <div className="status-row" style={{ marginTop: 0 }}>
              <span className={`status-pill ${draftPlan?.ready ? "ok" : "warn"}`}>
                {draftPlan?.ready ? "Draft ready" : "Draft pending"}
              </span>
              <span className="status-pill ok">{initialRfpFileCount} RFP files</span>
              <span className="status-pill ok">{initialLinkedAssetCount} linked assets</span>
              <span className={`status-pill ${prepOutlineRows.length > 0 ? "ok" : "warn"}`}>
                {prepOutlineRows.length} outline rows
              </span>
            </div>
            <div className="action-row" style={{ justifyContent: "flex-end" }}>
              <button
                className="secondary-button"
                disabled={isLoadingPlan || isRefreshingPlan}
                onClick={() => void loadDraftPlan({ refresh: true })}
                type="button"
              >
                {isRefreshingPlan ? "근거 새로고침 중..." : "근거 추천 새로고침"}
              </button>
              <button
                className="secondary-button"
                onClick={() => setIsPrepCollapsed((current) => !current)}
                type="button"
              >
                {isPrepCollapsed ? "준비 영역 펼치기" : "준비 영역 접기"}
              </button>
            </div>
          </div>
        </div>

        {isPrepCollapsed ? (
          <p className="page-copy">준비 영역이 접혀 있습니다. 초안을 다시 생성하려면 펼쳐서 실행하세요.</p>
        ) : (
          <>
            {isLoadingPlan ? (
              <div className="progress-shell">
                <div className="progress-meta">
                  <strong>초안 생성 계획 준비 중</strong>
                  <span className="subtle-copy">loading</span>
                </div>
                <p className="page-copy" style={{ marginTop: 10 }}>
                  목차별 추천 요구사항과 근거 문서를 정리하고 있습니다.
                </p>
                <div className="progress-bar" aria-hidden="true">
                  <div className="progress-fill" style={{ width: "42%" }} />
                </div>
              </div>
            ) : null}

            {draftPlan?.warnings.length ? (
              <div className="stack-list">
                {draftPlan.warnings.map((warning, index) => (
                  <SystemNotice
                    key={`${warning}-${index}`}
                    title={`생성 전 확인 #${index + 1}`}
                    description={warning}
                  />
                ))}
              </div>
            ) : null}

            {planError ? <p className="error-text">{planError}</p> : null}

            <div className="draft-prep-grid">
              <article className="mini-card">
                <p className="eyebrow">Checklist</p>
                <h3 className="card-title">생성 전 확인</h3>
                <ul className="plain-list">
                  <li>{initialRfpReady ? "RFP 추출 완료" : "RFP 추출 결과가 아직 없습니다."}</li>
                  <li>
                    {prepOutlineRows.length > 0
                      ? "목차 저장 완료"
                      : "Outline 페이지에서 목차를 먼저 저장해 주세요."}
                  </li>
                  <li>
                    {initialLinkedAssetCount > 0
                      ? "회사 자료 연결 완료"
                      : "자료 라이브러리에서 회사 자료를 연결하면 초안 품질이 좋아집니다."}
                  </li>
                </ul>
              </article>

              <article className="mini-card">
                <p className="eyebrow">Outline Preview</p>
                <h3 className="card-title">현재 목차 구조</h3>
                {prepOutlineRows.length === 0 ? (
                  <p className="card-copy">저장된 목차가 없습니다.</p>
                ) : (
                  <div className="stack-list">
                    {prepOutlineRows.map((section) => (
                      <p
                        key={section.id}
                        className="outline-row-preview"
                        style={{ paddingLeft: `${(section.depth - 1) * 20}px` }}
                      >
                        {section.label}
                      </p>
                    ))}
                  </div>
                )}
              </article>
            </div>

            {draftPlan?.sections.length ? (
              <section className="stack-list">
                {draftPlan.sections.map((section) => {
                  const selectionState = sectionSelections[section.section_id] ?? {
                    requirementIds: section.matched_requirements.map((requirement) => requirement.id),
                    chunkIds: [...section.rfp_sources, ...section.library_sources].map(
                      (source) => source.chunk_id
                    )
                  };
                  const selectedSourceCount = selectionState.chunkIds.length;
                  return (
                    <article key={section.section_id} className="mini-card draft-plan-card">
                      <div className="toolbar">
                        <div>
                          <p className="eyebrow">Section Plan</p>
                          <h3 className="card-title">{section.heading_text}</h3>
                          <p className="subtle-copy">{section.heading_path.join(" > ")}</p>
                        </div>
                        <div className="status-row" style={{ marginTop: 0 }}>
                          <span className="status-pill ok">{selectionState.requirementIds.length} requirements</span>
                          <span className="status-pill ok">{selectedSourceCount} sources</span>
                        </div>
                      </div>

                      <div className="draft-plan-block">
                        <p className="eyebrow">Requirements</p>
                        {section.matched_requirements.length === 0 ? (
                          <p className="card-copy">자동 매칭된 요구사항이 없습니다. 근거 문서만으로 생성됩니다.</p>
                        ) : (
                          <div className="checkbox-list">
                            {section.matched_requirements.map((requirement) => {
                              const checked = selectionState.requirementIds.includes(requirement.id);
                              const heading = [requirement.requirement_no, requirement.name]
                                .filter(Boolean)
                                .join(" ")
                                .trim();
                              return (
                                <label key={requirement.id} className="checkbox-row">
                                  <input
                                    checked={checked}
                                    className="checkbox-input"
                                    onChange={() => toggleRequirement(section.section_id, requirement.id)}
                                    type="checkbox"
                                  />
                                  <div>
                                    <strong>{heading || "무제 요구사항"}</strong>
                                    <p className="card-copy" style={{ marginTop: 8 }}>
                                      {requirement.definition || requirement.details || "정의된 내용 없음"}
                                    </p>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      <div className="draft-plan-block">
                        <p className="eyebrow">RFP Sources</p>
                        {section.rfp_sources.length === 0 ? (
                          <p className="card-copy">자동 추천된 RFP 원문 근거가 없습니다.</p>
                        ) : (
                          <div className="checkbox-list">
                            {section.rfp_sources.map((source) => {
                              const checked = selectionState.chunkIds.includes(source.chunk_id);
                              return (
                                <label key={source.chunk_id} className="checkbox-row">
                                  <input
                                    checked={checked}
                                    className="checkbox-input"
                                    onChange={() => toggleSource(section.section_id, source.chunk_id)}
                                    type="checkbox"
                                  />
                                  <div>
                                    <strong>{source.label}</strong>
                                    <p className="subtle-copy" style={{ marginTop: 6 }}>
                                      {source.route_label ? `${source.route_label} · ` : ""}score {source.score}
                                    </p>
                                    <p className="card-copy" style={{ marginTop: 8 }}>
                                      {source.snippet}
                                    </p>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        )}
                      </div>

                      <div className="draft-plan-block">
                        <p className="eyebrow">Company Sources</p>
                        {section.library_sources.length === 0 ? (
                          <p className="card-copy">연결된 회사 자료에서 자동 추천된 근거가 없습니다.</p>
                        ) : (
                          <div className="checkbox-list">
                            {section.library_sources.map((source) => {
                              const checked = selectionState.chunkIds.includes(source.chunk_id);
                              return (
                                <label key={source.chunk_id} className="checkbox-row">
                                  <input
                                    checked={checked}
                                    className="checkbox-input"
                                    onChange={() => toggleSource(section.section_id, source.chunk_id)}
                                    type="checkbox"
                                  />
                                  <div>
                                    <strong>{source.label}</strong>
                                    <p className="subtle-copy" style={{ marginTop: 6 }}>
                                      {source.route_label ? `${source.route_label} · ` : ""}score {source.score}
                                    </p>
                                    <p className="card-copy" style={{ marginTop: 8 }}>
                                      {source.snippet}
                                    </p>
                                  </div>
                                </label>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </article>
                  );
                })}
              </section>
            ) : null}

            <div className="action-row">
              <button
                className="button"
                disabled={isGenerating || isLoadingPlan || !canGenerate}
                onClick={() => void handleGenerateDraft()}
                type="button"
              >
                {isGenerating ? "초안 생성 중..." : "초안 생성"}
              </button>
            </div>

            {isGenerating ? (
              <div className="progress-shell">
                <div className="progress-meta">
                  <strong>초안 생성 중</strong>
                  <span className="subtle-copy">{generateProgress}%</span>
                </div>
                <p className="page-copy" style={{ marginTop: 10 }}>
                  {DRAFT_GENERATION_PROGRESS_STEPS[generateStepIndex]}
                </p>
                <p className="subtle-copy" style={{ marginTop: 8 }}>
                  문서 길이에 따라 보통 20~90초 정도 걸릴 수 있습니다.
                </p>
                <div className="progress-bar" aria-hidden="true">
                  <div className="progress-fill" style={{ width: `${generateProgress}%` }} />
                </div>
              </div>
            ) : null}
          </>
        )}

        {successMessage ? <p className="page-copy">{successMessage}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="split-layout" style={{ marginTop: 0 }}>
        <section className="panel-stack">
          {notices.length > 0 ? (
            notices.map((notice, index) => (
              <SystemNotice
                key={`${notice}-${index}`}
                title={`확인 필요(시스템) #${index + 1}`}
                description={notice}
              />
            ))
          ) : (
            <SystemNotice
              title="시스템 표기 없음"
              description="현재 초안에는 [확인 필요(시스템)] 마커가 없습니다."
            />
          )}

          <EditorTextarea
            onChange={setContent}
            onSelectionChange={setSelection}
            status={statusLabel}
            title={sectionTitle}
            value={content}
          />

          <div className="content-panel">
            <p className="eyebrow">Editor Actions</p>
            <h2 className="card-title">저장 및 선택 상태</h2>
            <p className="card-copy">
              선택된 텍스트: {selection.text.trim() || "선택된 구간 없음"}
            </p>
            <div className="action-row">
              <button
                className="secondary-button"
                disabled={isSaving}
                onClick={() => void handleSave()}
                type="button"
              >
                {isSaving ? "저장 중..." : "초안 저장"}
              </button>
            </div>
          </div>
        </section>

        <aside className="panel-stack">
          <section className="question-list">
            <p className="eyebrow">AI Edit Chat</p>
            <h2 className="card-title">대화형 수정</h2>
            <p className="card-copy">
              선택 구간이 있으면 해당 문장만 수정 제안을 만들고, 없으면 현재 초안에 대한 편집
              가이드를 반환합니다.
            </p>
            <label className="field" style={{ marginTop: 16 }}>
              <span>AI에게 요청</span>
              <textarea
                className="input-textarea"
                placeholder="예: 이 문단을 더 공공사업 제안서 톤으로 다듬고, 근거가 부족한 문장은 확인 필요로 표시해 줘"
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
              />
            </label>
            <div className="action-row">
              <button className="button" disabled={isSendingChat} onClick={() => void handleSendChat()} type="button">
                {isSendingChat ? "전송 중..." : "AI에게 요청"}
              </button>
            </div>
            <div className="chat-thread" style={{ marginTop: 16 }}>
              {chatMessages.length === 0 ? (
                <p className="card-copy">아직 대화가 없습니다.</p>
              ) : (
                chatMessages.map((message) => (
                  <article
                    key={message.id}
                    className={`chat-bubble ${message.role === "assistant" ? "assistant" : "user"}`}
                  >
                    <div className="status-row" style={{ marginTop: 0 }}>
                      <span className="code-badge">{message.role === "assistant" ? "AI" : "USER"}</span>
                      <span className="status-pill">
                        {message.apply_mode === "replace_selection" ? "apply ready" : "advice"}
                      </span>
                      {message.applied_at ? <span className="status-pill ok">applied</span> : null}
                    </div>
                    <p className="chat-message">{message.message_text}</p>
                    {message.selection_text ? (
                      <div className="preview-box" style={{ marginTop: 12 }}>
                        <p className="eyebrow">Selection</p>
                        <pre className="mono chat-code">{message.selection_text}</pre>
                      </div>
                    ) : null}
                    {message.role === "assistant" && message.suggestion_text ? (
                      <div className="preview-box" style={{ marginTop: 12 }}>
                        <p className="eyebrow">Suggestion</p>
                        <pre className="mono chat-code">{message.suggestion_text}</pre>
                        {message.apply_mode === "replace_selection" ? (
                          <div className="action-row">
                            <button
                              className="button"
                              disabled={Boolean(message.applied_at) || applyingMessageId === message.id}
                              onClick={() => void handleApplyMessage(message.id)}
                              type="button"
                            >
                              {applyingMessageId === message.id ? "적용 중..." : "초안에 적용"}
                            </button>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </article>
                ))
              )}
            </div>
          </section>

          <OpenQuestionPanel
            onResolve={handleResolve}
            pendingQuestionId={pendingQuestionId}
            questions={questions}
          />
        </aside>
      </section>
    </section>
  );
}
