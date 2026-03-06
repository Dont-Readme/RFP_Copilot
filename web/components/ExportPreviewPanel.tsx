import { MarkdownPreview } from "@/components/MarkdownPreview";
import { buildExportDownloadUrl } from "@/lib/api";

type ExportPreviewPanelProps = {
  projectId: number;
  exportSessionId: string;
  previewMd: string;
  formats: string[];
};

export function ExportPreviewPanel({
  projectId,
  exportSessionId,
  previewMd,
  formats
}: ExportPreviewPanelProps) {
  return (
    <div className="split-layout" style={{ marginTop: 0 }}>
      <section className="preview-shell">
        <MarkdownPreview content={previewMd} />
      </section>
      <section className="panel-stack">
        <div className="mini-card">
          <p className="eyebrow">Actions</p>
          <h2 className="card-title">다음 단계</h2>
          <div className="action-row">
            <a className="button" href={`/projects/${projectId}/draft`}>
              편집기로 돌아가기
            </a>
          </div>
          <div className="download-list">
            {formats.map((format) => (
              <a
                key={format}
                className="secondary-button"
                href={buildExportDownloadUrl(projectId, exportSessionId, format)}
                target="_blank"
              >
                {format} 다운로드
              </a>
            ))}
          </div>
        </div>
        <div className="mini-card">
          <p className="eyebrow">Formats</p>
          <h2 className="card-title">생성 대상</h2>
          <div className="status-row">
            {formats.map((format) => (
              <span key={format} className="status-pill ok">
                {format}
              </span>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
