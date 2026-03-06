"use client";

import { useEffect, useState } from "react";

import {
  deleteRfpFile,
  rerunRfpExtraction,
  updateRfpExtraction,
  uploadRfpFile
} from "@/lib/api";
import type { ProjectFile, RfpExtraction } from "@/lib/types";

type RfpWorkspaceProps = {
  projectId: number;
  initialExtraction: RfpExtraction;
};

type PendingUpload = {
  localId: string;
  file: File;
  role: ProjectFile["role"];
};

const FILE_ROLE_OPTIONS: Array<{ value: ProjectFile["role"]; label: string }> = [
  { value: "notice", label: "공고문" },
  { value: "sow", label: "과업지시서" },
  { value: "rfp", label: "제안요청서" },
  { value: "other", label: "기타" }
];

const FILE_ROLE_LABELS: Record<ProjectFile["role"], string> = {
  notice: "공고문",
  sow: "과업지시서",
  rfp: "제안요청서",
  requirements: "요구사항정의서",
  other: "기타"
};

const EXTRACTION_PROGRESS_STEPS = [
  "선택한 파일에서 텍스트와 chunk를 정리하고 있습니다.",
  "사업 개요와 요구사항 프롬프트를 OpenAI에 요청하고 있습니다.",
  "응답을 병합하고 검토용 형식으로 정리하고 있습니다."
];

function formatFileRole(role: ProjectFile["role"]): string {
  return FILE_ROLE_LABELS[role] ?? role;
}

function formatBytes(size: number): string {
  if (size < 1024) {
    return `${size} B`;
  }
  if (size < 1024 * 1024) {
    return `${(size / 1024).toFixed(1)} KB`;
  }
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function createPendingUpload(file: File, role: ProjectFile["role"]): PendingUpload {
  return {
    localId: `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    file,
    role
  };
}

export function RfpWorkspace({ projectId, initialExtraction }: RfpWorkspaceProps) {
  const [extraction, setExtraction] = useState<RfpExtraction>({
    ...initialExtraction,
    evaluation_items: []
  });
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState<ProjectFile["role"]>("notice");
  const [fileInputKey, setFileInputKey] = useState(0);
  const [pendingUploads, setPendingUploads] = useState<PendingUpload[]>([]);
  const [selectedFileIds, setSelectedFileIds] = useState<number[]>(
    initialExtraction.files.map((uploadedFile) => uploadedFile.id)
  );
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadLabel, setUploadLabel] = useState("");
  const [isReextracting, setIsReextracting] = useState(false);
  const [extractProgress, setExtractProgress] = useState(8);
  const [extractStepIndex, setExtractStepIndex] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const availableIds = extraction.files.map((uploadedFile) => uploadedFile.id);
    setSelectedFileIds((current) => {
      if (availableIds.length === 0) {
        return [];
      }

      const filtered = current.filter((fileId) => availableIds.includes(fileId));
      if (filtered.length === 0) {
        return availableIds;
      }

      const next = [...filtered];
      for (const fileId of availableIds) {
        if (!next.includes(fileId)) {
          next.push(fileId);
        }
      }
      return next;
    });
  }, [extraction.files]);

  useEffect(() => {
    if (!isReextracting) {
      setExtractProgress(8);
      setExtractStepIndex(0);
      return;
    }

    const startedAt = Date.now();
    const intervalId = window.setInterval(() => {
      const elapsed = Date.now() - startedAt;
      const nextProgress = Math.min(92, 12 + Math.floor(elapsed / 1300) * 4);
      const nextStepIndex = Math.min(
        EXTRACTION_PROGRESS_STEPS.length - 1,
        Math.floor(elapsed / 7000)
      );
      setExtractProgress((current) => Math.max(current, nextProgress));
      setExtractStepIndex(nextStepIndex);
    }, 900);

    return () => window.clearInterval(intervalId);
  }, [isReextracting]);

  function resetFilePicker() {
    setFile(null);
    setFileInputKey((current) => current + 1);
  }

  function handleQueueAdd() {
    if (!file) {
      setError("대기 목록에 추가할 파일을 선택해 주세요.");
      return;
    }

    setPendingUploads((current) => [...current, createPendingUpload(file, role)]);
    setError(null);
    resetFilePicker();
  }

  function updatePendingRole(localId: string, nextRole: ProjectFile["role"]) {
    setPendingUploads((current) =>
      current.map((item) => (item.localId === localId ? { ...item, role: nextRole } : item))
    );
  }

  function removePendingUpload(localId: string) {
    setPendingUploads((current) => current.filter((item) => item.localId !== localId));
  }

  async function handleUploadPendingFiles() {
    if (pendingUploads.length === 0) {
      setError("먼저 대기 목록에 파일을 추가해 주세요.");
      return;
    }

    const queueSnapshot = [...pendingUploads];
    const completedIds = new Set<string>();

    try {
      setIsUploading(true);
      setUploadProgress(6);
      setUploadLabel("대기 목록 업로드를 준비하고 있습니다.");
      setError(null);

      for (const [index, item] of queueSnapshot.entries()) {
        setUploadLabel(`업로드 중 ${index + 1}/${queueSnapshot.length}: ${item.file.name}`);
        const response = await uploadRfpFile(projectId, { file: item.file, role: item.role });
        completedIds.add(item.localId);
        setExtraction(response.extraction);
        setSelectedFileIds((current) =>
          current.includes(response.file.id) ? current : [...current, response.file.id]
        );
        setUploadProgress(Math.round(((index + 1) / queueSnapshot.length) * 100));
      }

      setPendingUploads((current) => current.filter((item) => !completedIds.has(item.localId)));
      resetFilePicker();
    } catch (uploadError) {
      setPendingUploads((current) => current.filter((item) => !completedIds.has(item.localId)));
      setError(
        uploadError instanceof Error ? uploadError.message : "RFP 파일 업로드에 실패했습니다."
      );
    } finally {
      setIsUploading(false);
      setUploadLabel("");
      setUploadProgress(0);
    }
  }

  async function handleDeleteFile(fileId: number) {
    try {
      setDeletingFileId(fileId);
      setError(null);
      await deleteRfpFile(projectId, fileId);
      setSelectedFileIds((current) => current.filter((candidate) => candidate !== fileId));
      setExtraction((current) => {
        const nextFiles = current.files.filter((candidate) => candidate.id !== fileId);
        if (nextFiles.length === 0) {
          return {
            ...current,
            status: "draft",
            raw_text: "",
            project_summary_text: "",
            ocr_required: false,
            files: [],
            requirements: [],
            evaluation_items: []
          };
        }
        return {
          ...current,
          files: nextFiles
        };
      });
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "업로드 파일 삭제에 실패했습니다.");
    } finally {
      setDeletingFileId(null);
    }
  }

  async function handleReextract() {
    if (pendingUploads.length > 0) {
      setError("대기 목록에 남아 있는 파일을 먼저 업로드해 주세요.");
      return;
    }

    if (selectedFileIds.length === 0) {
      setError("추출에 사용할 업로드 파일을 하나 이상 체크해 주세요.");
      return;
    }

    try {
      setIsReextracting(true);
      setError(null);
      const updated = await rerunRfpExtraction(projectId, { file_ids: selectedFileIds });
      setExtraction(updated);
    } catch (extractError) {
      setError(extractError instanceof Error ? extractError.message : "RFP 재추출에 실패했습니다.");
    } finally {
      setIsReextracting(false);
    }
  }

  async function handleSave(nextStatus: "draft" | "confirmed") {
    try {
      setIsSaving(true);
      setError(null);
      const updated = await updateRfpExtraction(projectId, {
        ...extraction,
        status: nextStatus
      });
      setExtraction(updated);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "추출 결과 저장에 실패했습니다.");
    } finally {
      setIsSaving(false);
    }
  }

  function toggleUploadedFile(fileId: number) {
    setSelectedFileIds((current) =>
      current.includes(fileId)
        ? current.filter((candidate) => candidate !== fileId)
        : [...current, fileId]
    );
  }

  function updateRequirement(
    index: number,
    field: "requirement_no" | "name" | "definition" | "details",
    value: string
  ) {
    setExtraction((current) => ({
      ...current,
      requirements: current.requirements.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item
      )
    }));
  }

  function addRequirementRow() {
    setExtraction((current) => ({
      ...current,
      requirements: [
        ...current.requirements,
        {
          id: Date.now(),
          project_id: current.project_id,
          sort_order: current.requirements.length + 1,
          requirement_no: "",
          name: "",
          definition: "",
          details: "",
          created_at: new Date().toISOString()
        }
      ]
    }));
  }

  function removeRequirementRow(index: number) {
    setExtraction((current) => ({
      ...current,
      requirements: current.requirements.filter((_, itemIndex) => itemIndex !== index)
    }));
  }

  return (
    <section className="panel-stack section-spacer">
      {error ? (
        <section className="content-panel system-notice">
          <p className="eyebrow">Attention</p>
          <h2 className="card-title">작업 중 오류가 발생했습니다</h2>
          <p className="error-text">{error}</p>
        </section>
      ) : null}

      <section className="content-panel">
        <p className="eyebrow">Upload</p>
        <h2 className="card-title">공고 파일 업로드</h2>
        <p className="page-copy">
          파일 유형을 선택한 뒤 대기 목록에 쌓고, 한 번에 업로드한 다음 추출에 사용할 파일만 체크해
          OpenAI 추출을 실행합니다. 추출 프롬프트는 `api/app/services/rfp_prompts.py`에서
          섹션별로 수정할 수 있습니다.
        </p>

        <div className="rfp-upload-grid">
          <label className="field">
            <span>파일 유형</span>
            <select value={role} onChange={(event) => setRole(event.target.value as ProjectFile["role"])}>
              {FILE_ROLE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label className="secondary-button" htmlFor="rfp-file-upload">
            파일 선택
          </label>
          <input
            key={fileInputKey}
            hidden
            id="rfp-file-upload"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button
            className="button"
            disabled={!file || isUploading}
            onClick={handleQueueAdd}
            type="button"
          >
            리스트에 추가
          </button>
        </div>

        {file ? <p className="page-copy">선택 파일: {file.name}</p> : null}

        <div className="rfp-upload-subsection section-spacer">
          <div className="toolbar">
            <div>
              <p className="eyebrow">Pending Queue</p>
              <h3 className="card-title">업로드 대기 목록</h3>
              <p className="page-copy">아래 목록을 확인한 뒤 한 번에 업로드하세요.</p>
            </div>
            <button
              className="button"
              disabled={isUploading || pendingUploads.length === 0}
              onClick={() => void handleUploadPendingFiles()}
              type="button"
            >
              {isUploading ? "업로드 중..." : "대기 목록 업로드"}
            </button>
          </div>

          {isUploading ? (
            <div className="progress-shell">
              <div className="progress-meta">
                <strong>업로드 진행 중</strong>
                <span>{uploadProgress}%</span>
              </div>
              <div className="progress-bar" aria-hidden="true">
                <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
              </div>
              <p className="page-copy">{uploadLabel || "파일을 서버에 저장하고 있습니다."}</p>
            </div>
          ) : null}

          <div className="stack-list section-spacer">
            {pendingUploads.length === 0 ? (
              <p className="page-copy">업로드 대기 중인 파일이 없습니다.</p>
            ) : (
              pendingUploads.map((item) => (
                <article key={item.localId} className="mini-card rfp-file-card">
                  <div className="rfp-file-main">
                    <div className="rfp-file-meta">
                      <h3>{item.file.name}</h3>
                      <p className="card-copy">{formatBytes(item.file.size)}</p>
                    </div>
                  </div>
                  <div className="rfp-file-actions">
                    <label className="field">
                      <span>유형</span>
                      <select
                        value={item.role}
                        onChange={(event) =>
                          updatePendingRole(item.localId, event.target.value as ProjectFile["role"])
                        }
                      >
                        {FILE_ROLE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="secondary-button"
                      onClick={() => removePendingUpload(item.localId)}
                      type="button"
                    >
                      제거
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>

        <div className="rfp-upload-divider" />

        <div className="rfp-upload-subsection section-spacer">
          <div className="toolbar">
            <div>
              <p className="eyebrow">Uploaded Files</p>
              <h3 className="card-title">업로드 완료 파일</h3>
              <p className="page-copy">
                체크한 파일만 추출에 사용됩니다. 긴 문서일수록 선택 범위를 줄이는 편이 더 안정적입니다.
              </p>
            </div>
            <div className="action-row">
              <button
                className="secondary-button"
                disabled={extraction.files.length === 0}
                onClick={() => setSelectedFileIds(extraction.files.map((uploadedFile) => uploadedFile.id))}
                type="button"
              >
                전체 선택
              </button>
              <button
                className="secondary-button"
                disabled={selectedFileIds.length === 0}
                onClick={() => setSelectedFileIds([])}
                type="button"
              >
                선택 해제
              </button>
              <button
                className="button"
                disabled={
                  isReextracting ||
                  isUploading ||
                  extraction.files.length === 0 ||
                  selectedFileIds.length === 0
                }
                onClick={() => void handleReextract()}
                type="button"
              >
                {isReextracting ? "추출 중..." : "선택 파일로 추출"}
              </button>
            </div>
          </div>

          {isReextracting ? (
            <div className="progress-shell">
              <div className="progress-meta">
                <strong>추출 진행 중</strong>
                <span>{extractProgress}%</span>
              </div>
              <div className="progress-bar" aria-hidden="true">
                <div className="progress-fill" style={{ width: `${extractProgress}%` }} />
              </div>
              <p className="page-copy">{EXTRACTION_PROGRESS_STEPS[extractStepIndex]}</p>
              <p className="subtle-copy">문서 길이에 따라 보통 20초에서 2분 정도 걸릴 수 있습니다.</p>
            </div>
          ) : null}

          <div className="status-row">
            <span className={`status-pill ${extraction.status === "confirmed" ? "ok" : "warn"}`}>
              {extraction.status}
            </span>
            <span className={`status-pill ${extraction.ocr_required ? "warn" : "ok"}`}>
              {extraction.ocr_required ? "OCR optional" : "Text extraction ok"}
            </span>
            <span className="status-pill">
              추출 선택 {selectedFileIds.length}/{extraction.files.length}
            </span>
          </div>

          <div className="stack-list section-spacer">
            {extraction.files.length === 0 ? (
              <p className="page-copy">아직 업로드된 공고 파일이 없습니다.</p>
            ) : (
              extraction.files.map((uploadedFile) => {
                const checked = selectedFileIds.includes(uploadedFile.id);
                return (
                  <article
                    key={uploadedFile.id}
                    className={`mini-card rfp-file-card ${checked ? "rfp-file-card-selected" : ""}`}
                  >
                    <div className="rfp-file-main">
                      <input
                        checked={checked}
                        className="checkbox-input"
                        onChange={() => toggleUploadedFile(uploadedFile.id)}
                        type="checkbox"
                      />
                      <div className="rfp-file-meta">
                        <h3>{uploadedFile.filename}</h3>
                        <p className="card-copy">
                          {formatFileRole(uploadedFile.role)} · {formatBytes(uploadedFile.size)}
                        </p>
                      </div>
                    </div>
                    <button
                      className="secondary-button"
                      disabled={deletingFileId === uploadedFile.id}
                      onClick={() => void handleDeleteFile(uploadedFile.id)}
                      type="button"
                    >
                      {deletingFileId === uploadedFile.id ? "삭제 중..." : "삭제"}
                    </button>
                  </article>
                );
              })
            )}
          </div>
        </div>
      </section>

      <section className="content-panel">
        <p className="eyebrow">Project Summary</p>
        <h2 className="card-title">사업 개요</h2>
        <textarea
          className="input-textarea input-textarea-lg rfp-summary-textarea"
          value={extraction.project_summary_text}
          onChange={(event) =>
            setExtraction((current) => ({
              ...current,
              project_summary_text: event.target.value
            }))
          }
        />
      </section>

      <section className="content-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">Requirements</p>
            <h2 className="card-title">요구사항</h2>
            <p className="page-copy">
              요구사항 번호가 없는 문서도 있으므로 빈 칸을 허용합니다. 추출 품질이 낮으면 직접
              행을 추가하거나 수정하세요. `세부 내용`은 여러 항목이 있으면 마크다운 bullet 형태로
              정리됩니다.
            </p>
          </div>
          <button className="secondary-button" onClick={addRequirementRow} type="button">
            요구사항 행 추가
          </button>
        </div>

        <div className="rfp-table-shell">
          <table className="mapping-table rfp-table">
            <thead>
              <tr>
                <th>요구사항 번호</th>
                <th>요구사항 명칭</th>
                <th>요구사항 정의</th>
                <th>세부 내용</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {extraction.requirements.length === 0 ? (
                <tr>
                  <td colSpan={5}>아직 추출된 요구사항이 없습니다.</td>
                </tr>
              ) : (
                extraction.requirements.map((item, index) => (
                  <tr key={`${item.id}-${index}`}>
                    <td>
                      <input
                        value={item.requirement_no}
                        onChange={(event) =>
                          updateRequirement(index, "requirement_no", event.target.value)
                        }
                      />
                    </td>
                    <td>
                      <input
                        value={item.name}
                        onChange={(event) => updateRequirement(index, "name", event.target.value)}
                      />
                    </td>
                    <td>
                      <textarea
                        className="input-textarea"
                        value={item.definition}
                        onChange={(event) =>
                          updateRequirement(index, "definition", event.target.value)
                        }
                      />
                    </td>
                    <td>
                      <textarea
                        className="input-textarea rfp-details-textarea"
                        value={item.details}
                        onChange={(event) => updateRequirement(index, "details", event.target.value)}
                      />
                    </td>
                    <td>
                      <button
                        className="secondary-button"
                        onClick={() => removeRequirementRow(index)}
                        type="button"
                      >
                        삭제
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="content-panel">
        <p className="eyebrow">Review Actions</p>
        <h2 className="card-title">페이지 전체 저장 및 확정</h2>
        <p className="page-copy">
          아래 버튼은 사업 개요와 요구사항 전체 수정 결과에 적용됩니다.
        </p>
        <div className="action-row">
          <button
            className="secondary-button"
            disabled={isSaving || isUploading || isReextracting}
            onClick={() => void handleSave("draft")}
            type="button"
          >
            {isSaving ? "저장 중..." : "임시 저장"}
          </button>
          <button
            className="button"
            disabled={isSaving || isUploading || isReextracting}
            onClick={() => void handleSave("confirmed")}
            type="button"
          >
            {isSaving ? "확정 중..." : "추출 결과 확정"}
          </button>
        </div>
      </section>
    </section>
  );
}
