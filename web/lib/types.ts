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
  question_text: string;
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
  parent_id: number | null;
  sort_order: number;
  title: string;
  needs_search: boolean;
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

export type EvalMapping = {
  id: number;
  project_id: number;
  evaluation_item_id: number;
  draft_section_id: number | null;
  section_title: string | null;
  strength_score: number;
  strength_label: "strong" | "weak" | "missing";
  rationale_text: string;
  created_at: string;
};

export type MappingWarning = {
  id: number;
  project_id: number;
  type: "missing" | "weak" | "overlap";
  evaluation_item_id: number | null;
  draft_section_id: number | null;
  message: string;
  created_at: string;
};

export type MappingResult = {
  strategy: string;
  evaluation_items: EvaluationItem[];
  mappings: EvalMapping[];
  warnings: MappingWarning[];
};

export type ExportSession = {
  id: string;
  project_id: number;
  preview_md_path: string;
  files_json: string;
  status: string;
  created_at: string;
};

export type ExportPreview = {
  export_session_id: string;
  preview_md: string;
  formats: string[];
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

export type DraftChatTurn = {
  user_message: DraftChatMessage;
  assistant_message: DraftChatMessage;
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
