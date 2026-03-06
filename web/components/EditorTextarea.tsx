"use client";

type EditorTextareaProps = {
  title: string;
  status: string;
  value: string;
  onChange: (value: string) => void;
  onSelectionChange: (selection: { start: number; end: number; text: string }) => void;
};

export function EditorTextarea({
  title,
  status,
  value,
  onChange,
  onSelectionChange
}: EditorTextareaProps) {
  return (
    <section className="editor-shell">
      <div className="editor-box">
        <p className="eyebrow">Draft Editor</p>
        <div className="status-row" style={{ marginTop: 0, marginBottom: 12 }}>
          <span className="status-pill ok">{title}</span>
          <span className="status-pill">{status}</span>
        </div>
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onSelect={(event) => {
            const element = event.target as HTMLTextAreaElement;
            onSelectionChange({
              start: element.selectionStart,
              end: element.selectionEnd,
              text: element.value.slice(element.selectionStart, element.selectionEnd)
            });
          }}
        />
      </div>
    </section>
  );
}
