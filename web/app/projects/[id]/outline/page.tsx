import { notFound } from "next/navigation";

import { getCitations, getOutline } from "@/lib/api";
import { OutlineManager } from "@/components/OutlineManager";

type ProjectOutlinePageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectOutlinePage({ params }: ProjectOutlinePageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const [outlineSections, citations] = await Promise.all([
    getOutline(projectId),
    getCitations(projectId)
  ]);

  return (
    <main className="page-shell">
      <section className="content-panel">
        <p className="eyebrow">Outline</p>
        <h1 className="card-title">Project #{projectId} Outline Workspace</h1>
        <p className="page-copy">
          목차 CRUD, `needs_search` 플래그 저장, 인용 검색 실행, 목차 기반 초안 재생성을
          한 화면에서 처리합니다.
        </p>
      </section>
      <OutlineManager
        initialCitations={citations}
        initialSections={outlineSections}
        projectId={projectId}
      />
    </main>
  );
}
