import { notFound } from "next/navigation";

import { ProjectStageNavigation } from "@/components/ProjectStageNavigation";
import { getRfpExtraction } from "@/lib/api";
import { RfpWorkspace } from "@/components/RfpWorkspace";

type ProjectRfpPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectRfpPage({ params }: ProjectRfpPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }
  const extraction = await getRfpExtraction(projectId);

  return (
    <main className="page-shell project-step-shell">
      <ProjectStageNavigation currentStage="rfp" projectId={projectId} />
      <section className="detail-panel">
        <p className="eyebrow">RFP 추출</p>
        <h1 className="card-title">프로젝트 #{projectId} RFP 작업 공간</h1>
        <p className="page-copy">
          공고문, 과업지시서, 제안요청서 등 복수 파일을 대기 목록에 담아 업로드하고, 선택한 파일만
          추출해 사업 개요와 요구사항을 검토·수정·확정합니다.
        </p>
      </section>
      <RfpWorkspace initialExtraction={extraction} projectId={projectId} />
    </main>
  );
}
