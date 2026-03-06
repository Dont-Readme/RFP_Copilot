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
        <p className="eyebrow">Open Questions</p>
        <h2 className="card-title">질문 패널</h2>
        {questions.length === 0 ? <p className="card-copy">현재 열린 질문이 없습니다.</p> : null}
        {questions.map((question) => (
          <div key={question.id} className="question-item">
            <div className="status-row" style={{ marginTop: 0 }}>
              <span className="code-badge">{question.id}</span>
              <span className={`status-pill ${question.status === "open" ? "warn" : "ok"}`}>
                {question.status}
              </span>
            </div>
            <p className="card-copy">{question.question_text}</p>
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
