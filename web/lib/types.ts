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

export type DraftPlanResult = {
  project_id: number;
  ready: boolean;
  warnings: string[];
  sections: DraftSectionPlan[];
};

export type RfpExtraction = {
  project_id: number;
  status: "draft" | "confirmed";
  raw_text: string;
  project_summary_text: string;
  ocr_required: boolean;
  updated_at: string;
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
