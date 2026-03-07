import type { OpenQuestion } from "@/lib/types";

type OpenQuestionPanelProps = {
  questions: OpenQuestion[];
  onResolve: (questionId: string, nextStatus: "open" | "resolved") => Promise<void>;
  pendingQuestionId: string | null;
};

export function OpenQuestionPanel({
  questions,
  onResolve,
  pendingQuestionId
}: OpenQuestionPanelProps) {
  return (
    <aside className="panel-stack">
      <div className="question-list">
        <p className="eyebrow">Review Items</p>
        <h2 className="card-title">작성 확인 사항</h2>
        {questions.length === 0 ? <p className="card-copy">현재 생성된 확인 사항이 없습니다.</p> : null}
        {questions.map((question) => (
          <div key={question.id} className="question-item">
            <div className="status-row" style={{ marginTop: 0 }}>
              <span className="code-badge">{question.section_heading_text || "목차 미상"}</span>
              <span className={`status-pill ${question.status === "open" ? "warn" : "ok"}`}>
                {question.status}
              </span>
              <span className="status-pill">{question.category}</span>
              <span className={`status-pill ${question.severity === "high" ? "warn" : "ok"}`}>
                {question.severity}
              </span>
            </div>
            <p className="card-copy" style={{ marginTop: 10 }}>
              {question.question_text}
            </p>
            <p className="subtle-copy" style={{ marginTop: 8 }}>
              source: {question.source_agent}
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
