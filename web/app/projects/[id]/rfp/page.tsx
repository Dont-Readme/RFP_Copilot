import { notFound } from "next/navigation";

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
    <main className="page-shell">
      <section className="content-panel">
        <p className="eyebrow">RFP Extraction</p>
        <h1 className="card-title">Project #{projectId} RFP Workspace</h1>
        <p className="page-copy">
          공고문, 과업지시서, 요구사항정의서 등 복수 파일을 올리고, 사업 개요/요구사항/평가항목을
          추출해 검토·수정·확정합니다.
        </p>
      </section>
      <RfpWorkspace initialExtraction={extraction} projectId={projectId} />
    </main>
  );
}
