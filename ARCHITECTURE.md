# ARCHITECTURE — RFP Copilot
## 1. 설계 목표(Goals) / 비목표(Non-goals)
### Goals
- 로컬 단일 사용자로 빠르게 사용 가능
- DB/스토리지 교체 가능
- OpenAI 기반 추출/생성/대화 편집 루프를 빠르게 검증
- 업로드 문서를 retrieval context로 재사용
- 초안을 본문 완결형으로 최대한 생성하고, 별도 확인 항목 의존도를 줄이기
- draft 편집 직후 즉시 다운로드 UX

### Non-goals
- HWP 완전 자동 편집/서식 완벽 지원
- 협업 기능(권한/코멘트/실시간 공동편집)
- OCR 고정밀 보장

## 2. 전체 구조 개요
- `web`(Next.js) ↔ `api`(FastAPI) REST
- `api`는 routes → repositories/services → DB/파일 저장으로 분리
- 저장소는 DB(SQLite 기본) + 파일 스토리지(로컬 폴더)

## 3. 컴포넌트 책임 분리(역할)
- routes: HTTP 처리, validation, status code
- services: pdf/rfp/library/outline/draft/search/export/rewrite
- repositories: DB CRUD 캡슐화
- storage_provider: 로컬 저장 구현과 추후 확장 포인트

## 4. 데이터 흐름(주요 시나리오)
1. 공고/RFP와 회사 자료 업로드 → 텍스트 추출/로컬 chunk 저장. 회사 자료는 PDF/TXT/MD/XLSX/CSV/TSV를 지원하고, PDF 텍스트가 비어 있으면 OCR fallback을 시도
2. 사용자가 업로드 완료 파일 중 추출 대상만 체크하고, 별도로 요구사항 소스 파일과 페이지 범위를 지정 → 공고 파일 role과 generic chunk를 사용한 `사업 개요 템플릿 / 요구사항` 추출. 이 중 요구사항은 지정한 소스 범위만 후보 단위로 다시 분해해 배치별 OpenAI structured extraction으로 합친 뒤 사용자 검토/확정
3. 사용자가 `Outline`에서 `depth/title`를 조정하면 `display_label`은 자동 번호로 계산되어 저장
4. `Draft`에서 추출 상태 + 연결 자료 + 저장된 목차를 확인한 뒤 초안 생성 실행
5. `draft/plan`에서 readiness, 작성 의도, section plan, generation unit, requirement coverage를 계산
6. AI planner(A)는 먼저 목차 역할과 outline 적합성을 해석하고, 이어서 요구사항 배치별로 generation unit과 requirement coverage를 생성한다. generation unit에는 planned search intent도 같이 포함되며, 검색 intent는 백엔드 `research_playbooks.py` 가이드를 1차 참고자료로 삼아 LLM이 생성한다. 이 가이드는 `unit_pattern`별 기본 planned search 여부, adaptive search 허용 조건, 우선 출처, 반드시 뽑을 정보, 초안 표현 힌트를 포함한다. outline이 성기면 내부 generation unit을 추가해 모든 요구사항에 primary coverage를 배정하고, 목차가 부적절하면 coverage warning과 사용자 확인 플래그를 반환한다
7. 공통 research API(C)는 OpenAI `Responses API + web_search`를 사용해 planned search를 먼저 수행하고, unit 생성 직전 LLM이 adaptive search 필요 여부를 한 번 더 판단한다. 검색 실행 로그는 `draft_search_tasks`에 저장되며, 같은 프로젝트에서 같은 날 같은 query/purpose/allowed_domains 조합이면 재검색 대신 기존 결과를 재사용한다. `execution/strategy` unit은 designer(B1)가 결합된 검색 결과를 받아 구조화된 실행 blueprint를 만들고, writer(B2)가 section이 아니라 generation unit별 초안을 쓴다. writer는 unit별 `writing_mode`, `unit_pattern`, `required_aspects`, blueprint, 결합된 검색 결과를 받아 구체적인 실행안 중심으로 작성하며, 기본 출력 형식은 `☐ / ○ / -` 개조식 Markdown이다. 필요 시 Markdown 표와 `<그림>`, `<도식>` placeholder를 본문에 직접 넣는다
8. draft 편집기에서 chat/apply 수정 및 md/txt 다운로드를 실행한다

## 5. API 설계(해당 시)
- 현재 구현:
  - `/api/health`
  - `/api/projects` `GET/POST`
  - `/api/projects/{project_id}` `GET/PATCH/DELETE`
  - `/api/projects/{project_id}/rfp/files` `GET/POST`
  - `/api/projects/{project_id}/rfp/files/{file_id}` `DELETE`
  - `/api/projects/{project_id}/rfp/upload` `POST` (legacy alias)
  - `/api/projects/{project_id}/rfp/extract` `POST`
  - `/api/projects/{project_id}/rfp/extraction` `GET/PATCH`
  - `/api/library/assets` `GET/POST`
  - `/api/projects/{project_id}/assets` `GET`
  - `/api/projects/{project_id}/assets/link` `POST`
  - `/api/projects/{project_id}/outline` `GET/POST`
  - `/api/projects/{project_id}/search/citations` `GET`
  - `/api/projects/{project_id}/search/run` `POST`
  - `/api/projects/{project_id}/draft/plan` `GET`
  - `/api/projects/{project_id}/draft/planning-config` `GET/PUT`
  - `/api/projects/{project_id}/draft/generate` `POST`
  - `/api/projects/{project_id}/draft/sections` `GET`
  - `/api/projects/{project_id}/draft/sections/{section_id}` `PATCH`
  - `/api/projects/{project_id}/draft/sections/{section_id}/chat` `GET`
  - `/api/projects/{project_id}/draft/chat` `POST`
  - `/api/projects/{project_id}/draft/chat/{message_id}/apply` `POST`
  - `/api/projects/{project_id}/questions` `GET`
  - `/api/projects/{project_id}/questions/{question_id}` `PATCH`
  - `/api/projects/{project_id}/export` `POST`
  - `/api/projects/{project_id}/export/{export_session_id}/download` `GET`
  - `/api/projects/{project_id}/rewrite` `POST`
  - `/api/health/openai` `GET`
- 에러 형태: `{ code, message, detail }`

## 6. 데이터 모델(해당 시)
- `Project`: 현재 구현
- `LibraryAsset`, `ProjectAssetLink`, `DraftSection`, `OpenQuestion`: 현재 구현
- `ProjectFile(role 포함)`, `RfpExtraction(project_summary_text 포함)`, `RfpRequirementItem`, `EvaluationItem(score_text 포함)`, `OutlineSection`, `Citation`, `ExportSession`, `DocumentChunk`, `DraftChatMessage`: 현재 구현
- `owner_user_id`는 MVP에서 `"local"` 고정

## 7. 폴더/파일 구조
- `/api/app/services/*`: 비즈니스 로직
- `/api/app/repositories/*`: 저장소 접근
- `/web/app/**`: 페이지 라우팅
- `/web/components/*`: UI 컴포넌트
- `/web/lib/*`: API 호출 및 타입

## 8. 핵심 설계 결정(왜 이렇게 했는가)
- SQLite로 시작하되 `DATABASE_URL`로 DB 교체 가능하게 구성했다.
- Alembic을 미리 배치해 마이그레이션 전환 비용을 줄였다.
- `lib/api.ts`를 공용 진입점으로 두어 Next.js 쪽 API 호출 방식을 단일화했다.
- 시스템 표기는 본문과 별도 패널에 의존하지 않고, 생성 프롬프트 단계에서 본문 완결형 품질을 우선한다.
- RFP/회사자료 PDF 추출은 텍스트 우선으로 처리하고, 비어 있는 PDF만 OCR fallback을 시도한다.
- RFP/회사자료는 먼저 로컬 chunk로 저장하고, 추출/생성에는 필요한 chunk만 넣어 whole-document prompt를 피한다.
- 라이브러리 자산 chunk가 `%PDF-`, `PK...` 같은 바이너리성 텍스트로 오염돼 있으면 재사용 대신 자동 재생성한다.
- RFP 추출은 generic chunk를 유지하되, 사업 개요는 관련 chunk를 그대로 사용하고 요구사항은 추출 직전에 후보 단위로 다시 분해해 배치별 OpenAI structured output으로 구현한다.
- 요구사항 소스와 페이지 범위는 현재 `rfp_extractions.source_file_path` 텍스트 컬럼에 JSON으로 저장해 프로젝트 재진입 시 재사용한다.
- LLM 프롬프트는 `api/app/services/prompts/` 아래 기능별 파일에 모아 사용자 조정 지점을 명확히 둔다.
- 실제 prompt 입력값은 `data/debug/project_<id>/prompt_traces/` 아래 JSON trace로 남겨 디버그 화면에서 확인할 수 있다.
- 공고 파일 업로드는 저장과 chunk 준비까지만 수행하고, 실제 추출은 사용자가 명시적으로 실행해 토큰 사용을 제어한다.
- RFP 추출은 사용자가 체크한 파일만 대상으로 수행해 불필요한 토큰 사용과 timeout 위험을 줄인다.
- OpenAI request timeout 기본값은 120초로 두고, section 추출은 timeout 시 1회 재시도한다.
- draft 편집은 전체 초안을 다시 생성하지 않고, 선택 구간과 주변 문맥만 사용한 chat/apply로 토큰 사용을 낮춘다.
- Export는 세션별 폴더를 만들어 md/txt 산출물 경로를 관리한다.
- outline은 구조 정의 전용으로 두고, ordered flat list + `depth`로 계층을 표현하며 번호는 `display_label`에 자동 계산해 저장한다.
- 검색/인용은 outline에서 제거하고, 생성 제어는 draft preparation 영역으로 이동한다.
- draft 생성은 `작성 의도 -> AI planner overview -> 요구사항 배치 planner -> generation unit planned search -> adaptive search 판단 -> generation unit designer/writer` 순서로 수행한다.
- generation unit의 `writing_mode`, `unit_pattern`, `required_aspects`, 권장 표/그림/도식 힌트 기준은 `api/app/services/draft_generation_taxonomy.py`에 중앙 정의해 planner/designer/writer가 공통으로 사용한다.
- 최신 검색은 공통 research API(C)가 OpenAI `Responses API + web_search`에 절대 날짜를 명시해 최신 정보를 찾고, planned/adaptive 검색 결과를 writer 입력과 Citation 저장에 함께 사용한다.
- OpenAI 키는 `api/.env`에서 읽고, `/api/health/openai`로 모델 접근을 검증한다.
- retrieval은 우선 로컬 파일 chunk + SQLite 메타데이터 + lexical scoring으로 시작하고, 필요 시 embedding/vector store로 확장한다.
- 회사 소개/특허/실적처럼 내부 자료가 핵심인 섹션은 내부 asset evidence가 있을 때 일반 외부 검색 태스크를 줄여 내부 근거를 우선 사용한다.

## 9. 에러 처리 & 로깅 규칙
- API 에러 응답은 `code/message/detail` 구조를 사용한다.
- 로그 레벨은 INFO 기본, 예외는 ERROR로 다룬다.
- 업로드/생성 작업은 추후 실패 사유 저장과 재시도 가능 구조로 확장한다.

## 10. 테스트 전략
- 백엔드: OpenAI 설정 확인, routed RFP structured extraction, chunk retrieval, draft generate, chat edit, export 스모크
- 프론트: 업로드 -> 추출 검토 -> 초안 생성 -> 대화형 수정 -> export 흐름 검증
- 스모크 테스트: `uvicorn`과 `next start` 또는 `next dev`를 실행한 뒤 핵심 작성 루프를 처음부터 끝까지 검증

## 11. 배포/운영(선택)
- MVP는 로컬 실행
- 추후 self-host 시 Postgres + S3/MinIO + 인증 추가 고려
