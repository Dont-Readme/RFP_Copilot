"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

type EditorSelection = {
  start: number;
  end: number;
  text: string;
};

type ChipPosition = {
  left: number;
  top: number;
};

type EditorTextareaProps = {
  title: string;
  status: string;
  value: string;
  selection: EditorSelection;
  onChange: (value: string) => void;
  onSelectionChange: (selection: EditorSelection) => void;
  onCommitSelection: (selection: EditorSelection) => void;
};

function hasSelection(selection: EditorSelection): boolean {
  return selection.start !== selection.end && selection.text.length > 0;
}

function measureSelectionAnchor(
  textarea: HTMLTextAreaElement,
  selectionStart: number
): { left: number; top: number; lineHeight: number } | null {
  const computed = window.getComputedStyle(textarea);
  const mirror = document.createElement("div");
  const marker = document.createElement("span");

  mirror.style.position = "absolute";
  mirror.style.visibility = "hidden";
  mirror.style.pointerEvents = "none";
  mirror.style.whiteSpace = "pre-wrap";
  mirror.style.overflowWrap = "break-word";
  mirror.style.wordBreak = "break-word";
  mirror.style.top = "0";
  mirror.style.left = "-9999px";
  mirror.style.width = `${textarea.clientWidth}px`;
  mirror.style.padding = computed.padding;
  mirror.style.border = computed.border;
  mirror.style.boxSizing = computed.boxSizing;
  mirror.style.fontFamily = computed.fontFamily;
  mirror.style.fontSize = computed.fontSize;
  mirror.style.fontWeight = computed.fontWeight;
  mirror.style.fontStyle = computed.fontStyle;
  mirror.style.letterSpacing = computed.letterSpacing;
  mirror.style.lineHeight = computed.lineHeight;
  mirror.style.textTransform = computed.textTransform;
  mirror.style.textIndent = computed.textIndent;
  mirror.style.tabSize = computed.tabSize;

  mirror.textContent = textarea.value.slice(0, selectionStart);
  marker.textContent = "\u200b";
  mirror.appendChild(marker);
  document.body.appendChild(mirror);

  const lineHeight = Number.parseFloat(computed.lineHeight) || Number.parseFloat(computed.fontSize) * 1.7 || 24;
  const measured = {
    left: marker.offsetLeft - textarea.scrollLeft,
    top: marker.offsetTop - textarea.scrollTop,
    lineHeight
  };

  document.body.removeChild(mirror);
  return measured;
}

export function EditorTextarea({
  title,
  status,
  value,
  selection,
  onChange,
  onSelectionChange,
  onCommitSelection
}: EditorTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const [chipPosition, setChipPosition] = useState<ChipPosition | null>(null);

  const syncSelectionFromTextarea = useCallback(
    (element: HTMLTextAreaElement) => {
      onSelectionChange({
        start: element.selectionStart,
        end: element.selectionEnd,
        text: element.value.slice(element.selectionStart, element.selectionEnd)
      });
    },
    [onSelectionChange]
  );

  const updateChipPosition = useCallback(() => {
    const textarea = textareaRef.current;
    if (!textarea || !hasSelection(selection)) {
      setChipPosition(null);
      return;
    }

    const measured = measureSelectionAnchor(textarea, selection.start);
    if (!measured) {
      setChipPosition(null);
      return;
    }

    // Hide the chip when the selection start line is outside the visible textarea viewport.
    if (measured.top < 0 || measured.top > textarea.clientHeight - measured.lineHeight) {
      setChipPosition(null);
      return;
    }

    const chipWidth = 84;
    const chipHeight = 34;
    const textareaRect = textarea.getBoundingClientRect();
    const nextLeft = Math.min(
      Math.max(textareaRect.left + 8, textareaRect.left + measured.left),
      Math.max(textareaRect.left + 8, textareaRect.right - chipWidth - 8)
    );

    let nextTop = textareaRect.top + measured.top - chipHeight - 8;
    if (nextTop < textareaRect.top + 8) {
      nextTop = textareaRect.top + measured.top + measured.lineHeight + 8;
    }
    nextTop = Math.min(
      Math.max(textareaRect.top + 8, nextTop),
      Math.max(textareaRect.top + 8, textareaRect.bottom - chipHeight - 8)
    );

    setChipPosition({
      left: nextLeft,
      top: nextTop
    });
  }, [selection]);

  useLayoutEffect(() => {
    updateChipPosition();
  }, [updateChipPosition, value]);

  useEffect(() => {
    const handleResize = () => updateChipPosition();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [updateChipPosition]);

  useEffect(() => {
    const handleScroll = () => updateChipPosition();
    window.addEventListener("scroll", handleScroll, true);
    return () => window.removeEventListener("scroll", handleScroll, true);
  }, [updateChipPosition]);

  return (
    <section className="editor-shell">
      <div className="editor-box">
        <p className="eyebrow">Draft Editor</p>
        <div className="status-row" style={{ marginTop: 0, marginBottom: 12 }}>
          <span className="status-pill ok">{title}</span>
          <span className="status-pill">{status}</span>
        </div>
        <div className="editor-input-shell">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onBlur={() => onSelectionChange({ start: 0, end: 0, text: "" })}
            onKeyUp={(event) => syncSelectionFromTextarea(event.currentTarget)}
            onMouseUp={(event) => syncSelectionFromTextarea(event.currentTarget)}
            onScroll={() => updateChipPosition()}
            onSelect={(event) => {
              syncSelectionFromTextarea(event.currentTarget);
            }}
          />
        </div>
      </div>
      {chipPosition && hasSelection(selection) ? (
        <button
          className="editor-selection-chip"
          onClick={() => {
            const textarea = textareaRef.current;
            onCommitSelection(selection);
            onSelectionChange({ start: 0, end: 0, text: "" });
            if (textarea) {
              textarea.setSelectionRange(selection.end, selection.end);
            }
          }}
          onMouseDown={(event) => event.preventDefault()}
          style={{ left: chipPosition.left, top: chipPosition.top, position: "fixed" }}
          type="button"
        >
          AI EDIT
        </button>
      ) : null}
    </section>
  );
}
