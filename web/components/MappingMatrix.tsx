type MappingRow = {
  code: string;
  evaluationTitle: string;
  sectionTitle: string;
  strengthLabel: "strong" | "weak" | "missing";
  strengthScore: number;
  rationaleText: string;
};

type MappingMatrixProps = {
  rows: MappingRow[];
};

export function MappingMatrix({ rows }: MappingMatrixProps) {
  return (
    <div className="content-panel">
      <table className="mapping-table">
        <thead>
          <tr>
            <th>평가항목</th>
            <th>초안 섹션</th>
            <th>강도</th>
            <th>근거</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.code}-${row.evaluationTitle}`}>
              <td>
                <div className="code-badge">{row.code}</div>
                <div style={{ marginTop: 8 }}>{row.evaluationTitle}</div>
              </td>
              <td>{row.sectionTitle}</td>
              <td>
                <span className={`status-pill ${row.strengthLabel === "strong" ? "ok" : "warn"}`}>
                  {row.strengthLabel}
                </span>
              </td>
              <td>
                <div>{row.rationaleText}</div>
                <div className="subtle-copy">score: {row.strengthScore.toFixed(3)}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
