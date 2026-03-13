"use client";

import { useState } from "react";

import type { AssetCategory, LibraryAsset } from "@/lib/types";
import { ASSET_CATEGORIES } from "@/lib/types";

type FileUploaderProps = {
  onUploaded: (asset: LibraryAsset) => void;
  onUpload: (formData: FormData) => Promise<LibraryAsset>;
};

export function FileUploader({ onUploaded, onUpload }: FileUploaderProps) {
  const [filename, setFilename] = useState("선택된 파일 없음");
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<AssetCategory>("회사소개");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("업로드할 파일을 먼저 선택해 주세요.");
      return;
    }

    const formData = new FormData();
    formData.append("category", category);
    formData.append("title", title);
    formData.append("file", file);

    try {
      setIsSubmitting(true);
      setError(null);
      const asset = await onUpload(formData);
      onUploaded(asset);
      setFile(null);
      setTitle("");
      setFilename("선택된 파일 없음");
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "업로드 중 오류가 발생했습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="upload-shell" onSubmit={handleSubmit}>
      <p className="eyebrow">자료 업로드</p>
      <h2 className="card-title">라이브러리 업로드</h2>
      <p className="card-copy">
        카테고리와 제목을 지정한 뒤 파일을 업로드합니다. 업로드된 항목은 프로젝트 화면에서
        연결할 수 있습니다.
      </p>
      <div className="form-grid">
        <label className="field">
          <span>자료 유형</span>
          <select value={category} onChange={(event) => setCategory(event.target.value as AssetCategory)}>
            {ASSET_CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>제목</span>
          <input
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="예: 2025 공공 레퍼런스 모음"
          />
        </label>
      </div>
      <div className="action-row">
        <label className="secondary-button" htmlFor="asset-upload-file">
          파일 선택
        </label>
        <input
          id="asset-upload-file"
          hidden
          type="file"
          onChange={(event) => {
            const nextFile = event.target.files?.[0];
            setFile(nextFile ?? null);
            setFilename(nextFile?.name ?? "선택된 파일 없음");
          }}
        />
        <button className="button" disabled={isSubmitting} type="submit">
          {isSubmitting ? "업로드 중..." : "업로드"}
        </button>
      </div>
      <p className="page-copy">{filename}</p>
      {error ? <p className="error-text">{error}</p> : null}
    </form>
  );
}
