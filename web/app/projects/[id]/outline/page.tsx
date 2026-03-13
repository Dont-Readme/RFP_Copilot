import { notFound } from "next/navigation";

import { ProjectStageNavigation } from "@/components/ProjectStageNavigation";
import { getOutline } from "@/lib/api";
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

  const outlineSections = await getOutline(projectId);

  return (
    <main className="page-shell project-step-shell">
      <ProjectStageNavigation currentStage="outline" projectId={projectId} />
      <section className="detail-panel">
        <p className="eyebrow">목차 작성</p>
        <h1 className="card-title">프로젝트 #{projectId} 목차 작업 공간</h1>
        <p className="page-copy">
          사용자가 제안서 목차 구조를 직접 정의하는 화면입니다. 상위/하위 관계와 depth를 정하면
          번호는 자동으로 계산되며, 초안 생성은 초안 작성 화면에서 진행합니다.
        </p>
      </section>
      <OutlineManager initialSections={outlineSections} projectId={projectId} />
    </main>
  );
}
