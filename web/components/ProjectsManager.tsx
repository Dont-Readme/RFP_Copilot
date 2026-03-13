"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { createProject, deleteProject, updateProject } from "@/lib/api";
import type { Project } from "@/lib/types";

type ProjectsManagerProps = {
  initialProjects: Project[];
};

export function ProjectsManager({ initialProjects }: ProjectsManagerProps) {
  const [projects, setProjects] = useState(initialProjects);
  const [draftName, setDraftName] = useState("");
  const [editingNames, setEditingNames] = useState<Record<number, string>>(
    Object.fromEntries(initialProjects.map((project) => [project.id, project.name]))
  );
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const emptyState = useMemo(() => projects.length === 0, [projects.length]);

  async function handleCreate(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!draftName.trim()) {
      setError("프로젝트 이름을 입력해 주세요.");
      return;
    }

    try {
      setBusyKey("create");
      setError(null);
      const created = await createProject({ name: draftName.trim() });
      setProjects((current) => [created, ...current]);
      setEditingNames((current) => ({ ...current, [created.id]: created.name }));
      setDraftName("");
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "프로젝트 생성에 실패했습니다.");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleRename(projectId: number) {
    const nextName = (editingNames[projectId] ?? "").trim();
    if (!nextName) {
      setError("프로젝트 이름은 비워둘 수 없습니다.");
      return;
    }

    try {
      setBusyKey(`rename-${projectId}`);
      setError(null);
      const updated = await updateProject(projectId, { name: nextName });
      setProjects((current) =>
        current.map((project) => (project.id === projectId ? updated : project))
      );
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "프로젝트 수정에 실패했습니다.");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDelete(projectId: number) {
    if (!window.confirm("이 프로젝트와 연결된 초안/질문/링크 데이터를 삭제합니다. 계속할까요?")) {
      return;
    }

    try {
      setBusyKey(`delete-${projectId}`);
      setError(null);
      await deleteProject(projectId);
      setProjects((current) => current.filter((project) => project.id !== projectId));
      setEditingNames((current) => {
        const next = { ...current };
        delete next[projectId];
        return next;
      });
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "프로젝트 삭제에 실패했습니다.");
    } finally {
      setBusyKey(null);
    }
  }

  return (
    <section className="section-spacer">
      <form className="content-panel" onSubmit={handleCreate}>
        <p className="eyebrow">프로젝트 관리</p>
        <h2 className="card-title">프로젝트 생성</h2>
        <div className="form-grid">
          <label className="field">
            <span>프로젝트 이름</span>
            <input
              placeholder="예: 2026 통합관제 제안 대응"
              value={draftName}
              onChange={(event) => setDraftName(event.target.value)}
            />
          </label>
        </div>
        <div className="action-row">
          <button className="button" disabled={busyKey === "create"} type="submit">
            {busyKey === "create" ? "생성 중..." : "프로젝트 만들기"}
          </button>
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </form>

      {emptyState ? (
        <section className="content-panel section-spacer">
          <p className="page-copy">생성된 프로젝트가 없습니다. 위 폼에서 첫 프로젝트를 만드세요.</p>
        </section>
      ) : (
        <section className="card-grid section-spacer">
          {projects.map((project) => (
            <article key={project.id} className="card">
              <p className="eyebrow">프로젝트 #{project.id}</p>
              <input
                className="inline-input"
                value={editingNames[project.id] ?? ""}
                onChange={(event) =>
                  setEditingNames((current) => ({
                    ...current,
                    [project.id]: event.target.value
                  }))
                }
              />
              <p className="card-copy">
                소유자: {project.owner_user_id} · 수정:{" "}
                {new Date(project.updated_at).toLocaleString("ko-KR")}
              </p>
              <div className="action-row">
                <Link className="secondary-button" href={`/projects/${project.id}`}>
                  작업 열기
                </Link>
                <button
                  className="button"
                  disabled={busyKey === `rename-${project.id}`}
                  onClick={() => void handleRename(project.id)}
                  type="button"
                >
                  {busyKey === `rename-${project.id}` ? "저장 중..." : "이름 저장"}
                </button>
                <button
                  className="button"
                  disabled={busyKey === `delete-${project.id}`}
                  onClick={() => void handleDelete(project.id)}
                  type="button"
                >
                  삭제
                </button>
              </div>
            </article>
          ))}
        </section>
      )}
    </section>
  );
}
