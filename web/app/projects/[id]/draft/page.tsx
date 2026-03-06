import { notFound } from "next/navigation";

import { listDraftChatMessages, listDraftSections, listQuestions } from "@/lib/api";
import type { DraftChatMessage, DraftSection, OpenQuestion } from "@/lib/types";
import { DraftWorkspace } from "@/components/DraftWorkspace";

type ProjectDraftPageProps = {
  params: Promise<{ id: string }>;
};

async function loadDraftWorkspace(projectId: number): Promise<{
  chatMessages: DraftChatMessage[];
  section: DraftSection;
  questions: OpenQuestion[];
}> {
  const [sections, questions] = await Promise.all([listDraftSections(projectId), listQuestions(projectId)]);
  const [section] = sections;

  if (!section) {
    throw new Error("No draft section available");
  }

  const chatMessages = await listDraftChatMessages(projectId, section.id);
  return { chatMessages, section, questions };
}

export default async function ProjectDraftPage({ params }: ProjectDraftPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { chatMessages, section, questions } = await loadDraftWorkspace(projectId);

  return (
    <main className="page-shell">
      <section className="detail-panel">
        <p className="eyebrow">Draft Editor</p>
        <h1 className="card-title">Project #{projectId} Draft Workspace</h1>
        <p className="page-copy">
          목차 기반으로 생성된 초안을 편집하고, 시스템 표기와 질문 패널, 부분 수정 요청을
          함께 다룹니다.
        </p>
      </section>

      <DraftWorkspace
        initialChatMessages={chatMessages}
        initialQuestions={questions}
        initialSection={section}
        projectId={projectId}
      />
    </main>
  );
}
