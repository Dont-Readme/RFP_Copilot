import Link from "next/link";
import { notFound } from "next/navigation";

import { getProject, listLibraryAssets, listProjectAssets } from "@/lib/api";
import { ProjectAssetManager } from "@/components/ProjectAssetManager";
import type { LibraryAsset, Project } from "@/lib/types";

type ProjectHomePageProps = {
  params: Promise<{ id: string }>;
};

const sections = [
  { href: "rfp", title: "RFP 추출", description: "공고 업로드와 요구사항 확정 흐름" },
  { href: "outline", title: "목차 작성", description: "목차 구조와 계층 정의" },
  { href: "draft", title: "초안 작성", description: "생성 준비 확인, 초안 생성, AI 편집, 다운로드" },
  { href: "debug", title: "디버그 인스펙터", description: "실제 프롬프트 입력값, 청크, planner 값을 확인" }
];

async function loadProjectWorkspace(projectId: number): Promise<{
  project: Project;
  allAssets: LibraryAsset[];
  linkedAssets: LibraryAsset[];
}> {
  const [project, allAssets, linkedAssets] = await Promise.all([
    getProject(projectId),
    listLibraryAssets(),
    listProjectAssets(projectId)
  ]);

  return { project, allAssets, linkedAssets };
}

export default async function ProjectHomePage({ params }: ProjectHomePageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { project, allAssets, linkedAssets } = await loadProjectWorkspace(projectId);
  const linkedAssetIds = linkedAssets.map((asset) => asset.id);

  return (
    <main className="page-shell">
      <div className="project-home-nav">
        <Link className="button" href="/projects">
          프로젝트 목록
        </Link>
      </div>

      <section className="detail-panel">
        <p className="eyebrow">프로젝트 워크스페이스</p>
        <h1 className="page-title">{project.name}</h1>
        <p className="page-copy">
          프로젝트별 상세 작업 공간입니다. 여기서 자료 연결 상태를 저장하고, 아래 하위 라우트로
          들어가 세부 기능을 편집합니다.
        </p>
      </section>

      <section className="section-spacer card-grid">
        {sections.map((section) => (
          <Link key={section.href} className="mini-card" href={`/projects/${projectId}/${section.href}`}>
            <h2>{section.title}</h2>
            <p>{section.description}</p>
          </Link>
        ))}
      </section>

      <div className="section-spacer">
        <ProjectAssetManager
          allAssets={allAssets}
          initialLinkedAssetIds={linkedAssetIds}
          projectId={projectId}
        />
      </div>
    </main>
  );
}
