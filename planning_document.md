---
tags: 
related-concepts: []
date-created: 금요일, 3월 6일 2026, 9:54:58 오전
date-modified: 금요일, 3월 6일 2026, 9:59:02 오전
---
# Bootstrap Coding-Ready Development Plan — RFP Copilot

## 0) Purpose

Codex 첫 세션에서 **프로젝트 골격(프론트+백엔드), 초기 문서(README/ARCHITECTURE/PROJECT_CONTEXT), 폴더 구조, 설정(.env.example), 기본 API/페이지 스캐폴딩**을 한 번에 생성해 바로 개발을 시작할 수 있는 부트스트랩 계획이다.

---

## 1) Project Overview

- 프로젝트명(가칭): **RFP Copilot**
    
- 한 줄: **공고 PDF에서 요구사항/평가항목을 추출하고, 자료 라이브러리와 목차를 기반으로 제안서 초안을 생성하며, 평가항목-문단 매핑 누락을 자동 경고하고, 웹에서 편집 후 산출물(md/txt/docx/xlsx)을 내보내는 로컬 웹앱**
    
- 핵심 차별점(필수): **평가항목 매핑 체크(누락 경고 + 문단별 가점 요소 제안)**
    

---

## 2) Scope: MVP / In Scope / Out of Scope + Success Metrics

### MVP 목표

1. 공고 PDF 업로드 → 요구사항/평가항목 구조화 추출(사용자 검토/수정/확정)
    
2. “내 자료 관리(라이브러리)”에서 **자료 유형을 사용자가 지정**하여 업로드/관리, 프로젝트에 연결
    
3. 목차 입력(섹션별 검색 필요 체크) → 초안 생성(자료 자동 삽입 + “확인 필요(시스템)” 표기 + 질문 리스트)
    
4. 평가항목 ↔ 문단 매핑 자동 추천/검증(누락 경고/강화 제안)
    
5. 웹 편집(Markdown/Text) → Export **미리보기 화면**에서 수정/다운로드 선택
    
6. 선택 영역 “부분 수정 요청하기”(선택 기능이지만 MVP에 넣을 수 있는 구조 제공)
    

### In Scope (MVP)

- 로컬 단일 사용자(로그인 없음)
    
- 스캔 PDF 혼재: OCR은 **옵션/부분 지원**(기본은 텍스트 추출 우선)
    
- 산출물: `.md`, `.txt`, `.docx`, `.xlsx`(WBS/일정/예산 템플릿)
    

### Out of Scope (MVP)

- HWP 자동 편집/서식 완벽 대응(사람이 최종 마감)
    
- 협업(권한/코멘트/실시간 공동편집)
    
- OCR 고정밀 보장(일부 문서에 한해 옵션 제공)
    
- 자동 태깅/자동 분해 기반 소재관리(업로드 시 사용자가 유형 지정)
    

### Success Metrics

- 평가항목 매핑 검증에서 **누락 항목 0건**에 근접하도록 경고 커버리지 확보
    
- 공고 1건당 요구사항 정리 시간 **50% 이상 절감**(체감 기준)
    
- Export 미리보기→수정→다운로드 플로우가 “제출 초안 제작”에 충분히 실용적
    

---

## 3) User Flow

1. 프로젝트 생성
    
2. 공고 PDF 업로드
    
3. 요구사항/평가항목 추출 결과 화면에서 검토/수정/확정
    
4. 내 자료 관리(라이브러리)에서 자료 업로드(유형 지정) 또는 기존 자료 선택
    
5. 프로젝트에 필요한 라이브러리 자료 연결
    
6. 목차 입력 + 섹션별 “검색 필요” 체크
    
7. 초안 생성 → “확인 필요(시스템)” 표기 + 질문 리스트 확인/해결
    
8. 평가항목 매핑 검증 → 누락 경고 해결 + 문단별 가점 요소 반영
    
9. Export 실행 → **미리보기 화면**에서 “수정(편집으로)” 또는 “다운로드”
    
10. (선택) 편집기에서 드래그 후 “이 부분 수정 요청하기”로 부분 재작성
    

---

## 4) Requirements + Acceptance Criteria (core only, clear)

### 핵심 요구사항

- R1. 공고 PDF 업로드 및 텍스트 추출(부족 시 OCR 옵션 표시)
    
- R2. 요구사항(지원자격/제출서류/평가항목/분량·서식/마감일 등) 구조화 추출 + 사용자 확정
    
- R3. 내 자료 라이브러리: 업로드 시 사용자가 자료 유형을 지정(회사소개/제품/실적/인력/특허/재무/레퍼런스/기타)
    
- R4. 목차 입력 + 섹션별 `검색 필요` 체크(체크된 섹션만 검색 실행)
    
- R5. 초안 생성: 자료 자동 삽입 + 부족정보는 “확인 필요(시스템)” 표기 + 질문 리스트 생성
    
- R6. “확인 필요(시스템)” UI: 사용자 입력과 **명확히 구분**(배지/아이콘/카드) + 질문 패널(점프/해결)
    
- R7. 평가항목 매핑 자동 추천/검증: 누락 경고 + 강화 제안 + 수동 수정 가능
    
- R8. Export: 생성 후 **미리보기 화면**에서 수정/다운로드 선택
    
- R9. 부분 수정 요청(선택): 사용자가 선택한 범위만 LLM으로 재작성 후 적용/취소
    

### Acceptance Criteria (Given/When/Then)

- AC1 (PDF 업로드)
    
    - Given 프로젝트가 존재한다
        
    - When 사용자가 공고 PDF를 업로드한다
        
    - Then 텍스트 추출을 시도하고 결과가 부족하면 “OCR 필요(옵션)” 상태를 표시한다
        
- AC2 (요구사항 확정)
    
    - Given 추출된 요구사항 필드가 표시된다
        
    - When 사용자가 필드를 수정하고 “확정”한다
        
    - Then 확정본이 저장되며 이후 초안 생성에 사용된다
        
- AC3 (라이브러리 업로드 유형 지정)
    
    - Given 사용자가 내 자료 관리 페이지에 있다
        
    - When 업로드 시 자료 유형을 선택하고 파일을 올린다
        
    - Then 해당 유형으로 저장되며 목록에서 필터링 가능하다
        
- AC4 (“확인 필요(시스템)” 시각적 구분)
    
    - Given 초안에 확인 필요 항목이 존재한다
        
    - When 사용자가 편집/미리보기 화면을 본다
        
    - Then 시스템 표기는 배지/아이콘/카드로 사용자 입력과 구분되며, 질문 패널에서 동일 항목을 확인하고 해당 문단으로 이동할 수 있다
        
- AC5 (매핑 누락 경고)
    
    - Given 평가항목과 초안이 존재한다
        
    - When 매핑 검증을 실행한다
        
    - Then 평가항목별 대응 섹션이 표시되고, 대응이 없거나 약하면 경고가 생성된다
        
- AC6 (Export 미리보기)
    
    - Given 사용자가 Export를 실행했다
        
    - When Export가 완료된다
        
    - Then 미리보기 화면이 표시되고 사용자는 “수정(편집으로)” 또는 “다운로드”를 선택할 수 있다
        
- AC7 (부분 수정)
    
    - Given 사용자가 편집기에서 텍스트 일부를 선택했다
        
    - When “이 부분 수정 요청하기”에 지시를 입력하고 실행한다
        
    - Then 선택된 구간만 교체되며, 적용 전 “적용/취소”가 가능하다
        

---

## 5) IPO Design

### Input

- 공고 PDF(텍스트/스캔 혼재)
    
- 사용자 확정 요구사항 데이터(필드 형태)
    
- 라이브러리 자료(파일 + 사용자 지정 유형 + 제목)
    
- 프로젝트 연결된 자료 목록
    
- 목차 트리 + 섹션별 needs_search 플래그
    
- 초안(섹션별 Markdown/Text)
    
- (선택) 부분 수정: 선택 텍스트 범위 + 사용자 지시문
    

### Process

1. PDF 텍스트 추출 → 부족 시 OCR 옵션
    
2. 요구사항/평가항목 추출(규칙 + LLM 보조) → 사용자 확정
    
3. 라이브러리 자료를 프로젝트에 연결(참조 풀 구성)
    
4. 목차 기반 초안 생성(섹션별) + 자료 삽입 + 부족정보 질문(OpenQuestion) 생성
    
5. needs_search=true 섹션만 검색 실행(출처 저장)
    
6. 평가항목 ↔ 섹션 매핑 추천 + 커버리지 점검 + 누락/약함 경고 + 강화 제안
    
7. Export 생성 → 미리보기 화면 제공 → 다운로드
    

### Output

- 구조화 요구사항/평가항목 데이터(확정본)
    
- 초안(섹션별 Markdown)
    
- OpenQuestion(질문 리스트) + 본문 내 시스템 표기
    
- 매핑 결과 + 경고 + 강화 제안
    
- 산출물 파일(md/txt/docx/xlsx) + 미리보기 데이터
    

---

## 6) Data Model + API Contract (if applicable)

### Data Model (SQLite 기본, Postgres 전환 가능)

- Project: id, name, owner_user_id(기본 “local”), created_at, updated_at
    
- ProjectFile: id, project_id, kind(rfp_pdf/export), filename, mime, path, size, created_at
    
- RfpExtraction(1:1): project_id, status(draft/confirmed), eligibility_text, submission_docs_text, evaluation_overview_text, format_rules_text, deadline_iso, contact_text, notes_text
    
- EvaluationItem: id, project_id, code, title, description, weight(optional)
    
- LibraryAsset: id, owner_user_id(기본 “local”), category(필수), title, filename, mime, path, created_at
    
- ProjectAssetLink: project_id, asset_id, usage_note(optional)
    
- OutlineSection: id, project_id, parent_id, order, title, needs_search(bool)
    
- DraftSection: id, project_id, outline_section_id, content_md, status(generated/edited), updated_at
    
- OpenQuestion: id(예: oq_001), project_id, outline_section_id(nullable), question_text, status(open/resolved), created_at
    
- Citation: id, project_id, outline_section_id, source_title, source_url, snippet, accessed_at
    
- EvalMapping: id, project_id, evaluation_item_id, outline_section_id, strength_score(0~1), rationale_text
    
- MappingWarning: id, project_id, type(missing/weak/overlap), evaluation_item_id(nullable), outline_section_id(nullable), message
    
- ExportSession: id, project_id, created_at, preview_md_path, files_json(생성된 파일 목록), status
    

### API Contract (MVP REST)

- Health
    
    - `GET /api/health` → `{ "ok": true }`
        
- Projects
    
    - `POST /api/projects` `{ "name": "..." }`
        
    - `GET /api/projects`
        
    - `GET /api/projects/{projectId}`
        
- RFP upload & extraction
    
    - `POST /api/projects/{projectId}/rfp/upload` (multipart: file)
        
    - `GET /api/projects/{projectId}/rfp/extraction`
        
    - `PATCH /api/projects/{projectId}/rfp/extraction` (사용자 수정/확정)
        
- Evaluation items
    
    - `POST /api/projects/{projectId}/evaluation-items` `{ items: [...] }`
        
    - `GET /api/projects/{projectId}/evaluation-items`
        
- Library (내 자료 관리)
    
    - `POST /api/library/assets` (multipart: category, title, file)
        
    - `GET /api/library/assets?category=...`
        
    - `POST /api/projects/{projectId}/assets/link` `{ "assetIds": [...] }`
        
    - `GET /api/projects/{projectId}/assets`
        
- Outline
    
    - `POST /api/projects/{projectId}/outline` `{ "sections": [...] }`
        
    - `GET /api/projects/{projectId}/outline`
        
- Draft
    
    - `POST /api/projects/{projectId}/draft/generate` `{ "mode": "full" }`
        
    - `GET /api/projects/{projectId}/draft/sections`
        
    - `PATCH /api/projects/{projectId}/draft/sections/{sectionId}` `{ "contentMd": "..." }`
        
- Open Questions
    
    - `GET /api/projects/{projectId}/questions`
        
    - `PATCH /api/projects/{projectId}/questions/{questionId}` `{ "status": "resolved" }`
        
- Search (체크된 섹션만)
    
    - `POST /api/projects/{projectId}/search/run` `{ "sectionIds": [...] }`
        
- Mapping
    
    - `POST /api/projects/{projectId}/mapping/run` `{ "strategy": "llm+rules" }`
        
    - `GET /api/projects/{projectId}/mapping`
        
    - `PATCH /api/projects/{projectId}/mapping` `{ "links": [...] }`
        
- Partial rewrite (선택)
    
    - `POST /api/projects/{projectId}/rewrite`
        
        - Request:
            
            ```json
            {
              "sectionId": "sec_1",
              "selectedText": "선택한 텍스트",
              "instruction": "이 부분을 평가항목 2에 더 맞게 강화해줘"
            }
            ```
            
        - Response:
            
            ```json
            { "replacementText": "대체 텍스트", "diffHint": "optional" }
            ```
            
- Export (미리보기 우선)
    
    - `POST /api/projects/{projectId}/export` `{ "formats": ["md","txt","docx","xlsx"] }`
        
    - `GET /api/projects/{projectId}/export/{exportSessionId}/preview` → `{ "previewMd": "..." }`
        
    - `GET /api/projects/{projectId}/export/{exportSessionId}/download?format=md` → file stream
        

---

## 7) Tech Stack & Environment (versions) + setup commands + .env.example

### Primary Stack (확정)

- Frontend: Next.js + TypeScript
    
- Backend: Python + FastAPI
    
- DB: SQLite 기본(전환점: `DATABASE_URL`)
    
- ORM/Migration: SQLAlchemy + Alembic
    
- Doc generation: python-docx, openpyxl
    
- PDF text: pypdf(우선)
    
- LLM: OpenAI API (앱 기능용; 개발용 Codex CLI와 별개)
    

### 권장 버전(초보 친화)

- Node.js: 24.x (LTS 계열)
    
- Python: 3.12+
    
- FastAPI: 최신 안정(설치 시점 기준)
    
- SQLite: 내장
    
- (옵션) OCR: tesseract, poppler-utils
    

### 로컬 실행 커맨드(WSL)

```bash
# backend
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (새 터미널)
cd web
npm install
npm run dev
```

### .env.example

`/api/.env.example`

```env
# LLM
OPENAI_API_KEY=YOUR_KEY
OPENAI_MODEL_DRAFT=gpt-4.1-mini
OPENAI_MODEL_MAPPING=gpt-5-mini

# DB (SQLite default; later swap to Postgres)
DATABASE_URL=sqlite:///../data/app.db

# Paths
APP_DATA_DIR=../data
UPLOAD_DIR=../data/uploads
EXPORT_DIR=../data/exports

# Limits
MAX_UPLOAD_MB=50

# OCR (optional)
OCR_ENABLED=false
```

`/web/.env.local.example`

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## 8) Architecture Summary (diagram + module responsibilities)

### 아키텍처 다이어그램

```text
Next.js Web(UI)
  - 프로젝트/공고/목차/초안/매핑/Export
  - 시스템표기(확인 필요) 카드 + 질문 패널
  - 선택영역 부분수정(옵션)
        |
        v
FastAPI(API)
  routes -> services -> repositories(DB) / storage(files)
        |
        +-> OpenAI(초안/매핑/부분수정/선택검색)
        +-> PDF extract (+ OCR optional)
        +-> docx/xlsx exporters
```

### 모듈 책임(백엔드)

- `routes/*`: 입력 검증/HTTP, 상태코드
    
- `services/*`:
    
    - `pdf_service`: PDF 텍스트 추출 + 추출량 기반 OCR 필요 판단
        
    - `rfp_service`: 요구사항/평가항목 추출 + 확정 저장
        
    - `library_service`: 라이브러리 업로드(유형 지정 필수) + 프로젝트 연결
        
    - `outline_service`: 목차 CRUD + needs_search
        
    - `draft_service`: 초안 생성(섹션별) + OpenQuestion 생성 + 시스템 표기 삽입
        
    - `mapping_service`: 평가항목↔섹션 매핑 추천/검증 + 경고/강화 제안
        
    - `search_service`: needs_search 섹션만 검색 + Citation 저장
        
    - `rewrite_service`: 선택영역 부분수정(선택 텍스트만 교체)
        
    - `export_service`: ExportSession 생성 + 미리보기용 md + 파일 생성/다운로드
        
- `repositories/*`: DB 접근 캡슐화(나중에 DB 교체 영향 최소화)
    
- `storage/*`: `StorageProvider` (LocalStorageProvider 기본)
    

### 모듈 책임(프론트)

- 에디터: `EditorTextarea` (선택 범위 추출, 부분수정 호출)
    
- 시스템 표기: `SystemNotice` (배지/아이콘/카드 렌더)
    
- 질문 패널: `OpenQuestionPanel` (점프/해결)
    
- Export 미리보기: `ExportPreviewPanel` (수정/다운로드)
    

---

## 9) Bootstrap File/Folder Structure

### target folder tree

```text
rfp-copilot/
  PROJECT_CONTEXT.md
  README.md
  ARCHITECTURE.md
  scripts/
    dev-api.sh
    dev-web.sh
  data/
    uploads/.gitkeep
    exports/.gitkeep
  api/
    .env.example
    requirements.txt
    alembic.ini
    alembic/
      env.py
      versions/.gitkeep
    app/
      main.py
      core/
        config.py
        logging.py
      db/
        base.py
        session.py
      models/
        project.py
        rfp.py
        evaluation.py
        library.py
        outline.py
        draft.py
        mapping.py
        export.py
      schemas/
        project.py
        rfp.py
        evaluation.py
        library.py
        outline.py
        draft.py
        mapping.py
        export.py
      repositories/
        project_repo.py
        rfp_repo.py
        library_repo.py
        outline_repo.py
        draft_repo.py
        mapping_repo.py
        export_repo.py
      services/
        storage_provider.py
        pdf_service.py
        ocr_service.py
        llm_service.py
        rfp_service.py
        library_service.py
        outline_service.py
        draft_service.py
        search_service.py
        mapping_service.py
        rewrite_service.py
        export_service.py
      routes/
        health.py
        projects.py
        rfp.py
        evaluation.py
        library.py
        outline.py
        draft.py
        mapping.py
        export.py
  web/
    .env.local.example
    package.json
    tsconfig.json
    next.config.js
    app/
      layout.tsx
      page.tsx
      projects/
        page.tsx
        [id]/
          page.tsx
          rfp/page.tsx
          outline/page.tsx
          draft/page.tsx
          mapping/page.tsx
          export/page.tsx
      library/
        page.tsx
    components/
      FileUploader.tsx
      EditorTextarea.tsx
      MarkdownPreview.tsx
      SystemNotice.tsx
      OpenQuestionPanel.tsx
      MappingMatrix.tsx
      ExportPreviewPanel.tsx
    lib/
      api.ts
      types.ts
```

### list of files to generate in first session (1-line purpose)

- `/PROJECT_CONTEXT.md`: 결정/가정/다음 작업의 “공식 기록”
    
- `/README.md`: 설치/실행/사용 흐름 요약
    
- `/ARCHITECTURE.md`: 구조/데이터모델/API/폴더 상세
    
- `/scripts/dev-api.sh`: 백엔드 실행 단축 스크립트
    
- `/scripts/dev-web.sh`: 프론트 실행 단축 스크립트
    
- `/api/app/main.py`: FastAPI 엔트리포인트 + 라우터 등록
    
- `/api/app/core/config.py`: 환경변수/경로/제한값 설정
    
- `/api/app/services/llm_service.py`: OpenAI 호출 래퍼(초안/매핑/부분수정 공통)
    
- `/web/app/projects/[id]/draft/page.tsx`: 편집기 + 질문패널 + 부분수정 UI 뼈대
    
- `/web/app/projects/[id]/export/page.tsx`: 미리보기 + 수정/다운로드 UI 뼈대
    

## 10) Documentation Pack (initial drafts)

### /PROJECT_CONTEXT.md

```md
# PROJECT_CONTEXT — RFP Copilot
## 1. 한 줄 요약
공고 PDF 요구사항/평가항목 추출 → 자료 라이브러리 기반 초안 생성 → 평가항목 매핑 검증 → 웹 편집 후 산출물(md/txt/docx/xlsx) 생성하는 로컬 웹앱.

## 2. MVP 목표
- 공고 PDF 업로드 및 요구사항/평가항목 구조화 + 사용자 확정
- 내 자료 라이브러리(유형 지정 업로드) + 프로젝트 연결
- 목차 기반 초안 생성 + “확인 필요(시스템)” 표기/질문 리스트 UI
- 평가항목 매핑 검증(누락 경고 + 강화 제안)
- Export 미리보기 → 수정/다운로드 흐름

## 3. 현재 결정된 사항(Decision Log)
1) 단일 사용자 로컬 실행(MVP)으로 시작한다.
2) 자료(회사소개/제품/실적/인력/특허/재무/레퍼런스)는 자동 태깅/분해하지 않고 업로드 시 사용자가 유형을 지정한다.
3) DB는 SQLite로 시작하되, DATABASE_URL 기반으로 Postgres 전환이 가능하도록 ORM+마이그레이션을 적용한다.
4) 초안 편집은 Markdown/Text 중심이며, HWP 최종 양식은 사람이 마무리한다.
5) “확인 필요(시스템)”는 본문 표기 + 질문 패널 UI로 사용자 입력과 명확히 구분한다.
6) Export는 미리보기 화면을 기본으로 두고, 거기서 수정/다운로드로 분기한다.
7) 선택 영역 “부분 수정 요청하기” 기능을 옵션으로 포함한다.
8) AGENTS.md 및 PLANS/ExecPlan을 생성한다(멀티패키지 + 순서 의존 작업이 많음).

## 4. 현재 상태 요약
- 상태: Bootstrap 설계 완료, 코드 스캐폴딩 생성 대기
- 우선순위: 1) 프로젝트/라이브러리 업로드 2) 초안 편집기+질문UI 3) 매핑 검증 4) Export 미리보기

## 5. 다음 작업(Next Actions)
1) repo 스캐폴딩 생성(api/web/data/scripts + 기본 문서)
2) FastAPI /health + Next.js 기본 라우팅 연결
3) 프로젝트 CRUD 최소 구현
4) 라이브러리 업로드(유형 지정) + 프로젝트 연결
5) 초안 편집기 + “확인 필요(시스템)” 렌더 + 질문 패널

## 6. 중요한 제약/주의사항
- 공고 PDF는 텍스트/스캔 혼재: OCR은 옵션이며 기본은 텍스트 추출 우선
- 업로드 파일 크기 제한 및 경로 sanitize 필수(보안 최소선)
- OpenAI API 키는 .env로만 관리(하드코딩 금지)
- 시스템 표기는 사용자 텍스트와 혼동되지 않게 UI/텍스트 모두에서 구분해야 함

## 7. 미결 사항(Open Questions)
- TBD (현재 없음)
```

### /README.md

````md
# RFP Copilot
## 1. 한 줄 요약
공고 PDF와 회사 자료를 바탕으로 제안서 초안을 만들고, 평가항목 매핑 누락을 자동 경고하며, 웹에서 편집 후 산출물을 내보내는 로컬 웹앱.

## 2. 프로젝트 목적
- 공고 요구사항/평가항목을 구조화해 제안서 작성 시간을 줄인다.
- 평가항목-문단 매핑 검증으로 “빠진 항목”을 사전에 차단한다.

## 3. 대상 사용자
- 로컬에서 혼자 제안서 초안을 만들고 싶은 사용자(초보 포함)

## 4. 핵심 기능
- 공고 PDF 업로드 → 요구사항/평가항목 추출 및 확정
- 내 자료 라이브러리(유형 지정 업로드) + 프로젝트 연결
- 목차 기반 초안 생성 + “확인 필요(시스템)” 표기/질문 리스트
- 평가항목 매핑 검증(누락 경고 + 강화 제안)
- Export 미리보기 → 수정/다운로드
- (옵션) 선택 영역 부분 수정 요청

## 5. 기술 스택
- Frontend: Next.js + TypeScript
- Backend: FastAPI (Python)
- DB: SQLite (DATABASE_URL로 Postgres 전환 가능)
- 문서 생성: python-docx, openpyxl

## 6. 설치 및 실행 방법
### 6.1 요구사항
- WSL(리눅스) 환경
- Node.js 24.x
- Python 3.12+

### 6.2 설치
```bash
# backend
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# frontend
cd ../web
npm install
```

### 6.3 환경 변수(.env)

- api: `api/.env` (템플릿: `api/.env.example`)
    
- web: `web/.env.local` (템플릿: `web/.env.local.example`)
    

### 6.4 실행

```bash
# backend
cd api
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# frontend (다른 터미널)
cd web
npm run dev
```

### 6.5 테스트

TBD (pytest 기반으로 추가 예정)

## 7. 폴더 구조 요약

- `api/`: FastAPI 백엔드
- `web/`: Next.js 프론트엔드
- `data/`: 업로드/산출물 로컬 저장
- `scripts/`: 실행 스크립트
    

## 8. 사용 방법

1. 프로젝트 생성
2. 공고 PDF 업로드 → 요구사항/평가항목 확정
3. 내 자료 관리에서 자료 업로드(유형 지정) → 프로젝트 연결
4. 목차 입력 + 검색 필요 체크
5. 초안 생성 → 질문(확인 필요) 해결
6. 매핑 검증 → 누락 경고 해결
7. Export → 미리보기 → 수정/다운로드
    

## 9. 문제 해결

- OpenAI 키 오류: `api/.env`의 `OPENAI_API_KEY` 확인
- PDF 추출 실패: 스캔 PDF일 수 있음(OCR 옵션 사용)
    

## 10. 참고/링크

- TBD
    

````

### /ARCHITECTURE.md
```md
# ARCHITECTURE — RFP Copilot
## 1. 설계 목표(Goals) / 비목표(Non-goals)
### Goals
- 로컬 단일 사용자로 빠르게 사용 가능(초보 친화)
- DB/스토리지 교체 가능(확장 대비)
- 평가항목 매핑 검증을 핵심 기능으로 강화
- “확인 필요(시스템)” 표기의 명확한 UI 구분
- Export 미리보기 → 수정/다운로드 UX

### Non-goals
- HWP 완전 자동 편집/서식 완벽 지원
- 협업 기능(권한/코멘트/실시간 공동편집)
- OCR 고정밀 보장

## 2. 전체 구조 개요
- web(Next.js) ↔ api(FastAPI) REST
- api는 services 중심으로 비즈니스 로직 분리
- 저장: DB(SQLite 기본) + 파일 스토리지(로컬 폴더)

## 3. 컴포넌트 책임 분리(역할)
- routes: HTTP / validation
- services: pdf/rfp/library/outline/draft/mapping/search/export/rewrite
- repositories: DB CRUD 캡슐화
- storage_provider: 로컬 저장(추후 S3/MinIO 확장)

## 4. 데이터 흐름(주요 시나리오)
1) PDF 업로드 → 텍스트 추출 → 요구사항/평가항목 추출
2) 사용자 확정 → 목차 입력 → 초안 생성
3) 초안 생성 시 OpenQuestion 생성 + 본문에 시스템 표기 삽입
4) 매핑 검증 → 경고/강화 제안 표시 → 사용자 수정 반영
5) Export → ExportSession 생성 → 미리보기 → 다운로드

## 5. API 설계(해당 시)
- /api/projects, /api/library/assets, /api/projects/{id}/draft/generate, /api/projects/{id}/mapping/run, /api/projects/{id}/export 등
- 에러: 400(입력), 413(용량), 422(손상 파일), 500(생성 실패)

## 6. 데이터 모델(해당 시)
- Project / RfpExtraction / EvaluationItem / LibraryAsset / OutlineSection / DraftSection / OpenQuestion / EvalMapping / ExportSession 등
- owner_user_id는 MVP에서 “local” 고정(멀티유저 대비)

## 7. 폴더/파일 구조
- /api/app/services/* : 비즈니스 로직
- /web/app/** : 페이지 라우팅
- /web/components/* : UI 컴포넌트

## 8. 핵심 설계 결정(왜 이렇게 했는가)
- SQLite로 시작하되 DATABASE_URL로 DB 교체 가능(확장 대비)
- StorageProvider 추상화로 로컬→S3 전환 가능
- 시스템 표기는 “본문 표기 + DB(OpenQuestion) + UI 패널”로 3중 보장

## 9. 에러 처리 & 로깅 규칙
- 모든 API는 에러 시 {code, message, detail} 형태로 통일
- 업로드/생성 작업은 실패 사유를 저장하고 재시도 가능하게 설계
- 로그 레벨: INFO 기본, 예외는 ERROR

## 10. 테스트 전략
- 백엔드: PDF 추출, 라이브러리 업로드 검증, 초안/질문 생성, 매핑 경고, export 생성, 부분수정
- 프론트: 선택영역 버튼 동작, export 미리보기에서 수정/다운로드 흐름

## 11. 배포/운영(선택)
- MVP는 로컬 실행
- 추후 self-host 시: Postgres + S3/MinIO + 인증 추가 고려
````

---

## 11) Decision Log + Assumptions + Open Questions

### Decision Log

1. **로컬 단일 사용자 MVP**로 시작: 초보 친화와 빠른 완성을 우선.
    
2. 라이브러리 자료는 **자동 분해/태깅 없이**, 업로드 시 사용자가 **유형을 지정**: 예측 가능하고 UI/로직 단순.
    
3. DB는 **SQLite 기본 + DATABASE_URL로 Postgres 전환 가능**(SQLAlchemy+Alembic): 나중에 확장 시 재작성 최소화.
    
4. 파일 저장은 `StorageProvider`로 추상화(로컬 기본): 나중에 S3/MinIO 전환 대비.
    
5. 편집은 **Markdown/Text 중심**: HWP는 사람이 최종 마무리.
    
6. “확인 필요(시스템)”는 **본문 표기 + 질문 패널 UI**로 시각적/텍스트적 구분을 강제.
    
7. Export는 **미리보기 → 수정/다운로드** UX를 표준으로 고정.
    
8. AGENTS.md 생성: 모노레포+규칙이 많아 Codex 실수 방지에 효과적.
    
9. PLANS/ExecPlan 생성: FE/BE/문서생성/매핑/검색/Export로 작업 순서 의존도가 높음.
    

### Assumptions

- OpenAI API 키는 사용자가 보유하고, `.env`로 주입한다.
    
- OCR은 기본 OFF이며, 스캔 PDF에서만 옵션으로 활성화한다.
    
- docx/xlsx는 “다운로드 우선”이며, 웹 내 완벽 미리보기는 MVP에서 필수 아님.
    
- 에디터는 MVP에서 textarea 기반(선택영역 기능 구현 쉬움)으로 시작한다.
    

### Open Questions (max 5)

- (없음) — MVP 부트스트랩에 필요한 결정은 완료.