import { notFound } from "next/navigation";

import { DebugChunkRefreshButton } from "@/components/DebugChunkRefreshButton";
import {
  getDebugDraftPlan,
  getDebugRfpChunks,
  getProject,
  getPromptTraces,
} from "@/lib/api";
import type {
  DebugRfpChunksResult,
  DebugPlannerResult,
  Project,
  PromptTrace,
} from "@/lib/types";

type ProjectDebugPageProps = {
  params: Promise<{ id: string }>;
};

async function loadDebugWorkspace(projectId: number): Promise<{
  plannerDebug: DebugPlannerResult;
  project: Project;
  rfpChunks: DebugRfpChunksResult;
  traces: PromptTrace[];
}> {
  const [project, plannerDebug, rfpChunks, promptTraceResult] = await Promise.all([
    getProject(projectId),
    getDebugDraftPlan(projectId),
    getDebugRfpChunks(projectId),
    getPromptTraces(projectId, 100),
  ]);
  return {
    plannerDebug,
    project,
    rfpChunks,
    traces: promptTraceResult.traces,
  };
}

function formatTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("ko-KR");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function stringifyMetadata(metadata: Record<string, unknown>): string {
  return JSON.stringify(metadata, null, 2);
}

function formatReferencedPlaybooks(metadata: Record<string, unknown>): string | null {
  const value = metadata["referenced_playbook_keys"];
  if (!Array.isArray(value) || value.length === 0) {
    return null;
  }
  const items = value.filter((item): item is string => typeof item === "string" && item.length > 0);
  return items.length ? items.join("\n") : null;
}

function formatRequirementCandidates(section: DebugPlannerResult["sections"][number]): string {
  return (
    section.requirement_candidates
      .map((item) =>
        [
          `${item.selected ? "SELECTED" : "CANDIDATE"} | score=${item.score} | tokens=${item.matched_tokens.join(", ") || "-"}`,
          `${item.requirement_no || "(번호 없음)"} ${item.name || ""}`.trim(),
          `definition: ${item.definition || "(없음)"}`,
          `details: ${item.details || "(없음)"}`,
        ].join("\n"),
      )
      .join("\n\n") || "(없음)"
  );
}

function formatEvaluationCandidates(section: DebugPlannerResult["sections"][number]): string {
  return (
    section.evaluation_candidates
      .map((item) =>
        [
          `${item.selected ? "SELECTED" : "CANDIDATE"} | score=${item.score} | tokens=${item.matched_tokens.join(", ") || "-"}`,
          item.item || "(항목 없음)",
          `score_text: ${item.score_text || "(없음)"}`,
          `notes: ${item.notes || "(없음)"}`,
        ].join("\n"),
      )
      .join("\n\n") || "(없음)"
  );
}

function formatAssetCandidates(section: DebugPlannerResult["sections"][number]): string {
  return (
    section.asset_candidates
      .map((item) =>
        [
          `${item.selected ? "SELECTED" : "CANDIDATE"} | score=${item.score} | tokens=${item.matched_tokens.join(", ") || "-"} | compact_heading_match=${item.compact_heading_match ? "yes" : "no"}`,
          `[${item.category}] ${item.title}`,
          `snippets:\n${item.snippet_previews.join("\n") || "(없음)"}`,
        ].join("\n"),
      )
      .join("\n\n") || "(없음)"
  );
}

function formatSearchTasks(section: DebugPlannerResult["sections"][number]): string {
  return (
    section.search_tasks
      .map((task) =>
        [
          task.topic,
          `reason: ${task.reason || "(없음)"}`,
          `expected_output: ${task.expected_output || "(없음)"}`,
          `freshness_required: ${task.freshness_required ? "true" : "false"}`,
        ].join("\n"),
      )
      .join("\n\n") || "(없음)"
  );
}

export default async function ProjectDebugPage({ params }: ProjectDebugPageProps) {
  const { id } = await params;
  const projectId = Number(id);
  if (Number.isNaN(projectId)) {
    notFound();
  }

  const { plannerDebug, project, rfpChunks, traces } = await loadDebugWorkspace(projectId);
  const totalChunks = rfpChunks.files.reduce((sum, file) => sum + file.chunk_count, 0);

  return (
    <main className="page-shell">
      <section className="detail-panel">
        <p className="eyebrow">Debug Inspector</p>
        <h1 className="page-title">{project.name}</h1>
        <p className="page-copy">
          이 화면은 실제 chunking 결과와 OpenAI 호출 직전에 저장한 prompt trace를 보여줍니다.
          값을 새로 보고 싶으면 RFP 추출, 초안 생성, AI 편집을 한 번 실행한 뒤 새로고침하면 됩니다.
        </p>
        <DebugChunkRefreshButton projectId={projectId} />
      </section>

      <section className="section-spacer card-grid">
        <article className="mini-card">
          <h2>Prompt Traces</h2>
          <p>{traces.length}건</p>
        </article>
        <article className="mini-card">
          <h2>RFP Files</h2>
          <p>{rfpChunks.files.length}개</p>
        </article>
        <article className="mini-card">
          <h2>Total Chunks</h2>
          <p>{totalChunks}개</p>
        </article>
        <article className="mini-card">
          <h2>Legacy Planner</h2>
          <p>{plannerDebug.sections.length}개</p>
        </article>
      </section>

      <section className="content-panel section-spacer">
        <p className="eyebrow">Planner Inputs</p>
        <h2 className="card-title">Legacy Rule-Based Planner Diagnostics</h2>
        <p className="page-copy">
          이 영역은 현재 초안 생성에 쓰이는 AI planner가 아니라, 이전 규칙 기반 planner가 후보를 어떻게
          점수화했는지 보여주는 레거시 진단 화면입니다.
        </p>
        {plannerDebug.warnings.length > 0 ? (
          <div className="draft-warning-list">
            {plannerDebug.warnings.map((warning, index) => (
              <p key={`${warning}-${index}`} className="draft-warning-item">
                {warning}
              </p>
            ))}
          </div>
        ) : null}
        <div className="panel-stack">
          {plannerDebug.sections.map((section) => (
            <details className="content-panel" key={section.section_id}>
              <summary className="debug-summary">
                <strong>{section.heading_text}</strong>
                <span>tokens={section.section_tokens.join(", ") || "-"}</span>
              </summary>
              <div className="draft-plan-block">
                <strong>heading_path</strong>
                <pre className="debug-pre">{section.heading_path.join(" > ") || "(없음)"}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>section_goal</strong>
                <pre className="debug-pre">{section.section_goal || "(없음)"}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>draft_guidance</strong>
                <pre className="debug-pre">{section.draft_guidance || "(없음)"}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>assigned_company_facts</strong>
                <pre className="debug-pre">{section.assigned_company_facts.join("\n") || "(없음)"}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>requirement_candidates</strong>
                <pre className="debug-pre">{formatRequirementCandidates(section)}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>evaluation_candidates</strong>
                <pre className="debug-pre">{formatEvaluationCandidates(section)}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>asset_candidates</strong>
                <pre className="debug-pre">{formatAssetCandidates(section)}</pre>
              </div>
              <div className="draft-plan-block">
                <strong>search_tasks</strong>
                <pre className="debug-pre">{formatSearchTasks(section)}</pre>
              </div>
            </details>
          ))}
        </div>
      </section>

      <section className="section-spacer panel-stack">
        <section className="content-panel">
          <p className="eyebrow">Prompt Traces</p>
          <h2 className="card-title">Actual Prompt Inputs</h2>
          <p className="page-copy">
            각 trace는 OpenAI 호출 직전에 저장한 실제 입력값입니다.
          </p>
        </section>
        {traces.length === 0 ? (
          <section className="content-panel system-notice">
            <p className="page-copy">
              아직 저장된 trace가 없습니다. RFP 추출, 초안 생성, AI 편집 중 하나를 실행한 뒤 다시 확인해
              주세요.
            </p>
          </section>
        ) : null}
        {traces.map((trace) => (
          <details className="content-panel" key={trace.id}>
            <summary className="debug-summary">
              <strong>{trace.trace_kind}</strong>
              <span>{formatTimestamp(trace.created_at)}</span>
            </summary>
            <p className="page-copy">model: {trace.model}</p>
            {formatReferencedPlaybooks(trace.metadata) ? (
              <div className="draft-plan-block">
                <strong>referenced_playbooks</strong>
                <pre className="debug-pre">{formatReferencedPlaybooks(trace.metadata)}</pre>
              </div>
            ) : null}
            <div className="draft-plan-block">
              <strong>metadata</strong>
              <pre className="debug-pre">{stringifyMetadata(trace.metadata)}</pre>
            </div>
            {trace.system_prompt ? (
              <div className="draft-plan-block">
                <strong>system_prompt</strong>
                <pre className="debug-pre">{trace.system_prompt}</pre>
              </div>
            ) : null}
            {trace.user_prompt ? (
              <div className="draft-plan-block">
                <strong>user_prompt</strong>
                <pre className="debug-pre">{trace.user_prompt}</pre>
              </div>
            ) : null}
            {trace.input_text ? (
              <div className="draft-plan-block">
                <strong>input_text</strong>
                <pre className="debug-pre">{trace.input_text}</pre>
              </div>
            ) : null}
          </details>
        ))}
      </section>

      <section className="section-spacer panel-stack">
        <section className="content-panel">
          <p className="eyebrow">RFP Chunks</p>
          <h2 className="card-title">Chunking Result Inspector</h2>
          <p className="page-copy">
            업로드된 RFP 파일별 raw text와 실제 chunk 목록입니다.
          </p>
        </section>
        {rfpChunks.files.map((file) => (
          <details className="content-panel" key={file.file_id}>
            <summary className="debug-summary">
              <strong>{file.filename}</strong>
              <span>
                {file.role} · {file.chunk_count} chunks · {formatBytes(file.size)}
              </span>
            </summary>
            <div className="draft-plan-block">
              <strong>raw_text</strong>
              <pre className="debug-pre">{file.raw_text || "(빈 텍스트)"}</pre>
            </div>
            <div className="debug-grid">
              {file.chunks.map((chunk) => (
                <article className="draft-plan-card" key={chunk.id}>
                  <p className="eyebrow">
                    chunk {chunk.chunk_index} · route={chunk.route_label ?? "general"}
                  </p>
                  <p className="page-copy">
                    page {chunk.page_start ?? "?"}
                    {chunk.page_end && chunk.page_end !== chunk.page_start ? `-${chunk.page_end}` : ""}
                    {" · "}
                    approx {chunk.token_estimate} tokens
                  </p>
                  <pre className="debug-pre">{chunk.text_content}</pre>
                </article>
              ))}
            </div>
          </details>
        ))}
      </section>
    </main>
  );
}
