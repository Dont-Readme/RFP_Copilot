"use client";

import { useEffect, useRef, useState } from "react";

import {
  applyDraftChatMessage,
  buildExportDownloadUrl,
  createDraftChatTurn,
  createExportSession,
  generateDraft,
  getDraftPlan,
  updateDraftSection,
  updateQuestion
} from "@/lib/api";
import type {
  DraftChatMessage,
  DraftPlanResult,
  DraftSection,
  OpenQuestion,
  OutlineSection
} from "@/lib/types";
import { EditorTextarea } from "@/components/EditorTextarea";
import { OpenQuestionPanel } from "@/components/OpenQuestionPanel";

type DraftWorkspaceProps = {
  projectId: number;
  initialLinkedAssetCount: number;
  initialOutlineSections: OutlineSection[];
  initialRfpFileCount: number;
  initialRfpReady: boolean;
  initialSection: DraftSection;
  initialReviewItems: OpenQuestion[];
  initialChatMessages: DraftChatMessage[];
};

type SelectionState = {
  start: number;
  end: number;
  text: string;
};

const EMPTY_SELECTION: SelectionState = { start: 0, end: 0, text: "" };

const DRAFT_GENERATION_PROGRESS_STEPS = [
  "저장된 목차와 RFP 요약 상태를 확인하고 있습니다.",
  "목차별 초안을 생성하고 있습니다.",
  "작성 확인 사항을 정리하고 있습니다."
];
const DOWNLOAD_FORMAT_OPTIONS = ["md", "txt"] as const;

type DownloadFormat = (typeof DOWNLOAD_FORMAT_OPTIONS)[number];

function hasSelection(selection: SelectionState): boolean {
  return selection.start !== selection.end && selection.text.length > 0;
}

function selectionMatchesContent(selection: SelectionState, currentContent: string): boolean {
  if (!hasSelection(selection)) {
    return true;
  }

  return currentContent.slice(selection.start, selection.end) === selection.text;
}

export function DraftWorkspace({
  projectId,
  initialLinkedAssetCount,
  initialOutlineSections,
  initialRfpFileCount,
  initialRfpReady,
  initialSection,
  initialReviewItems,
  initialChatMessages
}: DraftWorkspaceProps) {
  const [content, setContent] = useState(initialSection.content_md);
  const [questions, setQuestions] = useState(initialReviewItems);
  const [chatMessages, setChatMessages] = useState(initialChatMessages);
  const [sectionTitle, setSectionTitle] = useState(initialSection.title);
  const [editorSelection, setEditorSelection] = useState<SelectionState>(EMPTY_SELECTION);
  const [committedSelection, setCommittedSelection] = useState<SelectionState>(EMPTY_SELECTION);
  const [chatInput, setChatInput] = useState("");
  const [statusLabel, setStatusLabel] = useState(initialSection.status);
  const [draftPlan, setDraftPlan] = useState<DraftPlanResult | null>(null);
  const [isPrepCollapsed, setIsPrepCollapsed] = useState(false);
  const [isLoadingPlan, setIsLoadingPlan] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateProgress, setGenerateProgress] = useState(8);
  const [generateStepIndex, setGenerateStepIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);
  const [selectedDownloadFormats, setSelectedDownloadFormats] = useState<DownloadFormat[]>([]);
  const [isDownloading, setIsDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [applyingMessageId, setApplyingMessageId] = useState<number | null>(null);
  const [pendingQuestionId, setPendingQuestionId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const chatInputRef = useRef<HTMLTextAreaElement | null>(null);
  const copyFeedbackTimeoutRef = useRef<number | null>(null);

  const canGenerate = Boolean(draftPlan?.ready);
  const hasCommittedSelection = hasSelection(committedSelection);
  const isCommittedSelectionStale = hasCommittedSelection && !selectionMatchesContent(committedSelection, content);
  const canDownload = selectedDownloadFormats.length > 0;
  const prepOutlineRows =
    draftPlan?.sections.map((section) => ({
      id: section.section_id,
      depth: section.depth,
      label: section.heading_text
    })) ??
    initialOutlineSections.map((section) => ({
      id: section.id,
      depth: section.depth,
      label: `${section.display_label ? `${section.display_label} ` : ""}${section.title}`
    }));

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

  useEffect(() => {
    return () => {
      if (copyFeedbackTimeoutRef.current !== null) {
        window.clearTimeout(copyFeedbackTimeoutRef.current);
      }
    };
  }, []);

  async function loadDraftPlan(): Promise<DraftPlanResult | null> {
    try {
      setIsLoadingPlan(true);
      setPlanError(null);
      const nextPlan = await getDraftPlan(projectId);
      setDraftPlan(nextPlan);
      return nextPlan;
    } catch (loadError) {
      setPlanError(loadError instanceof Error ? loadError.message : "초안 준비 상태를 불러오지 못했습니다.");
      return null;
    } finally {
      setIsLoadingPlan(false);
    }
  }

  useEffect(() => {
    void loadDraftPlan();
  }, [projectId]);

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

  async function handleCopyDraft() {
    const textToCopy = content.trim();
    if (!textToCopy) {
      setError("복사할 초안 내용이 없습니다.");
      return;
    }

    try {
      setIsCopying(true);
      setError(null);

      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(content);
      } else {
        const tempTextarea = document.createElement("textarea");
        tempTextarea.value = content;
        tempTextarea.setAttribute("readonly", "true");
        tempTextarea.style.position = "absolute";
        tempTextarea.style.left = "-9999px";
        document.body.append(tempTextarea);
        tempTextarea.select();
        document.execCommand("copy");
        tempTextarea.remove();
      }

      setCopyFeedback("복사 완료");
      if (copyFeedbackTimeoutRef.current !== null) {
        window.clearTimeout(copyFeedbackTimeoutRef.current);
      }
      copyFeedbackTimeoutRef.current = window.setTimeout(() => {
        setCopyFeedback(null);
        copyFeedbackTimeoutRef.current = null;
      }, 1600);
    } catch (copyError) {
      setError(copyError instanceof Error ? copyError.message : "초안 복사에 실패했습니다.");
    } finally {
      setIsCopying(false);
    }
  }

  function openDownloadModal() {
    setSelectedDownloadFormats([]);
    setDownloadError(null);
    setIsDownloadModalOpen(true);
  }

  function closeDownloadModal() {
    if (isDownloading) {
      return;
    }
    setSelectedDownloadFormats([]);
    setDownloadError(null);
    setIsDownloadModalOpen(false);
  }

  function toggleDownloadFormat(format: DownloadFormat) {
    setSelectedDownloadFormats((current) =>
      current.includes(format) ? current.filter((item) => item !== format) : [...current, format]
    );
    setDownloadError(null);
  }

  function queueFileDownload(url: string, offsetMs: number) {
    window.setTimeout(() => {
      const iframe = document.createElement("iframe");
      iframe.style.display = "none";
      iframe.src = url;
      document.body.append(iframe);
      window.setTimeout(() => iframe.remove(), 5000);
    }, offsetMs);
  }

  async function handleDownloadDraft() {
    if (!canDownload) {
      setDownloadError("최소 한 개 이상의 형식을 선택해 주세요.");
      return;
    }

    const formatsToDownload = [...selectedDownloadFormats];

    try {
      setIsDownloading(true);
      setDownloadError(null);
      setError(null);
      setSuccessMessage(null);

      const synced = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setStatusLabel(synced.status);
      setSectionTitle(synced.title);

      const session = await createExportSession(projectId, { formats: formatsToDownload });
      formatsToDownload.forEach((format, index) => {
        queueFileDownload(buildExportDownloadUrl(projectId, session.id, format), index * 250);
      });

      setSelectedDownloadFormats([]);
      setIsDownloadModalOpen(false);
      setSuccessMessage(
        `${formatsToDownload.map((format) => format.toUpperCase()).join(", ")} 다운로드를 시작했습니다.`
      );
    } catch (downloadRequestError) {
      setDownloadError(
        downloadRequestError instanceof Error
          ? downloadRequestError.message
          : "다운로드 준비에 실패했습니다."
      );
    } finally {
      setIsDownloading(false);
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
      setError(questionError instanceof Error ? questionError.message : "작성 확인 사항 상태 변경에 실패했습니다.");
    } finally {
      setPendingQuestionId(null);
    }
  }

  async function handleSendChat() {
    if (!chatInput.trim()) {
      setError("AI에게 보낼 수정 요청을 입력해 주세요.");
      return;
    }
    if (isCommittedSelectionStale) {
      setError("선택된 텍스트가 변경되었습니다. DRAFT EDITOR에서 다시 선택 후 AI EDIT를 눌러 주세요.");
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
        selection_start: hasCommittedSelection ? committedSelection.start : null,
        selection_end: hasCommittedSelection ? committedSelection.end : null,
        selection_text: hasCommittedSelection ? committedSelection.text : null
      });
      setChatMessages((current) => [...current, turn.user_message, turn.assistant_message]);
      if (turn.review_items.length > 0) {
        setQuestions((current) => [...current, ...turn.review_items]);
        setSuccessMessage(`AI 요청을 반영하며 작성 확인 사항 ${turn.review_items.length}건을 추가했습니다.`);
      }
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
      setEditorSelection(EMPTY_SELECTION);
      setCommittedSelection(EMPTY_SELECTION);
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
      const result = await generateDraft(projectId, { mode: "full" });
      setContent(result.section.content_md);
      setQuestions(result.questions);
      setChatMessages([]);
      setSectionTitle(result.section.title);
      setStatusLabel(result.section.status);
      setEditorSelection(EMPTY_SELECTION);
      setCommittedSelection(EMPTY_SELECTION);
      setChatInput("");
      setSuccessMessage(
        `초안을 생성했습니다. 작성 확인 사항 ${result.questions.length}건이 함께 갱신되었습니다.`
      );
    } catch (generateError) {
      setError(generateError instanceof Error ? generateError.message : "초안 생성에 실패했습니다.");
    } finally {
      setIsGenerating(false);
    }
  }

  function handleCommitSelection(nextSelection: SelectionState) {
    setCommittedSelection(nextSelection);
    setError(null);
    setSuccessMessage(null);
    window.requestAnimationFrame(() => {
      chatInputRef.current?.focus();
    });
  }

  function handleClearCommittedSelection() {
    setCommittedSelection(EMPTY_SELECTION);
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Draft Preparation</p>
            <h2 className="card-title">초안 생성 준비</h2>
            <p className="page-copy">
              확정된 RFP 요약과 저장된 목차를 확인한 뒤 초안을 생성합니다. 검색 출처 표기는
              검색 기능이 준비되면 별도로 붙입니다.
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
                  저장된 목차와 RFP 요약 상태를 확인하고 있습니다.
                </p>
                <div className="progress-bar" aria-hidden="true">
                  <div className="progress-fill" style={{ width: "42%" }} />
                </div>
              </div>
            ) : null}

            {draftPlan?.warnings.length ? (
              <div className="draft-warning-list">
                {draftPlan.warnings.map((warning, index) => (
                  <p key={`${warning}-${index}`} className="draft-warning-item">
                    {warning}
                  </p>
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
                      ? `연결된 회사 자료 ${initialLinkedAssetCount}건`
                      : "연결된 회사 자료 없음"}
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

      <section className="split-layout draft-editor-layout" style={{ marginTop: 0 }}>
        <section className="panel-stack draft-editor-main">
          <EditorTextarea
            selection={editorSelection}
            onChange={setContent}
            onCommitSelection={handleCommitSelection}
            onSelectionChange={setEditorSelection}
            status={statusLabel}
            title={sectionTitle}
            value={content}
          />

          <div className="action-row draft-editor-save-row">
            <span className="draft-editor-feedback-slot" aria-live="polite">
              {copyFeedback ?? "\u00A0"}
            </span>
            <button
              className="button"
              disabled={isCopying}
              onClick={() => void handleCopyDraft()}
              type="button"
            >
              전체 복사
            </button>
            <button
              className="button"
              disabled={isSaving || isDownloading}
              onClick={() => void handleSave()}
              type="button"
            >
              {isSaving ? "저장 중..." : "초안 저장"}
            </button>
            <button
              className="button"
              disabled={isDownloading}
              onClick={openDownloadModal}
              type="button"
            >
              다운로드
            </button>
          </div>
        </section>

        <aside className="panel-stack draft-editor-side">
          <section className="question-list">
            <p className="eyebrow">AI Edit Chat</p>
            <h2 className="card-title">대화형 수정</h2>
            <div className={`preview-box draft-selection-preview${hasCommittedSelection ? "" : " is-empty"}`}>
              <div className="draft-selection-preview-header">
                <p className="eyebrow">Selected Text</p>
                {hasCommittedSelection ? (
                  <button className="secondary-button draft-selection-clear" onClick={handleClearCommittedSelection} type="button">
                    선택 해제
                  </button>
                ) : null}
              </div>
              {hasCommittedSelection ? (
                <>
                  <pre className="mono chat-code">{committedSelection.text}</pre>
                  {isCommittedSelectionStale ? (
                    <p className="error-text" style={{ marginTop: 0 }}>
                      초안 내용이 바뀌었습니다. 다시 선택 후 `AI EDIT`를 눌러 주세요.
                    </p>
                  ) : null}
                </>
              ) : (
                <p className="card-copy" style={{ marginTop: 0 }}>
                  DRAFT EDITOR에서 텍스트를 선택한 뒤 `AI EDIT` 칩을 누르면 여기에 들어옵니다.
                </p>
              )}
            </div>
            <label className="field" style={{ marginTop: 16 }}>
              <span>AI에게 요청</span>
              <textarea
                ref={chatInputRef}
                className="input-textarea"
                placeholder={
                  hasCommittedSelection
                    ? "예: 이 선택 구간을 더 간결한 제안서 문체로 다듬어 줘"
                    : "예: 이 문단을 더 공공사업 제안서 톤으로 다듬고, 근거가 부족한 문장은 확인 필요로 표시해 줘"
                }
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

      {isDownloadModalOpen ? (
        <div
          aria-hidden="true"
          className="modal-scrim"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeDownloadModal();
            }
          }}
        >
          <section aria-labelledby="draft-download-modal-title" aria-modal="true" className="modal-card" role="dialog">
            <p className="eyebrow">Draft Download</p>
            <h2 className="card-title" id="draft-download-modal-title">
              다운로드 형식 선택
            </h2>
            <p className="page-copy">
              저장되지 않은 변경은 먼저 반영한 뒤 선택한 형식으로 다운로드를 시작합니다.
            </p>
            <div className="checkbox-list download-format-list">
              {DOWNLOAD_FORMAT_OPTIONS.map((format) => (
                <label key={format} className="checkbox-row">
                  <input
                    checked={selectedDownloadFormats.includes(format)}
                    onChange={() => toggleDownloadFormat(format)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{format}</strong>
                  </span>
                </label>
              ))}
            </div>
            {downloadError ? <p className="error-text">{downloadError}</p> : null}
            <div className="action-row modal-actions">
              <button
                className="secondary-button"
                disabled={isDownloading}
                onClick={closeDownloadModal}
                type="button"
              >
                취소
              </button>
              <button
                className="button"
                disabled={isDownloading || !canDownload}
                onClick={() => void handleDownloadDraft()}
                type="button"
              >
                {isDownloading ? "다운로드 준비 중..." : "다운로드"}
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
