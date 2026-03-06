import Link from "next/link";

import { getHealth, listProjects } from "@/lib/api";
import type { ApiHealth, Project } from "@/lib/types";
import { ProjectsManager } from "@/components/ProjectsManager";

export const dynamic = "force-dynamic";

const fallbackProjects: Project[] = [
  {
    id: 101,
    name: "2026 스마트시티 제안 대응",
    owner_user_id: "local",
    created_at: "2026-03-06T00:00:00",
    updated_at: "2026-03-06T00:00:00"
  },
  {
    id: 102,
    name: "AI 민원 분석 플랫폼 제안서",
    owner_user_id: "local",
    created_at: "2026-03-06T00:00:00",
    updated_at: "2026-03-06T00:00:00"
  }
];

async function loadDashboardData(): Promise<{
  health: ApiHealth | null;
  projects: Project[];
  sourceLabel: string;
  error: string | null;
}> {
  try {
    const [health, projects] = await Promise.all([getHealth(), listProjects()]);
    return { health, projects, sourceLabel: "api", error: null };
  } catch (error) {
    return {
      health: null,
      projects: fallbackProjects,
      sourceLabel: "local fallback",
      error: error instanceof Error ? error.message : "Unknown API error"
    };
  }
}

export default async function ProjectsPage() {
  const { health, projects, sourceLabel, error } = await loadDashboardData();

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <p className="eyebrow">Bootstrap Dashboard</p>
        <h1 className="page-title">RFP Copilot</h1>
        <p className="page-copy">
          FastAPI와 Next.js를 연결한 초기 스캐폴딩입니다. 현재 프로젝트 목록은
          <span className="inline-pill" style={{ marginLeft: 8 }}>{sourceLabel}</span>
          에서 불러옵니다.
        </p>
        <div className="status-row">
          <span className={`status-pill ${health?.ok ? "ok" : "warn"}`}>
            API {health?.ok ? "connected" : "fallback"}
          </span>
          <span className="status-pill">{projects.length} projects</span>
        </div>
        {error ? (
          <p className="page-copy">API 연결 실패: {error}</p>
        ) : (
          <p className="page-copy">`lib/api.ts` 경유로 `/api/health`와 `/api/projects`를 호출했습니다.</p>
        )}
      </section>

      <div className="link-row">
        <Link className="secondary-button" href="/library">
          자료 라이브러리
        </Link>
      </div>

      <ProjectsManager initialProjects={projects} />
    </main>
  );
}
