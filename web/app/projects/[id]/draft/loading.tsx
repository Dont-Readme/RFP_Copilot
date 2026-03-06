export default function DraftLoading() {
  return (
    <main className="page-shell">
      <section className="detail-panel">
        <p className="eyebrow">Draft Editor</p>
        <h1 className="card-title">Draft Workspace Loading</h1>
        <p className="page-copy">
          저장된 초안, 질문, 목차, 연결 자료를 불러오고 있습니다.
        </p>
      </section>

      <section className="content-panel section-spacer">
        <div className="progress-shell" style={{ marginTop: 0 }}>
          <div className="progress-meta">
            <strong>화면 준비 중</strong>
            <span className="subtle-copy">loading</span>
          </div>
          <p className="page-copy" style={{ marginTop: 10 }}>
            Draft Editor 진입에 필요한 데이터를 서버에서 정리하고 있습니다.
          </p>
          <div className="progress-bar" aria-hidden="true">
            <div className="progress-fill" style={{ width: "42%" }} />
          </div>
        </div>
      </section>
    </main>
  );
}
