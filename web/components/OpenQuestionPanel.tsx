import type { OpenQuestion } from "@/lib/types";

type OpenQuestionPanelProps = {
  questions: OpenQuestion[];
  onResolve: (questionId: string, nextStatus: "open" | "resolved") => Promise<void>;
  pendingQuestionId: string | null;
};

function formatQuestionStatus(status: OpenQuestion["status"]): string {
  return status === "resolved" ? "해결됨" : "미해결";
}

function formatQuestionSeverity(severity: string): string {
  if (severity === "high") {
    return "높음";
  }
  if (severity === "medium") {
    return "보통";
  }
  if (severity === "low") {
    return "낮음";
  }
  return severity;
}

function formatSourceAgent(agent: string): string {
  if (agent === "system") {
    return "시스템";
  }
  if (agent === "writer") {
    return "작성기";
  }
  if (agent === "researcher") {
    return "리서처";
  }
  if (agent === "chat") {
    return "AI 편집";
  }
  return agent;
}

export function OpenQuestionPanel({
  questions,
  onResolve,
  pendingQuestionId
}: OpenQuestionPanelProps) {
  return (
    <aside className="panel-stack">
      <div className="question-list">
        <p className="eyebrow">확인 항목</p>
        <h2 className="card-title">작성 확인 사항</h2>
        {questions.length === 0 ? <p className="card-copy">현재 생성된 확인 사항이 없습니다.</p> : null}
        {questions.map((question) => (
          <div key={question.id} className="question-item">
            <div className="status-row" style={{ marginTop: 0 }}>
              <span className="code-badge">{question.section_heading_text || "목차 미상"}</span>
              <span className={`status-pill ${question.status === "open" ? "warn" : "ok"}`}>
                {formatQuestionStatus(question.status)}
              </span>
              <span className="status-pill">{question.category}</span>
              <span className={`status-pill ${question.severity === "high" ? "warn" : "ok"}`}>
                {formatQuestionSeverity(question.severity)}
              </span>
            </div>
            <p className="card-copy" style={{ marginTop: 10 }}>
              {question.question_text}
            </p>
            <p className="subtle-copy" style={{ marginTop: 8 }}>
              생성 주체: {formatSourceAgent(question.source_agent)}
            </p>
            <div className="action-row">
              {question.status === "open" ? (
                <button
                  className="button"
                  disabled={pendingQuestionId === question.id}
                  onClick={() => onResolve(question.id, "resolved")}
                  type="button"
                >
                  {pendingQuestionId === question.id ? "처리 중..." : "해결 처리"}
                </button>
              ) : (
                <button
                  className="secondary-button"
                  disabled={pendingQuestionId === question.id}
                  onClick={() => onResolve(question.id, "open")}
                  type="button"
                >
                  다시 열기
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
