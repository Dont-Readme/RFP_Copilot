export type ApiHealth = {
  ok: boolean;
};

export type Project = {
  id: number;
  name: string;
  owner_user_id: string;
  created_at: string;
  updated_at: string;
};

export type ProjectFile = {
  id: number;
  project_id: number;
  kind: string;
  role: "notice" | "sow" | "rfp" | "requirements" | "other";
  filename: string;
  mime: string;
  path: string;
  size: number;
  created_at: string;
};

export type EvaluationItem = {
  id: number;
  project_id: number;
  item: string;
  score: string;
  notes: string;
  created_at: string;
};

export type RfpRequirementItem = {
  id: number;
  project_id: number;
  sort_order: number;
  requirement_no: string;
  name: string;
  definition: string;
  details: string;
  created_at: string;
};

export type RequirementSourceSelection = {
  file_id: number;
  page_from: number | null;
  page_to: number | null;
};

export type OpenQuestion = {
  id: string;
  project_id: number;
  draft_section_id: number | null;
  outline_section_id: number | null;
  section_heading_text: string;
  question_text: string;
  category: string;
  severity: string;
  source_agent: string;
  status: "open" | "resolved";
  created_at: string;
};

export type LibraryAsset = {
  id: number;
  owner_user_id: string;
  category: string;
  title: string;
  filename: string;
  mime: string;
  path: string;
  created_at: string;
};

export type ProjectAssetLinkResult = {
  project_id: number;
  asset_ids: number[];
};

export type DraftSection = {
  id: number;
  project_id: number;
  title: string;
  content_md: string;
  status: string;
  updated_at: string;
};

export type OutlineSection = {
  id: number;
  project_id: number;
  sort_order: number;
  depth: number;
  display_label: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Citation = {
  id: number;
  project_id: number;
  outline_section_id: number;
  source_title: string;
  source_url: string;
  snippet: string;
  accessed_at: string;
};

export type RewriteResponse = {
  replacement_text: string;
  diff_hint: string | null;
};

export type DraftChatMessage = {
  id: number;
  project_id: number;
  draft_section_id: number;
  role: "user" | "assistant";
  message_text: string;
  suggestion_text: string | null;
  apply_mode: "replace_selection" | "advice_only";
  selection_start: number | null;
  selection_end: number | null;
  selection_text: string | null;
  applied_at: string | null;
  created_at: string;
};

export type DraftSectionPlan = {
  section_id: number;
  heading_text: string;
  depth: number;
  heading_path: string[];
  section_goal: string;
  assigned_requirement_titles: string[];
  assigned_evaluation_titles: string[];
  assigned_company_facts: string[];
  search_topics: string[];
  status: string;
};

export type DraftPlanningConfig = {
  project_id: number;
  author_intent: string;
};

export type DraftGenerationUnit = {
  unit_key: string;
  outline_section_id: number;
  section_heading_text: string;
  unit_title: string;
  unit_goal: string;
  writing_instruction: string;
  writing_mode: string;
  unit_pattern: string;
  required_aspects: string[];
  primary_requirement_titles: string[];
  secondary_requirement_titles: string[];
  asset_titles: string[];
  search_topics: string[];
  outline_fit_warning: string;
};

export type DraftRequirementCoverage = {
  requirement_id: number;
  requirement_label: string;
  primary_unit_key: string;
  primary_outline_section_id: number;
  secondary_unit_keys: string[];
  rationale: string;
};

export type DraftPlanResult = {
  project_id: number;
  ready: boolean;
  warnings: string[];
  sections: DraftSectionPlan[];
  author_intent: string;
  planner_summary: string;
  planner_mode: string;
  generation_units: DraftGenerationUnit[];
  requirement_coverage: DraftRequirementCoverage[];
  coverage_warnings: string[];
  generation_requires_confirmation: boolean;
};

export type DraftSearchCitation = {
  title: string;
  url: string;
  snippet: string;
};

export type DraftSearchSource = {
  title: string;
  url: string;
};

export type DraftSearchTask = {
  id: number;
  project_id: number;
  outline_section_id: number;
  topic: string;
  unit_key: string;
  purpose: string;
  reason: string;
  source_stage: string;
  expected_output: string;
  allowed_domains: string[];
  max_results: number;
  query_text: string;
  result_summary: string;
  citations: DraftSearchCitation[];
  sources: DraftSearchSource[];
  status: string;
  searched_on: string;
  created_at: string;
  updated_at: string;
};

export type DebugPlannerRequirementCandidate = {
  requirement_id: number;
  requirement_no: string;
  name: string;
  definition: string;
  details: string;
  score: number;
  matched_tokens: string[];
  selected: boolean;
};

export type DebugPlannerEvaluationCandidate = {
  evaluation_item_id: number;
  item: string;
  score_text: string;
  notes: string;
  score: number;
  matched_tokens: string[];
  selected: boolean;
};

export type DebugPlannerAssetCandidate = {
  asset_id: number;
  category: string;
  title: string;
  score: number;
  matched_tokens: string[];
  compact_heading_match: boolean;
  selected: boolean;
  snippet_previews: string[];
};

export type DebugPlannerSearchTask = {
  topic: string;
  reason: string;
  freshness_required: boolean;
  expected_output: string;
};

export type DebugPlannerSection = {
  section_id: number;
  heading_text: string;
  heading_path: string[];
  section_tokens: string[];
  section_goal: string;
  draft_guidance: string;
  assigned_company_facts: string[];
  search_tasks: DebugPlannerSearchTask[];
  requirement_candidates: DebugPlannerRequirementCandidate[];
  evaluation_candidates: DebugPlannerEvaluationCandidate[];
  asset_candidates: DebugPlannerAssetCandidate[];
};

export type DebugPlannerResult = {
  project_id: number;
  ready: boolean;
  warnings: string[];
  sections: DebugPlannerSection[];
};

export type DebugDocumentChunk = {
  id: number;
  chunk_index: number;
  page_start: number | null;
  page_end: number | null;
  route_label: string | null;
  token_estimate: number;
  text_content: string;
  created_at: string;
};

export type DebugRfpFileChunks = {
  file_id: number;
  filename: string;
  role: string;
  mime: string;
  size: number;
  raw_text: string;
  chunk_count: number;
  chunks: DebugDocumentChunk[];
};

export type DebugRfpChunksResult = {
  project_id: number;
  files: DebugRfpFileChunks[];
};

export type PromptTrace = {
  id: string;
  project_id: number;
  trace_kind: string;
  model: string;
  system_prompt: string | null;
  user_prompt: string | null;
  input_text: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type PromptTraceListResult = {
  project_id: number;
  traces: PromptTrace[];
};

export type RfpExtraction = {
  project_id: number;
  status: "draft" | "confirmed";
  raw_text: string;
  project_summary_text: string;
  ocr_required: boolean;
  updated_at: string;
  requirement_sources: RequirementSourceSelection[];
  files: ProjectFile[];
  requirements: RfpRequirementItem[];
  evaluation_items: EvaluationItem[];
};

export type RfpUploadResponse = {
  extraction: RfpExtraction;
  file: ProjectFile;
};

export type ExportSession = {
  id: string;
  project_id: number;
  preview_md_path: string;
  files_json: string;
  status: string;
  created_at: string;
};

export type SearchRunResult = {
  project_id: number;
  section_ids: number[];
  citations: Citation[];
};

export type DraftGenerateResult = {
  section: DraftSection;
  questions: OpenQuestion[];
};

export type DraftGeneratePayload = {
  mode: string;
  confirm_warnings?: boolean;
};

export type DraftChatTurn = {
  user_message: DraftChatMessage;
  assistant_message: DraftChatMessage;
  review_items: OpenQuestion[];
};

export const ASSET_CATEGORIES = [
  "회사소개",
  "제품",
  "실적",
  "인력",
  "특허",
  "재무",
  "레퍼런스",
  "기타"
] as const;

export type AssetCategory = (typeof ASSET_CATEGORIES)[number];
