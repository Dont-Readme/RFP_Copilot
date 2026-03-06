type MarkdownPreviewProps = {
  content: string;
};

export function MarkdownPreview({ content }: MarkdownPreviewProps) {
  return (
    <div className="preview-box">
      <p className="eyebrow">Markdown Preview</p>
      <pre className="mono" style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>
        {content}
      </pre>
    </div>
  );
}
