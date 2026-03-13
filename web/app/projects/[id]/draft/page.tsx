import { notFound } from "next/navigation";

import { ProjectStageNavigation } from "@/components/ProjectStageNavigation";
import {
  getOutline,
  getRfpExtraction,
  listDraftChatMessages,
  listDraftSections,
  listProjectAssets
} from "@/lib/api";
import type { DraftChatMessage, DraftSection, OutlineSection } from "@/lib/types";
import { DraftWorkspace } from "@/components/DraftWorkspace";

type ProjectDraftPageProps = {
  params: Promise<{ id: string }>;
};

async function loadDraftWorkspace(projectId: number): Promise<{
  chatMessages: DraftChatMessage[];
  linkedAssetCount: number;
  outlineSections: OutlineSection[];
  rfpFileCount: number;
  rfpReady: boolean;
  section: DraftSection;
}> {
  const [sections, outlineSections, extraction, linkedAssets] = await Promise.all([
    listDraftSections(projectId),
    getOutline(projectId),
    getRfpExtraction(projectId),
    listProjectAssets(projectId)
  ]);
  const [section] = sections;

  if (!section) {
    throw new Error("초안 섹션이 없습니다.");
  }

  const chatMessages = await listDraftChatMessages(projectId, section.id);
  return {
    chatMessages,
    linkedAssetCount: linkedAssets.length,
    outlineSections,
    rfpFileCount: extraction.files.length,
    rfpReady: Boolean(extraction.raw_text.trim()),
    section,
  };
}

export default async function ProjectDraftPage({ params }: ProjectDraftPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { chatMessages, linkedAssetCount, outlineSections, rfpFileCount, rfpReady, section } =
    await loadDraftWorkspace(projectId);

  return (
    <main className="page-shell draft-page-shell project-step-shell">
      <ProjectStageNavigation currentStage="draft" projectId={projectId} />
      <section className="detail-panel">
        <p className="eyebrow">초안 작성</p>
        <h1 className="card-title">프로젝트 #{projectId} 초안 작업 공간</h1>
        <p className="page-copy">
          RFP 추출 결과와 저장된 목차를 확인한 뒤 초안을 생성하고 같은 화면에서 편집합니다.
        </p>
      </section>

      <DraftWorkspace
        initialChatMessages={chatMessages}
        initialLinkedAssetCount={linkedAssetCount}
        initialOutlineSections={outlineSections}
        initialRfpFileCount={rfpFileCount}
        initialRfpReady={rfpReady}
        initialSection={section}
        projectId={projectId}
      />
    </main>
  );
}
