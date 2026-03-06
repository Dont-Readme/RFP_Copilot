import { notFound } from "next/navigation";

import { ExportManager } from "@/components/ExportManager";

type ProjectExportPageProps = {
  params: Promise<{ id: string }>;
};

export default async function ProjectExportPage({ params }: ProjectExportPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  return (
    <main className="page-shell">
      <section className="content-panel">
        <p className="eyebrow">Export Preview</p>
        <h1 className="card-title">Project #{projectId} Export Preview</h1>
        <p className="page-copy">
          현재 프로젝트 상태를 바탕으로 preview와 다운로드 파일을 생성합니다.
        </p>
      </section>
      <ExportManager projectId={projectId} />
    </main>
  );
}
