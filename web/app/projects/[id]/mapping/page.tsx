import { notFound } from "next/navigation";

import { getMapping } from "@/lib/api";
import { MappingManager } from "@/components/MappingManager";

type ProjectMappingPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectMappingPage({ params }: ProjectMappingPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }
  const initialResult = await getMapping(projectId);

  return (
    <main className="page-shell">
      <section className="content-panel">
        <p className="eyebrow">Mapping Validation</p>
        <h1 className="card-title">Project #{projectId} Evaluation Mapping</h1>
        <p className="page-copy">
          평가항목과 초안 간 대응 강도를 계산하고, 누락/약함 경고를 확인합니다.
        </p>
      </section>
      <MappingManager initialResult={initialResult} projectId={projectId} />
    </main>
  );
}
