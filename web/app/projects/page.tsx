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
    return { health, projects, sourceLabel: "실시간 API", error: null };
  } catch (error) {
    return {
      health: null,
      projects: fallbackProjects,
      sourceLabel: "로컬 예비 데이터",
      error: error instanceof Error ? error.message : "알 수 없는 API 오류"
    };
  }
}

export default async function ProjectsPage() {
  const { health, projects, sourceLabel, error } = await loadDashboardData();

  return (
    <main className="page-shell">
      <section className="hero-panel">
        <div className="toolbar">
          <div>
            <p className="eyebrow">서비스 대시보드</p>
            <h1 className="page-title">RFP Copilot</h1>
            <p className="page-copy">
              프로젝트를 생성하고 RFP 추출, 목차 작성, 초안 편집 흐름으로 들어가는 메인 화면입니다.
              현재 프로젝트 목록은
              <span className="inline-pill" style={{ marginLeft: 8 }}>{sourceLabel}</span>
              에서 불러옵니다.
            </p>
          </div>
          <Link className="button" href="/library">
            자료 라이브러리
          </Link>
        </div>
        <div className="status-row">
          <span className={`status-pill ${health?.ok ? "ok" : "warn"}`}>
            {health?.ok ? "API 연결됨" : "예비 데이터 표시"}
          </span>
          <span className="status-pill">프로젝트 {projects.length}개</span>
        </div>
        {error ? (
          <p className="page-copy">API 연결 실패: {error}</p>
        ) : (
          <p className="page-copy">`lib/api.ts`를 통해 `/api/health`와 `/api/projects`를 호출했습니다.</p>
        )}
      </section>

      <ProjectsManager initialProjects={projects} />
    </main>
  );
}
