# RFP Copilot
## 1. 한 줄 요약
공고 파일과 회사 자료를 바탕으로 RFP를 구조화하고, 제안서 초안을 만들고, AI와 대화하며 수정한 뒤 산출물을 내보내는 로컬 웹앱.

## 2. 프로젝트 목적
- 공고 요구사항/평가항목을 구조화해 제안서 작성 시간을 줄인다.
- 구조화된 RFP 정보와 초안 생성 흐름을 한 화면에서 관리한다.

## 2.1 현재 방향 메모
- 핵심 작성 루프는 `멀티파일 대기 목록 업로드 -> 체크한 파일만 OpenAI 사업 개요 템플릿/요구사항 추출 -> 초안 생성 -> AI와 대화형 수정 -> 다운로드`다.
- 현재 레포는 이 초기 MVP 루프를 끝까지 연결했고, 목차 정의는 `Outline`, 생성 준비와 초안 생성/편집은 `Draft`로 분리했다.
- `Draft`는 `작성 의도 -> AI planner overview -> 요구사항 배치 planner -> generation unit planned search -> adaptive search 판단 -> generation unit designer/writer` 흐름으로 동작한다.
- generation unit 분류 기준과 `execution` 세부 패턴, 권장 표/그림/도식 힌트는 [api/app/services/draft_generation_taxonomy.py](/home/kdm_theimc/coding/RFP_copilot/api/app/services/draft_generation_taxonomy.py) 에 저장해 planner/designer/writer가 공통으로 사용한다.
- 다음 우선순위는 추출 근거 가시화와 검색 제어 고도화다.

## 3. 대상 사용자
- 로컬에서 혼자 제안서 초안을 만들고 싶은 사용자

## 4. 핵심 기능
- 프로젝트 CRUD(생성/조회/수정/삭제)
- 공고 RFP 멀티파일 업로드(role 지정, 요구사항정의서 포함 가능)/텍스트 추출/document chunk 저장/OpenAI section별 structured extraction/사업 개요 템플릿+요구사항 확정
- 내 자료 라이브러리(유형 지정 업로드) + 프로젝트 연결 + chunk 저장(PDF/TXT/MD/XLSX/CSV/TSV, PDF는 OCR fallback 지원)
- Outline Builder: 계층(depth) + 자동 번호(display label) + 제목 기반 목차 구조 저장
- Draft Workspace: 작성 의도 입력 + AI planner 기반 generation unit 계획/작성/공통 research API 기반 검색 파이프라인
- draft 편집기에서 선택 구간 기준 AI chat/apply 편집 루프
- draft 편집기에서 바로 다운로드(md/txt)
- 선택 영역 부분 수정 요청

## 5. 기술 스택
- Frontend: Next.js + TypeScript
- Backend: FastAPI (Python)
- DB: SQLite (DATABASE_URL로 Postgres 전환 가능)
- ORM/Migration: SQLAlchemy + Alembic
- 산출물 다운로드: Markdown / Text

## 6. 설치 및 실행 방법
### 6.1 요구사항
- Linux/WSL 환경
- Node.js 22.22+ (24.x 권장)
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
- OpenAI 키 입력 위치: `api/.env`의 `OPENAI_API_KEY=...`
- OpenAI 연결 확인: `GET /api/health/openai`
- 기본 OpenAI timeout은 `120초`이며, 필요 시 `OPENAI_TIMEOUT_SECONDS`로 조정한다
- 최신 웹 검색 researcher 모델은 `OPENAI_MODEL_RESEARCH`로 분리하며 기본값은 `gpt-5-mini`다
- `OCR_ENABLED=true`이면 PDF 텍스트 추출이 비어 있을 때 OpenAI OCR fallback을 시도한다

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
```bash
# backend syntax check
cd api
source .venv/bin/activate
python -m compileall app

# frontend type check
cd ../web
npm run typecheck

# frontend production build
npm run build
```

## 7. 폴더 구조 요약
- `api/`: FastAPI 백엔드
- `web/`: Next.js 프론트엔드
- `data/`: 업로드/산출물 로컬 저장
- `scripts/`: 실행 스크립트

## 8. 사용 방법
1. 프로젝트 목록 페이지에서 프로젝트를 생성하거나 이름을 수정한다.
2. 프로젝트의 `RFP` 탭에서 공고 파일을 대기 목록에 추가한 뒤 한 번에 업로드한다.
3. 업로드 완료 목록에서 필요한 파일을 체크하고, 별도로 요구사항 소스 파일과 페이지 범위를 지정한 뒤 추출한다. 요구사항만 별도 정리된 문서가 있으면 `요구사항정의서` 유형으로 올리는 편이 더 정확하다.
4. 자료 라이브러리에서 자료를 유형과 함께 업로드한다.
5. 프로젝트 상세 페이지에서 필요한 자료를 체크해 연결한다.
6. `Outline` 탭에서 상위/하위 구조와 제목을 정리하면 번호가 자동 계산된 목차를 저장한다.
7. `Draft` 탭에서 RFP/연결 자료/목차 상태를 검토한 뒤 초안을 생성한다.
8. 초안 편집기에서 본문을 저장하고, 선택 구간의 `AI EDIT` 칩을 통해 AI와 대화하며 수정 제안을 적용한다.
9. `Draft` 탭에서 `다운로드` 버튼을 눌러 `md` 또는 `txt`로 바로 내려받는다.
10. 선택 텍스트에 부분 수정 요청을 보내고, 제안문을 적용하거나 취소한다.

## 9. 문제 해결
- OpenAI 키 오류: `api/.env`의 `OPENAI_API_KEY` 확인
- OpenAI 상태 확인: `GET /api/health/openai`에서 모델 접근 여부 확인
- RFP 추출 실패: 스캔 PDF로 텍스트가 비어 있거나 OpenAI 호출이 timeout/실패했을 수 있음. 체크한 파일 수를 줄이거나 `OPENAI_TIMEOUT_SECONDS`를 늘려 다시 시도
- 긴 PDF 비용 문제: 현재는 whole PDF를 통째로 보내지 않고, 로컬 chunk 저장 후 관련 chunk만 추출/초안 생성에 사용
- 초안 생성 방식: 저장된 목차와 작성 의도를 기준으로 AI planner가 먼저 목차 역할과 outline 적합성을 해석하고, 이후 요구사항 배치별 section plan, generation unit, requirement coverage를 만든다. 목차가 부적절하면 coverage warning과 사용자 확인 흐름을 거친다. 각 generation unit은 planner가 만든 planned search intent를 먼저 실행하고, 이어서 unit 생성 직전 LLM이 adaptive search 필요 여부를 한 번 더 판단한다. `execution/strategy` unit은 모든 검색 결과가 모인 뒤 designer 단계가 실행 blueprint를 먼저 만들고, writer는 section이 아니라 generation unit 단위로 실행된다. writer는 `writing_mode`, `unit_pattern`, `required_aspects`, blueprint, 결합된 검색 결과를 받아 더 구체적인 실행안을 작성하며, 기본 출력은 `☐ / ○ / -` 개조식 Markdown이다. 필요 시 Markdown 표와 `<그림>`, `<도식>` placeholder도 본문에 직접 포함한다. planner/writer는 회사 자료 제목만이 아니라 실제 asset chunk 본문 일부도 내부 근거로 사용한다. 검색은 공통 `research` API가 OpenAI `Responses API + web_search`를 이용해 수행하고, 최신성 판단은 절대 날짜 기준으로 진행한다. 검색 intent는 사용자 입력 규칙이 아니라 백엔드 `research_playbooks.py` 가이드를 1차 참고자료로 삼아 LLM이 생성하며, 이 가이드에는 `unit_pattern`별 기본 planned search 여부, adaptive search 허용 조건, 우선 출처, 반드시 확보할 정보, 초안 표현 힌트가 포함된다. 검색 실행 로그와 결과 요약은 Draft 화면에서 확인할 수 있고, 같은 프로젝트에서 같은 날 같은 검색은 재사용한다
- 프롬프트 수정 위치: `api/app/services/prompts/`
- RFP 추출: `api/app/services/prompts/rfp.py`
- 초안 생성/AI 편집: `api/app/services/prompts/draft.py`
- 최신 검색: `api/app/services/prompts/search.py`
- 실제 prompt 입력값과 RFP chunk 확인: `web /projects/{id}/debug`, trace 파일은 `data/debug/project_<id>/prompt_traces/`
- chat/apply 적용 실패: 선택 문장이 이미 바뀌어 서버와 mismatch일 수 있음. 새 선택으로 다시 요청
- API 연결 실패: `web/.env.local`의 `NEXT_PUBLIC_API_BASE_URL` 확인
- 업로드 실패: `api/.env`의 `MAX_UPLOAD_MB`와 `data/uploads` 쓰기 권한 확인
- PDF 추출 실패: 스캔 PDF일 수 있음. `OCR_ENABLED`와 OpenAI 키를 확인하고 다시 시도
- 스캔 브로슈어 OCR 품질: OCR은 동작해도 원본 해상도와 모델 성능에 따라 문자가 깨질 수 있음
- XLSX/CSV 반영 문제: 파일을 다시 연결하거나 draft 재생성을 실행하면 기존 바이너리성 chunk를 감지해 자동 재생성한다
- 목차가 비어 있음: `Outline` 탭에서 섹션을 추가하고 저장해야 `Draft`에서 초안을 생성할 수 있음

## 10. 참고/링크
- 부트스트랩 설계: `planning_document.md`
