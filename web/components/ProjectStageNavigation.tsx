import Link from "next/link";

type ProjectStage = "rfp" | "outline" | "draft";

type ProjectStageNavigationProps = {
  currentStage: ProjectStage;
  projectId: number;
};

const STAGES: Array<{ href: ProjectStage; label: string }> = [
  { href: "rfp", label: "RFP 추출" },
  { href: "outline", label: "목차 작성" },
  { href: "draft", label: "초안 작성" }
];

export function ProjectStageNavigation({
  currentStage,
  projectId
}: ProjectStageNavigationProps) {
  return (
    <div className="project-stage-nav">
      <Link className="button" href={`/projects/${projectId}`}>
        프로젝트 워크스페이스
      </Link>
      <div className="project-stage-links">
        {STAGES.map((stage) => (
          <Link
            key={stage.href}
            className={`project-stage-link${stage.href === currentStage ? " is-active" : ""}`}
            href={`/projects/${projectId}/${stage.href}`}
          >
            {stage.label}
          </Link>
        ))}
      </div>
    </div>
  );
}
