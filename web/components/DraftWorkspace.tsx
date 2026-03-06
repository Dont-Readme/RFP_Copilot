"use client";

import { useMemo, useState } from "react";

import {
  applyDraftChatMessage,
  createDraftChatTurn,
  updateDraftSection,
  updateQuestion
} from "@/lib/api";
import type { DraftChatMessage, DraftSection, OpenQuestion } from "@/lib/types";
import { EditorTextarea } from "@/components/EditorTextarea";
import { OpenQuestionPanel } from "@/components/OpenQuestionPanel";
import { SystemNotice } from "@/components/SystemNotice";

type DraftWorkspaceProps = {
  projectId: number;
  initialSection: DraftSection;
  initialQuestions: OpenQuestion[];
  initialChatMessages: DraftChatMessage[];
};

type SelectionState = {
  start: number;
  end: number;
  text: string;
};

function extractSystemNotices(content: string): string[] {
  return content
    .split("\n")
    .filter((line) => line.includes("[확인 필요(시스템)]"))
    .map((line) => line.replace("[확인 필요(시스템)]", "").trim())
    .filter(Boolean);
}

export function DraftWorkspace({
  projectId,
  initialSection,
  initialQuestions,
  initialChatMessages
}: DraftWorkspaceProps) {
  const [content, setContent] = useState(initialSection.content_md);
  const [questions, setQuestions] = useState(initialQuestions);
  const [chatMessages, setChatMessages] = useState(initialChatMessages);
  const [selection, setSelection] = useState<SelectionState>({ start: 0, end: 0, text: "" });
  const [chatInput, setChatInput] = useState("");
  const [statusLabel, setStatusLabel] = useState(initialSection.status);
  const [isSaving, setIsSaving] = useState(false);
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [applyingMessageId, setApplyingMessageId] = useState<number | null>(null);
  const [pendingQuestionId, setPendingQuestionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const notices = useMemo(() => extractSystemNotices(content), [content]);

  async function handleSave() {
    try {
      setIsSaving(true);
      setError(null);
      const updated = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setStatusLabel(updated.status);
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
      const synced = await updateDraftSection(projectId, initialSection.id, { content_md: content });
      setStatusLabel(synced.status);
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
      const response = await applyDraftChatMessage(projectId, messageId);
      setContent(response.section.content_md);
      setStatusLabel(response.section.status);
      setChatMessages((current) =>
        current.map((message) => (message.id === messageId ? response.message : message))
      );
    } catch (applyError) {
      setError(applyError instanceof Error ? applyError.message : "AI 제안 적용에 실패했습니다.");
    } finally {
      setApplyingMessageId(null);
    }
  }

  return (
    <section className="split-layout" style={{ marginTop: 24 }}>
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
          title={initialSection.title}
          value={content}
        />

        <div className="content-panel">
          <p className="eyebrow">Editor Actions</p>
          <h2 className="card-title">저장 및 선택 상태</h2>
          <p className="card-copy">
            선택된 텍스트: {selection.text.trim() || "선택된 구간 없음"}
          </p>
          <div className="action-row">
            <button className="secondary-button" disabled={isSaving} onClick={() => void handleSave()} type="button">
              {isSaving ? "저장 중..." : "초안 저장"}
            </button>
          </div>
          {error ? <p className="error-text">{error}</p> : null}
        </div>
      </section>

      <aside className="panel-stack">
        <section className="question-list">
          <p className="eyebrow">AI Edit Chat</p>
          <h2 className="card-title">대화형 수정</h2>
          <p className="card-copy">
            선택 구간이 있으면 해당 문장만 수정 제안을 만들고, 없으면 현재 초안에 대한 편집 가이드를
            반환합니다.
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
  );
}
