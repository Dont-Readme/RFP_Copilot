import type {
  ApiHealth,
  Citation,
  DraftChatMessage,
  DraftChatTurn,
  DraftGenerateResult,
  DraftSection,
  ExportPreview,
  ExportSession,
  MappingResult,
  LibraryAsset,
  OpenQuestion,
  OutlineSection,
  Project,
  ProjectFile,
  ProjectAssetLinkResult,
  RfpExtraction,
  RfpUploadResponse,
  SearchRunResult,
  RewriteResponse
} from "@/lib/types";

export function getApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      ...(init?.headers ?? {})
    }
  });

  if (!response.ok) {
    let detail: string;
    try {
      detail = JSON.stringify(await response.json());
    } catch {
      detail = await response.text();
    }

    throw new Error(`API request failed for ${path}: ${response.status} ${detail}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function getHealth(): Promise<ApiHealth> {
  return request<ApiHealth>("/api/health");
}

export async function listProjects(): Promise<Project[]> {
  return request<Project[]>("/api/projects");
}

export async function getProject(projectId: number): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`);
}

export async function createProject(payload: { name: string }): Promise<Project> {
  return request<Project>("/api/projects", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function updateProject(projectId: number, payload: { name: string }): Promise<Project> {
  return request<Project>(`/api/projects/${projectId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function deleteProject(projectId: number): Promise<void> {
  return request<void>(`/api/projects/${projectId}`, {
    method: "DELETE"
  });
}

export async function listLibraryAssets(category?: string): Promise<LibraryAsset[]> {
  const search = category ? `?category=${encodeURIComponent(category)}` : "";
  return request<LibraryAsset[]>(`/api/library/assets${search}`);
}

export async function uploadLibraryAsset(formData: FormData): Promise<LibraryAsset> {
  return request<LibraryAsset>("/api/library/assets", {
    method: "POST",
    body: formData
  });
}

export async function listProjectAssets(projectId: number): Promise<LibraryAsset[]> {
  return request<LibraryAsset[]>(`/api/projects/${projectId}/assets`);
}

export async function syncProjectAssets(
  projectId: number,
  payload: { asset_ids: number[] }
): Promise<ProjectAssetLinkResult> {
  return request<ProjectAssetLinkResult>(`/api/projects/${projectId}/assets/link`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function getOutline(projectId: number): Promise<OutlineSection[]> {
  return request<OutlineSection[]>(`/api/projects/${projectId}/outline`);
}

export async function saveOutline(
  projectId: number,
  payload: {
    sections: Array<{
      id?: number | null;
      parent_id?: number | null;
      sort_order?: number | null;
      title: string;
      needs_search: boolean;
    }>;
  }
): Promise<OutlineSection[]> {
  return request<OutlineSection[]>(`/api/projects/${projectId}/outline`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function getCitations(projectId: number, sectionId?: number): Promise<Citation[]> {
  const search = sectionId ? `?section_id=${encodeURIComponent(String(sectionId))}` : "";
  return request<Citation[]>(`/api/projects/${projectId}/search/citations${search}`);
}

export async function runSearch(
  projectId: number,
  payload: { section_ids: number[] }
): Promise<SearchRunResult> {
  return request<SearchRunResult>(`/api/projects/${projectId}/search/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function listDraftSections(projectId: number): Promise<DraftSection[]> {
  return request<DraftSection[]>(`/api/projects/${projectId}/draft/sections`);
}

export async function generateDraft(
  projectId: number,
  payload?: { mode: string }
): Promise<DraftGenerateResult> {
  return request<DraftGenerateResult>(`/api/projects/${projectId}/draft/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload ?? { mode: "full" })
  });
}

export async function updateDraftSection(
  projectId: number,
  sectionId: number,
  payload: { content_md: string }
): Promise<DraftSection> {
  return request<DraftSection>(`/api/projects/${projectId}/draft/sections/${sectionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function listQuestions(projectId: number): Promise<OpenQuestion[]> {
  return request<OpenQuestion[]>(`/api/projects/${projectId}/questions`);
}

export async function updateQuestion(
  projectId: number,
  questionId: string,
  payload: { status: "open" | "resolved" }
): Promise<OpenQuestion> {
  return request<OpenQuestion>(`/api/projects/${projectId}/questions/${questionId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function listDraftChatMessages(
  projectId: number,
  sectionId: number
): Promise<DraftChatMessage[]> {
  return request<DraftChatMessage[]>(`/api/projects/${projectId}/draft/sections/${sectionId}/chat`);
}

export async function createDraftChatTurn(
  projectId: number,
  payload: {
    section_id: number;
    message: string;
    selection_start?: number | null;
    selection_end?: number | null;
    selection_text?: string | null;
  }
): Promise<DraftChatTurn> {
  return request<DraftChatTurn>(`/api/projects/${projectId}/draft/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function applyDraftChatMessage(
  projectId: number,
  messageId: number
): Promise<{ section: DraftSection; message: DraftChatMessage }> {
  return request<{ section: DraftSection; message: DraftChatMessage }>(
    `/api/projects/${projectId}/draft/chat/${messageId}/apply`,
    {
      method: "POST"
    }
  );
}

export async function rewriteSelection(
  projectId: number,
  payload: { section_id: number; selected_text: string; instruction: string }
): Promise<RewriteResponse> {
  return request<RewriteResponse>(`/api/projects/${projectId}/rewrite`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function getRfpExtraction(projectId: number): Promise<RfpExtraction> {
  return request<RfpExtraction>(`/api/projects/${projectId}/rfp/extraction`);
}

export async function rerunRfpExtraction(projectId: number): Promise<RfpExtraction> {
  return request<RfpExtraction>(`/api/projects/${projectId}/rfp/extract`, {
    method: "POST"
  });
}

export async function listRfpFiles(projectId: number): Promise<ProjectFile[]> {
  return request<ProjectFile[]>(`/api/projects/${projectId}/rfp/files`);
}

export async function uploadRfpFile(
  projectId: number,
  payload: {
    file: File;
    role: ProjectFile["role"];
  }
): Promise<RfpUploadResponse> {
  const formData = new FormData();
  formData.append("file", payload.file);
  formData.append("role", payload.role);
  return request<RfpUploadResponse>(`/api/projects/${projectId}/rfp/files`, {
    method: "POST",
    body: formData
  });
}

export async function deleteRfpFile(projectId: number, fileId: number): Promise<void> {
  return request<void>(`/api/projects/${projectId}/rfp/files/${fileId}`, {
    method: "DELETE"
  });
}

export async function updateRfpExtraction(
  projectId: number,
  payload: Omit<RfpExtraction, "project_id" | "updated_at">
): Promise<RfpExtraction> {
  return request<RfpExtraction>(`/api/projects/${projectId}/rfp/extraction`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function getMapping(projectId: number): Promise<MappingResult> {
  return request<MappingResult>(`/api/projects/${projectId}/mapping`);
}

export async function runMapping(projectId: number, payload?: { strategy: string }): Promise<MappingResult> {
  return request<MappingResult>(`/api/projects/${projectId}/mapping/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload ?? { strategy: "rules" })
  });
}

export async function createExportSession(
  projectId: number,
  payload: { formats: Array<"md" | "txt" | "docx" | "xlsx"> }
): Promise<ExportSession> {
  return request<ExportSession>(`/api/projects/${projectId}/export`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
}

export async function getExportPreview(
  projectId: number,
  exportSessionId: string
): Promise<ExportPreview> {
  return request<ExportPreview>(`/api/projects/${projectId}/export/${exportSessionId}/preview`);
}

export function buildExportDownloadUrl(
  projectId: number,
  exportSessionId: string,
  format: string
): string {
  return `${getApiBaseUrl()}/api/projects/${projectId}/export/${exportSessionId}/download?format=${encodeURIComponent(format)}`;
}
