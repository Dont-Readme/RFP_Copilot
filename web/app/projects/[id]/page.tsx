import Link from "next/link";
import { notFound } from "next/navigation";

import { getProject, listLibraryAssets, listProjectAssets } from "@/lib/api";
import { ProjectAssetManager } from "@/components/ProjectAssetManager";
import type { LibraryAsset, Project } from "@/lib/types";

type ProjectHomePageProps = {
  params: Promise<{ id: string }>;
};

const sections = [
  { href: "rfp", title: "RFP Extraction", description: "공고 업로드와 요구사항 확정 흐름" },
  { href: "outline", title: "Outline", description: "목차 구조와 계층 정의" },
  { href: "draft", title: "Draft Editor", description: "생성 준비 확인, 초안 생성, AI 편집" },
  { href: "mapping", title: "Mapping", description: "평가항목 매핑 검증 매트릭스" },
  { href: "export", title: "Export", description: "미리보기 후 수정/다운로드 분기" }
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
      <section className="detail-panel">
        <p className="eyebrow">Project Workspace</p>
        <h1 className="page-title">{project.name}</h1>
        <p className="page-copy">
          프로젝트별 상세 작업 공간입니다. 여기서 자료 연결 상태를 저장하고, 아래 하위 라우트로
          들어가 세부 기능을 편집합니다.
        </p>
        <div className="link-row">
          <Link className="secondary-button" href="/projects">
            프로젝트 목록
          </Link>
          <Link className="secondary-button" href="/library">
            자료 라이브러리
          </Link>
        </div>
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
