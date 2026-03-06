"use client";

import { useState } from "react";

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

const FILE_ROLE_OPTIONS: Array<{ value: ProjectFile["role"]; label: string }> = [
  { value: "notice", label: "공고문" },
  { value: "sow", label: "과업지시서" },
  { value: "rfp", label: "제안요청서" },
  { value: "requirements", label: "요구사항정의서" },
  { value: "other", label: "기타" }
];

function formatFileRole(role: ProjectFile["role"]): string {
  return FILE_ROLE_OPTIONS.find((option) => option.value === role)?.label ?? role;
}

export function RfpWorkspace({ projectId, initialExtraction }: RfpWorkspaceProps) {
  const [extraction, setExtraction] = useState(initialExtraction);
  const [file, setFile] = useState<File | null>(null);
  const [role, setRole] = useState<ProjectFile["role"]>("notice");
  const [isUploading, setIsUploading] = useState(false);
  const [isReextracting, setIsReextracting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [deletingFileId, setDeletingFileId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    if (!file) {
      setError("업로드할 파일을 선택해 주세요.");
      return;
    }

    try {
      setIsUploading(true);
      setError(null);
      const response = await uploadRfpFile(projectId, { file, role });
      setExtraction(response.extraction);
      setFile(null);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "RFP 업로드에 실패했습니다.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleDeleteFile(fileId: number) {
    try {
      setDeletingFileId(fileId);
      setError(null);
      await deleteRfpFile(projectId, fileId);
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
    try {
      setIsReextracting(true);
      setError(null);
      const updated = await rerunRfpExtraction(projectId);
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

  function updateEvaluation(index: number, field: "item" | "score" | "notes", value: string) {
    setExtraction((current) => ({
      ...current,
      evaluation_items: current.evaluation_items.map((item, itemIndex) =>
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

  function addEvaluationRow() {
    setExtraction((current) => ({
      ...current,
      evaluation_items: [
        ...current.evaluation_items,
        {
          id: Date.now(),
          project_id: current.project_id,
          item: "",
          score: "",
          notes: "",
          created_at: new Date().toISOString()
        }
      ]
    }));
  }

  function removeEvaluationRow(index: number) {
    setExtraction((current) => ({
      ...current,
      evaluation_items: current.evaluation_items.filter((_, itemIndex) => itemIndex !== index)
    }));
  }

  return (
    <section className="panel-stack section-spacer">
      <section className="content-panel">
        <p className="eyebrow">Upload</p>
        <h2 className="card-title">공고 파일 업로드</h2>
        <p className="page-copy">
          공고문, 과업지시서, 요구사항정의서 등 여러 파일을 올린 뒤 전체 파일 기준으로 추출을
          실행합니다. 추출 프롬프트는 `api/app/services/rfp_prompts.py`에서 섹션별로 수정할 수
          있습니다.
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
            hidden
            id="rfp-file-upload"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            type="file"
          />
          <button className="button" disabled={isUploading} onClick={() => void handleUpload()} type="button">
            {isUploading ? "업로드 중..." : "파일 업로드"}
          </button>
          <button
            className="secondary-button"
            disabled={isReextracting || extraction.files.length === 0}
            onClick={() => void handleReextract()}
            type="button"
          >
            {isReextracting ? "추출 중..." : "전체 파일로 추출"}
          </button>
        </div>

        <div className="status-row">
          <span className={`status-pill ${extraction.status === "confirmed" ? "ok" : "warn"}`}>
            {extraction.status}
          </span>
          <span className={`status-pill ${extraction.ocr_required ? "warn" : "ok"}`}>
            {extraction.ocr_required ? "OCR optional" : "Text extraction ok"}
          </span>
          <span className="status-pill">{extraction.files.length} files</span>
        </div>
        {file ? <p className="page-copy">선택 파일: {file.name}</p> : null}

        <div className="stack-list section-spacer">
          {extraction.files.length === 0 ? (
            <p className="page-copy">아직 업로드된 공고 파일이 없습니다.</p>
          ) : (
            extraction.files.map((uploadedFile) => (
              <article key={uploadedFile.id} className="mini-card rfp-file-card">
                <div>
                  <h3>{uploadedFile.filename}</h3>
                  <p className="card-copy">
                    {formatFileRole(uploadedFile.role)} · {(uploadedFile.size / 1024).toFixed(1)} KB
                  </p>
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
            ))
          )}
        </div>
      </section>

      <section className="content-panel">
        <p className="eyebrow">Project Summary</p>
        <h2 className="card-title">사업 개요</h2>
        <textarea
          className="input-textarea input-textarea-lg"
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
              행을 추가하거나 수정하세요.
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
                        className="input-textarea"
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
        <div className="toolbar">
          <div>
            <p className="eyebrow">Evaluation</p>
            <h2 className="card-title">평가항목</h2>
            <p className="page-copy">
              배점은 원문 표기를 유지하는 편이 좋습니다. 예: `20점`, `30%`, `정량 20 / 정성 10`.
            </p>
          </div>
          <button className="secondary-button" onClick={addEvaluationRow} type="button">
            평가항목 행 추가
          </button>
        </div>

        <div className="rfp-table-shell">
          <table className="mapping-table rfp-table">
            <thead>
              <tr>
                <th>평가항목</th>
                <th>배점</th>
                <th>비고</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              {extraction.evaluation_items.length === 0 ? (
                <tr>
                  <td colSpan={4}>아직 추출된 평가항목이 없습니다.</td>
                </tr>
              ) : (
                extraction.evaluation_items.map((item, index) => (
                  <tr key={`${item.id}-${index}`}>
                    <td>
                      <input
                        value={item.item}
                        onChange={(event) => updateEvaluation(index, "item", event.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        value={item.score}
                        onChange={(event) => updateEvaluation(index, "score", event.target.value)}
                      />
                    </td>
                    <td>
                      <textarea
                        className="input-textarea"
                        value={item.notes}
                        onChange={(event) => updateEvaluation(index, "notes", event.target.value)}
                      />
                    </td>
                    <td>
                      <button
                        className="secondary-button"
                        onClick={() => removeEvaluationRow(index)}
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

        <div className="action-row">
          <button className="secondary-button" disabled={isSaving} onClick={() => void handleSave("draft")} type="button">
            {isSaving ? "저장 중..." : "임시 저장"}
          </button>
          <button className="button" disabled={isSaving} onClick={() => void handleSave("confirmed")} type="button">
            {isSaving ? "확정 중..." : "추출 결과 확정"}
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </section>
  );
}
