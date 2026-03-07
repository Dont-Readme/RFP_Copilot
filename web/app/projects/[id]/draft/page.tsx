import { notFound } from "next/navigation";

import {
  getOutline,
  getRfpExtraction,
  listDraftChatMessages,
  listDraftSections,
  listProjectAssets,
  listQuestions
} from "@/lib/api";
import type { DraftChatMessage, DraftSection, OpenQuestion, OutlineSection } from "@/lib/types";
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
  reviewItems: OpenQuestion[];
  section: DraftSection;
}> {
  const [sections, reviewItems, outlineSections, extraction, linkedAssets] = await Promise.all([
    listDraftSections(projectId),
    listQuestions(projectId),
    getOutline(projectId),
    getRfpExtraction(projectId),
    listProjectAssets(projectId)
  ]);
  const [section] = sections;

  if (!section) {
    throw new Error("No draft section available");
  }

  const chatMessages = await listDraftChatMessages(projectId, section.id);
  return {
    chatMessages,
    linkedAssetCount: linkedAssets.length,
    outlineSections,
    rfpFileCount: extraction.files.length,
    rfpReady: Boolean(extraction.raw_text.trim()),
    reviewItems,
    section,
  };
}

export default async function ProjectDraftPage({ params }: ProjectDraftPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { chatMessages, linkedAssetCount, outlineSections, rfpFileCount, rfpReady, reviewItems, section } =
    await loadDraftWorkspace(projectId);

  return (
    <main className="page-shell draft-page-shell">
      <section className="detail-panel">
        <p className="eyebrow">Draft Editor</p>
        <h1 className="card-title">Project #{projectId} Draft Workspace</h1>
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
        initialReviewItems={reviewItems}
        initialSection={section}
        projectId={projectId}
      />
    </main>
  );
}
