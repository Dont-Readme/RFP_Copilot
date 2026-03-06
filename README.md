# RFP Copilot
## 1. 한 줄 요약
공고 파일과 회사 자료를 바탕으로 RFP를 구조화하고, 제안서 초안을 만들고, AI와 대화하며 수정한 뒤 산출물을 내보내는 로컬 웹앱.

## 2. 프로젝트 목적
- 공고 요구사항/평가항목을 구조화해 제안서 작성 시간을 줄인다.
- 평가항목-문단 매핑 검증으로 빠진 항목을 사전에 차단한다.

## 2.1 현재 방향 메모
- 핵심 작성 루프는 `멀티파일 업로드 -> chunk 저장 -> OpenAI 3섹션 추출 -> retrieval 기반 초안 생성 -> AI와 대화형 수정 -> 다운로드`다.
- 현재 레포는 이 초기 MVP 루프를 끝까지 연결했고, 다음 우선순위는 추출 근거 가시화와 생성 제어 고도화다.
- 평가항목 매핑은 유지하되, 우선순위는 핵심 작성 루프 다음이다.

## 3. 대상 사용자
- 로컬에서 혼자 제안서 초안을 만들고 싶은 사용자

## 4. 핵심 기능
- 프로젝트 CRUD(생성/조회/수정/삭제)
- 공고 RFP 멀티파일 업로드(role 지정)/텍스트 추출/document chunk 저장/OpenAI section별 structured extraction/평가항목 확정
- 내 자료 라이브러리(유형 지정 업로드) + 프로젝트 연결 + chunk 저장
- Outline CRUD + `needs_search` 저장 + 로컬 chunk retrieval 기반 citation 검색
- 추출된 RFP + 업로드 문서 retrieval을 쓰는 OpenAI 초안 생성 + "확인 필요(시스템)" 표기/질문 리스트
- draft 편집기에서 선택 구간 기준 AI chat/apply 편집 루프
- 평가항목 매핑 검증(누락 경고 + 강화 제안)
- Export 미리보기 → 수정/다운로드(md/txt/docx/xlsx)
- 선택 영역 부분 수정 요청

## 5. 기술 스택
- Frontend: Next.js + TypeScript
- Backend: FastAPI (Python)
- DB: SQLite (DATABASE_URL로 Postgres 전환 가능)
- ORM/Migration: SQLAlchemy + Alembic
- 문서 생성: python-docx, openpyxl

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
2. 프로젝트의 `RFP` 탭에서 공고 파일을 업로드하고, OpenAI로 추출된 요구사항/평가항목을 검토 후 확정한다.
3. 필요하면 같은 화면에서 전체 업로드 파일 기준으로 다시 추출한다.
4. 자료 라이브러리에서 자료를 유형과 함께 업로드한다.
5. 프로젝트 상세 페이지에서 필요한 자료를 체크해 연결한다.
6. `Outline` 탭에서 목차를 저장하고, `검색 필요` 섹션에 대해 chunk retrieval 기반 citation 검색을 실행한다.
7. 같은 화면에서 추출된 RFP + 연결 자료 chunk를 근거로 OpenAI 초안을 재생성한다.
8. 초안 편집기에서 본문을 저장하고, 선택 구간을 기준으로 AI와 대화하며 수정 제안을 적용한다.
9. `Mapping` 탭에서 평가항목 매핑을 실행해 누락/약함 경고를 확인한다.
10. `Export` 탭에서 산출물을 생성하고 미리보기/다운로드한다.
11. 선택 텍스트에 부분 수정 요청을 보내고, 제안문을 적용하거나 취소한다.

## 9. 문제 해결
- OpenAI 키 오류: `api/.env`의 `OPENAI_API_KEY` 확인
- OpenAI 상태 확인: `GET /api/health/openai`에서 모델 접근 여부 확인
- RFP 추출 실패: 스캔 PDF로 텍스트가 비어 있거나 OpenAI 호출이 실패했을 수 있음. `RFP` 탭의 재추출 또는 OCR 경로 확인
- 긴 PDF 비용 문제: 현재는 whole PDF를 통째로 보내지 않고, 로컬 chunk 저장 후 관련 chunk만 추출/초안 생성에 사용
- 프롬프트 수정 위치: `api/app/services/rfp_prompts.py`
- chat/apply 적용 실패: 선택 문장이 이미 바뀌어 서버와 mismatch일 수 있음. 새 선택으로 다시 요청
- API 연결 실패: `web/.env.local`의 `NEXT_PUBLIC_API_BASE_URL` 확인
- 업로드 실패: `api/.env`의 `MAX_UPLOAD_MB`와 `data/uploads` 쓰기 권한 확인
- PDF 추출 실패: 스캔 PDF일 수 있음(OCR 옵션 사용)
- 검색 결과가 비어 있음: 현재 검색은 외부 웹이 아니라 저장된 RFP/연결 자료 chunk만 대상으로 함

## 10. 참고/링크
- 부트스트랩 설계: `planning_document.md`
