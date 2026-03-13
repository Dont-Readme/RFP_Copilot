"use client";

import { useEffect, useRef, useState } from "react";

import {
  applyDraftChatMessage,
  buildExportDownloadUrl,
  createDraftChatTurn,
  createExportSession,
  generateDraft,
  getDraftPlan,
  getDraftSearchTasks,
  updateDraftPlanningConfig,
  updateDraftSection
} from "@/lib/api";
import type {
  DraftChatMessage,
  DraftPlanResult,
  DraftSearchTask,
  DraftSection,
  OutlineSection
} from "@/lib/types";
import { EditorTextarea } from "@/components/EditorTextarea";
import { useUnsavedChangesGuard } from "@/hooks/useUnsavedChangesGuard";

type DraftWorkspaceProps = {
  projectId: number;
  initialLinkedAssetCount: number;
  initialOutlineSections: OutlineSection[];
  initialRfpFileCount: number;
  initialRfpReady: boolean;
  initialSection: DraftSection;
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
  "생성 단위별 본문 초안을 작성하고 있습니다.",
  "초안 편집을 위해 본문 구성을 마무리하고 있습니다."
];
const DOWNLOAD_FORMAT_OPTIONS = ["md", "txt"] as const;

type DownloadFormat = (typeof DOWNLOAD_FORMAT_OPTIONS)[number];
type PrepCardStatus = "loading" | "done" | "warn";

function hasSelection(selection: SelectionState): boolean {
  return selection.start !== selection.end && selection.text.length > 0;
}

function selectionMatchesContent(selection: SelectionState, currentContent: string): boolean {
  if (!hasSelection(selection)) {
    return true;
  }

  return currentContent.slice(selection.start, selection.end) === selection.text;
}

function formatPlannerReadyStatus(
  ready: boolean,
  generationRequiresConfirmation: boolean
): string {
  if (!ready) {
    return "준비 필요";
  }
  return generationRequiresConfirmation ? "확인 후 생성" : "초안 생성 가능";
}

function formatChatRole(role: DraftChatMessage["role"]): string {
  return role === "assistant" ? "AI" : "사용자";
}

function formatApplyMode(mode: DraftChatMessage["apply_mode"]): string {
  return mode === "replace_selection" ? "적용 가능" : "조언 전용";
}

function PrepCardTitle({
  eyebrow,
  title,
  status
}: {
  eyebrow: string;
  title: string;
  status: PrepCardStatus;
}) {
  return (
    <div className="draft-prep-card-header">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h3 className="card-title">{title}</h3>
      </div>
      <span
        aria-label={status === "loading" ? "로딩 중" : status === "done" ? "완료" : "확인 필요"}
        className={`prep-card-indicator is-${status}`}
        title={status === "loading" ? "준비 중" : status === "done" ? "완료" : "확인 필요"}
      >
        {status === "done" ? "✓" : status === "warn" ? "!" : ""}
      </span>
    </div>
  );
}

export function DraftWorkspace({
  projectId,
  initialLinkedAssetCount,
  initialOutlineSections,
  initialRfpFileCount,
  initialRfpReady,
  initialSection,
  initialChatMessages
}: DraftWorkspaceProps) {
  const [content, setContent] = useState(initialSection.content_md);
  const [savedContent, setSavedContent] = useState(initialSection.content_md);
  const [chatMessages, setChatMessages] = useState(initialChatMessages);
  const [sectionTitle, setSectionTitle] = useState(initialSection.title);
  const [editorSelection, setEditorSelection] = useState<SelectionState>(EMPTY_SELECTION);
  const [committedSelection, setCommittedSelection] = useState<SelectionState>(EMPTY_SELECTION);
  const [chatInput, setChatInput] = useState("");
  const [statusLabel, setStatusLabel] = useState(initialSection.status);
  const [draftPlan, setDraftPlan] = useState<DraftPlanResult | null>(null);
  const [authorIntent, setAuthorIntent] = useState("");
  const [savedAuthorIntent, setSavedAuthorIntent] = useState("");
  const [isPrepCollapsed, setIsPrepCollapsed] = useState(false);
  const [isLoadingPlan, setIsLoadingPlan] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateProgress, setGenerateProgress] = useState(8);
  const [generateStepIndex, setGenerateStepIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isSavingIntent, setIsSavingIntent] = useState(false);
  const [isCopying, setIsCopying] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);
  const [isPlannerModalOpen, setIsPlannerModalOpen] = useState(false);
  const [isOutlineModalOpen, setIsOutlineModalOpen] = useState(false);
  const [isCoverageModalOpen, setIsCoverageModalOpen] = useState(false);
  const [isSearchModalOpen, setIsSearchModalOpen] = useState(false);
  const [selectedDownloadFormats, setSelectedDownloadFormats] = useState<DownloadFormat[]>([]);
  const [isDownloading, setIsDownloading] = useState(false);
  const [isLoadingSearchTasks, setIsLoadingSearchTasks] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [applyingMessageId, setApplyingMessageId] = useState<number | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [searchTasks, setSearchTasks] = useState<DraftSearchTask[]>([]);
  const chatInputRef = useRef<HTMLTextAreaElement | null>(null);
  const copyFeedbackTimeoutRef = useRef<number | null>(null);

  const canGenerate = Boolean(draftPlan?.ready);
  const hasCommittedSelection = hasSelection(committedSelection);
  const isCommittedSelectionStale = hasCommittedSelection && !selectionMatchesContent(committedSelection, content);
  const canDownload = selectedDownloadFormats.length > 0;
  const hasUnsavedAuthorIntent = authorIntent !== savedAuthorIntent;
  const hasUnsavedDraftContent = content !== savedContent;
  const coverageCount = draftPlan?.requirement_coverage.length ?? 0;
  const completedSearchCount = searchTasks.filter((task) => task.status === "done").length;
  const adaptiveSearchCount = searchTasks.filter((task) => task.source_stage === "adaptive").length;
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
  const checklistStatus: PrepCardStatus =
    initialRfpReady && prepOutlineRows.length > 0 ? "done" : "warn";
  const authorIntentStatus: PrepCardStatus = isSavingIntent
    ? "loading"
    : hasUnsavedAuthorIntent
      ? "warn"
      : "done";
  const plannerCardStatus: PrepCardStatus = isLoadingPlan
    ? "loading"
    : draftPlan?.generation_units.length && !draftPlan?.generation_requires_confirmation && !(draftPlan?.coverage_warnings.length ?? 0)
      ? "done"
      : "warn";
  const outlineCardStatus: PrepCardStatus =
    prepOutlineRows.length > 0 ? "done" : "warn";

  useUnsavedChangesGuard(hasUnsavedDraftContent || hasUnsavedAuthorIntent);

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
      setAuthorIntent(nextPlan.author_intent);
      setSavedAuthorIntent(nextPlan.author_intent);
      return nextPlan;
    } catch (loadError) {
      setPlanError(loadError instanceof Error ? loadError.message : "초안 준비 상태를 불러오지 못했습니다.");
      return null;
    } finally {
      setIsLoadingPlan(false);
    }
  }

  async function loadSearchTasks(): Promise<void> {
    try {
      setIsLoadingSearchTasks(true);
      const nextTasks = await getDraftSearchTasks(projectId);
      setSearchTasks(nextTasks);
    } finally {
      setIsLoadingSearchTasks(false);
    }
  }

  useEffect(() => {
    void loadDraftPlan();
  }, [projectId]);

  useEffect(() => {
    void loadSearchTasks();
  }, [projectId]);

  async function persistAuthorIntent(options?: { reloadPlan?: boolean }): Promise<DraftPlanResult | null> {
    try {
      setIsSavingIntent(true);
      setError(null);
      setSuccessMessage(null);
      await updateDraftPlanningConfig(projectId, {
        author_intent: authorIntent
      });
      setSavedAuthorIntent(authorIntent);
      if (options?.reloadPlan === false) {
        setSuccessMessage("작성 의도를 저장했습니다.");
        return draftPlan;
      }
      const nextPlan = await loadDraftPlan();
      setSuccessMessage("작성 의도를 저장하고 계획을 새로 계산했습니다.");
      return nextPlan;
    } catch (intentError) {
      setError(intentError instanceof Error ? intentError.message : "작성 설정 저장에 실패했습니다.");
      return null;
    } finally {
      setIsSavingIntent(false);
    }
  }

  async function handleSave() {
    try {
      setIsSaving(true);
      setError(null);
      setSuccessMessage(null);
      const updated = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setSavedContent(updated.content_md);
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

  function openPlannerModal() {
    setIsPlannerModalOpen(true);
  }

  function closePlannerModal() {
    setIsPlannerModalOpen(false);
  }

  function openOutlineModal() {
    setIsOutlineModalOpen(true);
  }

  function closeOutlineModal() {
    setIsOutlineModalOpen(false);
  }

  function openCoverageModal() {
    setIsCoverageModalOpen(true);
  }

  function closeCoverageModal() {
    if (isGenerating) {
      return;
    }
    setIsCoverageModalOpen(false);
  }

  function openSearchModal() {
    setIsSearchModalOpen(true);
    void loadSearchTasks();
  }

  function closeSearchModal() {
    setIsSearchModalOpen(false);
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
      setSavedContent(synced.content_md);
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

  async function handleSendChat() {
    if (!chatInput.trim()) {
      setError("AI에게 보낼 수정 요청을 입력해 주세요.");
      return;
    }
    if (isCommittedSelectionStale) {
      setError("선택된 텍스트가 변경되었습니다. 초안 편집기에서 다시 선택한 뒤 AI 편집을 눌러 주세요.");
      return;
    }

    try {
      setIsSendingChat(true);
      setError(null);
      setSuccessMessage(null);
      const synced = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setSavedContent(synced.content_md);
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
      setSavedContent(response.section.content_md);
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

  async function handleGenerateDraft(confirmedWarnings = false) {
    const plan =
      hasUnsavedAuthorIntent
        ? await persistAuthorIntent({ reloadPlan: true })
        : draftPlan ?? (await loadDraftPlan());
    if (!plan?.ready) {
      setError("RFP 추출 결과와 저장된 목차가 있어야 초안을 생성할 수 있습니다.");
      return;
    }
    if (plan.generation_requires_confirmation && !confirmedWarnings) {
      openCoverageModal();
      return;
    }

    try {
      if (confirmedWarnings) {
        setIsCoverageModalOpen(false);
      }
      setIsGenerating(true);
      setError(null);
      setSuccessMessage(null);
      const result = await generateDraft(projectId, {
        mode: "full",
        confirm_warnings: confirmedWarnings
      });
      setContent(result.section.content_md);
      setSavedContent(result.section.content_md);
      setChatMessages([]);
      setSectionTitle(result.section.title);
      setStatusLabel(result.section.status);
      setEditorSelection(EMPTY_SELECTION);
      setCommittedSelection(EMPTY_SELECTION);
      setChatInput("");
      await loadSearchTasks();
      setSuccessMessage("초안을 생성했습니다.");
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
            <p className="eyebrow">초안 준비</p>
            <h2 className="card-title">초안 생성 준비</h2>
            <p className="page-copy">
              확정된 RFP 요약과 저장된 목차를 확인한 뒤 초안을 생성합니다. 작성 의도는
              생성 단위와 요구사항 배치에 반영되고, 외부 검색은 시스템이 목차와 요구사항을
              바탕으로 판단해 수행합니다.
            </p>
          </div>
          <div className="draft-prep-toolbar-side">
            <div className="status-row" style={{ marginTop: 0 }}>
              <span className={`status-pill ${draftPlan?.ready ? "ok" : "warn"}`}>
                {formatPlannerReadyStatus(
                  Boolean(draftPlan?.ready),
                  Boolean(draftPlan?.generation_requires_confirmation)
                )}
              </span>
              <span className="status-pill ok">RFP 파일 {initialRfpFileCount}건</span>
              <span className="status-pill ok">연결 자료 {initialLinkedAssetCount}건</span>
              <span className={`status-pill ${prepOutlineRows.length > 0 ? "ok" : "warn"}`}>
                목차 {prepOutlineRows.length}개
              </span>
            </div>
            <div className="action-row" style={{ justifyContent: "flex-end" }}>
              <button
                className="button"
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
              <div aria-live="polite" className="progress-shell is-live" role="status">
                <div className="progress-meta">
                  <div className="progress-heading">
                    <span aria-hidden="true" className="progress-indicator">
                      <span className="progress-indicator-ring" />
                      <span className="progress-indicator-core" />
                    </span>
                    <strong>초안 생성 계획 준비 중</strong>
                  </div>
                  <span className="subtle-copy">로딩 중</span>
                </div>
                <p className="page-copy progress-live-copy" style={{ marginTop: 10 }}>
                  {isSavingIntent
                    ? "작성 의도를 저장한 뒤 AI 기획기가 생성 단위와 요구사항 커버리지를 다시 계산하고 있습니다."
                    : "AI 기획기 캐시를 확인한 뒤 생성 단위와 요구사항 커버리지를 준비하고 있습니다."}
                </p>
                <div className="progress-bar is-live" aria-hidden="true">
                  <div className="progress-fill is-live" style={{ width: "42%" }} />
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

            {draftPlan?.coverage_warnings.length ? (
              <div className="draft-warning-list">
                {draftPlan.coverage_warnings.map((warning, index) => (
                  <p key={`coverage-${warning}-${index}`} className="draft-warning-item">
                    {warning}
                  </p>
                ))}
              </div>
            ) : null}

            {planError ? <p className="error-text">{planError}</p> : null}

            <div className="draft-prep-grid">
              <article className="mini-card draft-prep-card">
                <PrepCardTitle eyebrow="생성 확인" status={checklistStatus} title="생성 전 확인" />
                <ul className="plain-list">
                  <li>{initialRfpReady ? "RFP 추출 완료" : "RFP 추출 결과가 아직 없습니다."}</li>
                  <li>
                    {prepOutlineRows.length > 0
                      ? "목차 저장 완료"
                      : "목차 작성 페이지에서 목차를 먼저 저장해 주세요."}
                  </li>
                  <li>
                    {initialLinkedAssetCount > 0
                      ? `연결된 회사 자료 ${initialLinkedAssetCount}건`
                      : "연결된 회사 자료 없음"}
                  </li>
                </ul>
              </article>

              <article className="mini-card draft-prep-card">
                <PrepCardTitle eyebrow="작성 의도" status={authorIntentStatus} title="작성 의도" />
                <p className="card-copy">
                  강조할 강점, 원하는 추진 전략, 반드시 넣고 싶은 메시지를 적어두면 AI 기획기가
                  생성 단위와 요구사항 배치에 반영합니다.
                </p>
                <label className="field" style={{ marginTop: 12 }}>
                  <textarea
                    className="input-textarea"
                    onChange={(event) => setAuthorIntent(event.target.value)}
                    placeholder="예: 사업 수행 내용은 요구사항 중심으로 촘촘하게 작성. 추진 전략에는 애자일 운영, 컨소시엄 협업, 전문가 자문 체계를 강조."
                    rows={6}
                    value={authorIntent}
                  />
                </label>
                <div className="action-row draft-prep-intent-action" style={{ marginTop: 12 }}>
                  <span className={`status-pill draft-prep-intent-status ${hasUnsavedAuthorIntent ? "warn" : "ok"}`}>
                    {hasUnsavedAuthorIntent ? "의도 미저장" : "의도 저장됨"}
                  </span>
                  <button
                    className="button"
                    disabled={isSavingIntent}
                    onClick={() => void persistAuthorIntent({ reloadPlan: true })}
                    type="button"
                  >
                    {isSavingIntent ? "저장 중..." : "의도 저장 후 계획 갱신"}
                  </button>
                </div>
              </article>

              <article className="mini-card draft-prep-card">
                <PrepCardTitle eyebrow="계획 결과" status={plannerCardStatus} title="생성 단위와 커버리지" />
                <div className="status-row" style={{ marginTop: 0 }}>
                  <span className={`status-pill ${draftPlan?.planner_mode === "ai_v2" ? "ok" : "warn"}`}>
                    {draftPlan?.planner_mode === "ai_v2" ? "AI 계획" : "확인 필요"}
                  </span>
                  <span className="status-pill ok">{draftPlan?.generation_units.length ?? 0}개 생성 단위</span>
                  <span className={`status-pill ${coverageCount > 0 ? "ok" : "warn"}`}>
                    {coverageCount}개 요구사항 커버
                  </span>
                  <span className={`status-pill ${completedSearchCount > 0 ? "ok" : "warn"}`}>
                    검색 결과 {completedSearchCount}건
                  </span>
                  {draftPlan?.generation_requires_confirmation ? (
                    <span className="status-pill warn">사용자 확인 필요</span>
                  ) : null}
                </div>
                <p className="card-copy" style={{ marginTop: 12 }}>
                  {draftPlan?.planner_summary || "작성 의도와 RFP를 바탕으로 생성 단위와 요구사항 배치를 준비합니다."}
                </p>
                <div className="action-row draft-prep-card-action">
                  <button className="button" onClick={openSearchModal} type="button">
                    검색 내역 보기
                  </button>
                  <button
                    className="button"
                    disabled={!draftPlan?.generation_units.length && !draftPlan?.requirement_coverage.length}
                    onClick={openPlannerModal}
                    type="button"
                  >
                    자세히 보기
                  </button>
                </div>
              </article>

              <article className="mini-card draft-prep-card">
                <PrepCardTitle eyebrow="목차 미리보기" status={outlineCardStatus} title="현재 목차 구조" />
                {prepOutlineRows.length === 0 ? (
                  <p className="card-copy">저장된 목차가 없습니다.</p>
                ) : (
                  <p className="card-copy">{prepOutlineRows.length}개 목차가 저장되어 있습니다.</p>
                )}
                <div className="action-row draft-prep-card-action">
                  <button
                    className="button"
                    disabled={prepOutlineRows.length === 0}
                    onClick={openOutlineModal}
                    type="button"
                  >
                    자세히 보기
                  </button>
                </div>
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
              <div aria-live="polite" className="progress-shell is-live" role="status">
                <div className="progress-meta">
                  <div className="progress-heading">
                    <span aria-hidden="true" className="progress-indicator">
                      <span className="progress-indicator-ring" />
                      <span className="progress-indicator-core" />
                    </span>
                    <strong>초안 생성 중</strong>
                  </div>
                  <span className="subtle-copy">{generateProgress}%</span>
                </div>
                <p className="page-copy progress-live-copy" style={{ marginTop: 10 }}>
                  {DRAFT_GENERATION_PROGRESS_STEPS[generateStepIndex]}
                </p>
                <div className="progress-bar is-live" aria-hidden="true">
                  <div className="progress-fill is-live" style={{ width: `${generateProgress}%` }} />
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
            <p className="eyebrow">AI 편집 대화</p>
            <h2 className="card-title">대화형 수정</h2>
            <div className={`preview-box draft-selection-preview${hasCommittedSelection ? "" : " is-empty"}`}>
              <div className="draft-selection-preview-header">
                <p className="eyebrow">선택 텍스트</p>
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
                      초안 내용이 바뀌었습니다. 다시 선택한 뒤 `AI 편집`을 눌러 주세요.
                    </p>
                  ) : null}
                </>
              ) : (
                <p className="card-copy" style={{ marginTop: 0 }}>
                  초안 편집기에서 텍스트를 선택한 뒤 `AI 편집` 칩을 누르면 여기에 들어옵니다.
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
                      <span className="code-badge">{formatChatRole(message.role)}</span>
                      <span className="status-pill">
                        {formatApplyMode(message.apply_mode)}
                      </span>
                      {message.applied_at ? <span className="status-pill ok">적용됨</span> : null}
                    </div>
                    <p className="chat-message">{message.message_text}</p>
                    {message.selection_text ? (
                      <div className="preview-box" style={{ marginTop: 12 }}>
                        <p className="eyebrow">선택 원문</p>
                        <pre className="mono chat-code">{message.selection_text}</pre>
                      </div>
                    ) : null}
                    {message.role === "assistant" && message.suggestion_text ? (
                      <div className="preview-box" style={{ marginTop: 12 }}>
                        <p className="eyebrow">수정 제안</p>
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
            <p className="eyebrow">초안 다운로드</p>
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

      {isPlannerModalOpen ? (
        <div
          aria-hidden="true"
          className="modal-scrim"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closePlannerModal();
            }
          }}
        >
          <section
            aria-labelledby="planner-detail-modal-title"
            aria-modal="true"
            className="modal-card planner-modal-card"
            role="dialog"
          >
            <p className="eyebrow">계획 상세</p>
            <h2 className="card-title" id="planner-detail-modal-title">
              생성 단위와 요구사항 커버리지
            </h2>
            <p className="page-copy">
              현재 AI 기획기가 계산한 생성 단위와 요구사항 커버리지 전체 목록입니다.
            </p>

            <div className="planner-modal-grid">
              <section className="planner-modal-section">
                <div className="status-row" style={{ marginTop: 0 }}>
                  <span className="status-pill ok">{draftPlan?.generation_units.length ?? 0}개 생성 단위</span>
                  <span className={`status-pill ${coverageCount > 0 ? "ok" : "warn"}`}>
                    {coverageCount}개 요구사항 커버
                  </span>
                </div>
                <div className="planner-modal-scroll">
                  {draftPlan?.generation_units.length ? (
                    <div className="stack-list" style={{ marginTop: 12 }}>
                      {draftPlan.generation_units.map((unit) => (
                        <div key={unit.unit_key} className="preview-box" style={{ padding: 14 }}>
                          <p className="eyebrow" style={{ marginBottom: 6 }}>
                            {unit.section_heading_text}
                          </p>
                          <p style={{ margin: 0, fontWeight: 700 }}>{unit.unit_title}</p>
                          <p className="card-copy" style={{ marginTop: 8 }}>
                            {unit.unit_goal}
                          </p>
                          <p className="subtle-copy" style={{ marginTop: 6 }}>
                            작성 모드: {unit.writing_mode} / 패턴: {unit.unit_pattern}
                          </p>
                          {unit.required_aspects.length ? (
                            <p className="subtle-copy" style={{ marginTop: 6 }}>
                              작성 관점: {unit.required_aspects.join(", ")}
                            </p>
                          ) : null}
                          <p className="subtle-copy" style={{ marginTop: 8 }}>
                            주요 요구사항: {unit.primary_requirement_titles.join(", ") || "없음"}
                          </p>
                          {unit.secondary_requirement_titles.length ? (
                            <p className="subtle-copy" style={{ marginTop: 6 }}>
                              보조 반영: {unit.secondary_requirement_titles.join(", ")}
                            </p>
                          ) : null}
                          {unit.asset_titles.length ? (
                            <p className="subtle-copy" style={{ marginTop: 6 }}>
                              회사 자료: {unit.asset_titles.join(", ")}
                            </p>
                          ) : null}
                          {unit.search_topics.length ? (
                            <p className="subtle-copy" style={{ marginTop: 6 }}>
                              검색 주제: {unit.search_topics.join(", ")}
                            </p>
                          ) : null}
                          {unit.outline_fit_warning ? (
                            <p className="card-copy" style={{ marginTop: 8 }}>
                              주의: {unit.outline_fit_warning}
                            </p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="card-copy" style={{ marginTop: 12 }}>
                      생성 단위가 아직 없습니다.
                    </p>
                  )}
                </div>
              </section>

              <section className="planner-modal-section">
                <h3 className="card-title" style={{ fontSize: "1.05rem" }}>
                  요구사항 커버리지
                </h3>
                <div className="planner-modal-scroll">
                  {draftPlan?.requirement_coverage.length ? (
                    <div className="stack-list" style={{ marginTop: 12 }}>
                      {draftPlan.requirement_coverage.map((coverage) => (
                        <div key={coverage.requirement_id} className="preview-box" style={{ padding: 14 }}>
                          <p style={{ margin: 0, fontWeight: 700 }}>{coverage.requirement_label}</p>
                          <p className="subtle-copy" style={{ marginTop: 8 }}>
                            주요 생성 단위: {coverage.primary_unit_key}
                          </p>
                          <p className="subtle-copy" style={{ marginTop: 6 }}>
                            연결 목차 ID: {coverage.primary_outline_section_id}
                          </p>
                          {coverage.secondary_unit_keys.length ? (
                            <p className="subtle-copy" style={{ marginTop: 6 }}>
                              보조 생성 단위: {coverage.secondary_unit_keys.join(", ")}
                            </p>
                          ) : null}
                          {coverage.rationale ? (
                            <p className="card-copy" style={{ marginTop: 8 }}>
                              {coverage.rationale}
                            </p>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="card-copy" style={{ marginTop: 12 }}>
                      요구사항 커버리지가 아직 없습니다.
                    </p>
                  )}
                </div>
              </section>
            </div>

            <div className="action-row modal-actions">
              <button className="button" onClick={closePlannerModal} type="button">
                닫기
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {isSearchModalOpen ? (
        <div
          aria-hidden="true"
          className="modal-scrim"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeSearchModal();
            }
          }}
        >
          <section aria-labelledby="search-detail-modal-title" aria-modal="true" className="modal-card planner-modal-card" role="dialog">
            <p className="eyebrow">검색 내역</p>
            <h2 className="card-title" id="search-detail-modal-title">
              planned / adaptive 검색 결과
            </h2>
            <div className="status-row" style={{ marginTop: 12 }}>
              <span className="status-pill ok">완료 {completedSearchCount}건</span>
              <span className={`status-pill ${adaptiveSearchCount > 0 ? "ok" : "warn"}`}>
                adaptive {adaptiveSearchCount}건
              </span>
            </div>
            <div className="planner-modal-scroll" style={{ marginTop: 16 }}>
              {isLoadingSearchTasks ? (
                <p className="card-copy">검색 내역을 불러오는 중입니다.</p>
              ) : searchTasks.length === 0 ? (
                <p className="card-copy">아직 저장된 검색 내역이 없습니다.</p>
              ) : (
                <div className="stack-list">
                  {searchTasks.map((task) => (
                    <div key={task.id} className="preview-box" style={{ padding: 14 }}>
                      <div className="status-row" style={{ marginTop: 0 }}>
                        <span className={`status-pill ${task.source_stage === "adaptive" ? "warn" : "ok"}`}>
                          {task.source_stage}
                        </span>
                        <span className={`status-pill ${task.status === "done" ? "ok" : task.status === "failed" ? "warn" : ""}`}>
                          {task.status}
                        </span>
                      </div>
                      <p style={{ margin: "8px 0 0", fontWeight: 700 }}>{task.topic}</p>
                      {task.purpose ? <p className="subtle-copy" style={{ marginTop: 6 }}>목적: {task.purpose}</p> : null}
                      {task.reason ? <p className="card-copy" style={{ marginTop: 8 }}>{task.reason}</p> : null}
                      {task.result_summary ? <pre className="mono chat-code" style={{ marginTop: 12 }}>{task.result_summary}</pre> : null}
                      {task.citations.length ? (
                        <div style={{ marginTop: 12 }}>
                          <p className="eyebrow">출처</p>
                          <div className="stack-list">
                            {task.citations.map((citation, index) => (
                              <a key={`${task.id}-${citation.url}-${index}`} className="card-copy" href={citation.url} rel="noreferrer" target="_blank">
                                {citation.title}
                              </a>
                            ))}
                          </div>
                        </div>
                      ) : null}
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="action-row modal-actions">
              <button className="button" onClick={closeSearchModal} type="button">
                닫기
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {isCoverageModalOpen ? (
        <div
          aria-hidden="true"
          className="modal-scrim"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeCoverageModal();
            }
          }}
        >
          <section
            aria-labelledby="coverage-warning-modal-title"
            aria-modal="true"
            className="modal-card"
            role="dialog"
          >
            <p className="eyebrow">생성 전 확인</p>
            <h2 className="card-title" id="coverage-warning-modal-title">
              현재 목차로 생성해도 될지 확인해 주세요
            </h2>
            <p className="page-copy">
              AI 기획기가 현재 목차 구조에서 요구사항 커버 품질이 떨어질 수 있다고 판단했습니다.
              그대로 생성할 수도 있지만, 목차를 보완하면 품질이 더 좋아질 수 있습니다.
            </p>
            <div className="draft-warning-list" style={{ marginTop: 16 }}>
              {(draftPlan?.coverage_warnings ?? []).map((warning, index) => (
                <p key={`modal-warning-${index}`} className="draft-warning-item">
                  {warning}
                </p>
              ))}
            </div>
            <div className="action-row modal-actions">
              <button className="secondary-button" onClick={closeCoverageModal} type="button">
                취소
              </button>
              <button
                className="button"
                disabled={isGenerating}
                onClick={() => void handleGenerateDraft(true)}
                type="button"
              >
                {isGenerating ? "초안 생성 중..." : "동의 후 생성"}
              </button>
            </div>
          </section>
        </div>
      ) : null}

      {isOutlineModalOpen ? (
        <div
          aria-hidden="true"
          className="modal-scrim"
          onClick={(event) => {
            if (event.target === event.currentTarget) {
              closeOutlineModal();
            }
          }}
        >
          <section
            aria-labelledby="outline-detail-modal-title"
            aria-modal="true"
            className="modal-card outline-modal-card"
            role="dialog"
          >
            <p className="eyebrow">목차 상세</p>
            <h2 className="card-title" id="outline-detail-modal-title">
              현재 목차 구조
            </h2>
            <p className="page-copy">저장된 목차 전체를 확인합니다.</p>
            <div className="planner-modal-scroll" style={{ marginTop: 16 }}>
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
            </div>
            <div className="action-row modal-actions">
              <button className="button" onClick={closeOutlineModal} type="button">
                닫기
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </section>
  );
}
