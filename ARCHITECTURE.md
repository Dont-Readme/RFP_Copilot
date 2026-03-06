# ARCHITECTURE — RFP Copilot
## 1. 설계 목표(Goals) / 비목표(Non-goals)
### Goals
- 로컬 단일 사용자로 빠르게 사용 가능
- DB/스토리지 교체 가능
- OpenAI 기반 추출/생성/대화 편집 루프를 빠르게 검증
- 업로드 문서를 retrieval context로 재사용
- "확인 필요(시스템)" 표기의 명확한 UI 구분
- Export 미리보기 → 수정/다운로드 UX

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
- services: pdf/rfp/library/outline/draft/mapping/search/export/rewrite
- repositories: DB CRUD 캡슐화
- storage_provider: 로컬 저장 구현과 추후 확장 포인트

## 4. 데이터 흐름(주요 시나리오)
1. 공고/RFP와 회사 자료 업로드 → 텍스트 추출/로컬 chunk 저장
2. 사용자가 업로드 완료 파일 중 추출 대상만 체크 → 공고 파일 role과 routed chunk를 사용한 `사업 개요 템플릿 / 요구사항` section별 OpenAI structured extraction → 사용자 검토/확정
3. 사용자가 `Outline`에서 `depth/title`를 조정하면 `display_label`은 자동 번호로 계산되어 저장
4. `Draft`에서 추출 상태 + 연결 자료 + 저장된 목차를 확인한 뒤 초안 생성 실행
5. `draft/plan`에서 목차별 관련 요구사항과 RFP/회사 자료 chunk를 추천하고 사용자가 포함·제외를 조정
6. 업로드 문서 chunk retrieval → 섹션별 컨텍스트 조합
7. 추출된 RFP + 선택된 retrieved chunk를 사용한 section별 OpenAI 초안 생성 → OpenQuestion/시스템 표기 삽입
8. 편집기에서 선택 구간 기준 AI chat/apply 수정 → 적용/취소
9. Export → 미리보기 → 다운로드

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
  - `/api/projects/{project_id}/draft/generate` `POST`
  - `/api/projects/{project_id}/draft/sections` `GET`
  - `/api/projects/{project_id}/draft/sections/{section_id}` `PATCH`
  - `/api/projects/{project_id}/draft/sections/{section_id}/chat` `GET`
  - `/api/projects/{project_id}/draft/chat` `POST`
  - `/api/projects/{project_id}/draft/chat/{message_id}/apply` `POST`
  - `/api/projects/{project_id}/questions` `GET`
  - `/api/projects/{project_id}/questions/{question_id}` `PATCH`
  - `/api/projects/{project_id}/mapping` `GET`
  - `/api/projects/{project_id}/mapping/run` `POST`
  - `/api/projects/{project_id}/export` `POST`
  - `/api/projects/{project_id}/export/{export_session_id}/preview` `GET`
  - `/api/projects/{project_id}/export/{export_session_id}/download` `GET`
  - `/api/projects/{project_id}/rewrite` `POST`
  - `/api/health/openai` `GET`
- 에러 형태: `{ code, message, detail }`

## 6. 데이터 모델(해당 시)
- `Project`: 현재 구현
- `LibraryAsset`, `ProjectAssetLink`, `DraftSection`, `OpenQuestion`: 현재 구현
- `ProjectFile(role 포함)`, `RfpExtraction(project_summary_text 포함)`, `RfpRequirementItem`, `EvaluationItem(score_text 포함)`, `OutlineSection`, `Citation`, `EvalMapping`, `MappingWarning`, `ExportSession`, `DocumentChunk`, `DraftChatMessage`: 현재 구현
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
- 시스템 표기는 "본문 표기 + DB(OpenQuestion) + UI 패널" 구조를 유지할 수 있게 뼈대를 먼저 만들었다.
- RFP 추출은 텍스트 우선으로 처리하고, 스캔/OCR 필요 여부만 메타데이터로 남긴다.
- RFP/회사자료는 먼저 로컬 chunk로 저장하고, 추출/생성에는 필요한 chunk만 넣어 whole-document prompt를 피한다.
- RFP 추출은 routed chunk를 묶어 섹션별 OpenAI structured output으로 구현한다.
- RFP 프롬프트는 `api/app/services/rfp_prompts.py`에 모아 사용자 조정 지점을 명확히 둔다.
- 공고 파일 업로드는 저장과 chunk 준비까지만 수행하고, 실제 추출은 사용자가 명시적으로 실행해 토큰 사용을 제어한다.
- RFP 추출은 사용자가 체크한 파일만 대상으로 수행해 불필요한 토큰 사용과 timeout 위험을 줄인다.
- OpenAI request timeout 기본값은 120초로 두고, section 추출은 timeout 시 1회 재시도한다.
- draft 편집은 전체 초안을 다시 생성하지 않고, 선택 구간과 주변 문맥만 사용한 chat/apply로 토큰 사용을 낮춘다.
- 매핑 검증은 단순 토큰 겹침 기반 휴리스틱으로 시작해 후속 고도화를 열어 둔다.
- Export는 세션별 폴더를 만들어 preview와 산출물 경로를 함께 관리한다.
- outline은 구조 정의 전용으로 두고, ordered flat list + `depth`로 계층을 표현하며 번호는 `display_label`에 자동 계산해 저장한다.
- 검색/인용은 outline에서 제거하고, 생성 제어는 draft preparation 영역으로 이동한다.
- draft 생성은 먼저 목차별 plan을 계산하고, 사용자가 고른 requirement/chunk만으로 section별 generation을 수행한다.
- search는 현재 외부 웹 검색이 아니라 프로젝트에 저장된 RFP/연결 자료 chunk를 lexical retrieval로 재활용해 Citation을 생성한다.
- OpenAI 키는 `api/.env`에서 읽고, `/api/health/openai`로 모델 접근을 검증한다.
- retrieval은 우선 로컬 파일 chunk + SQLite 메타데이터 + lexical scoring으로 시작하고, 필요 시 embedding/vector store로 확장한다.

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
