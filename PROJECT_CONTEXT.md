# PROJECT_CONTEXT — RFP Copilot
## 1. 한 줄 요약
공고/RFP와 회사 자료를 업로드하고, OpenAI 기반 추출과 문서 기반 초안 생성을 거쳐, 사용자와 AI가 함께 초안을 다듬은 뒤 다운로드하는 로컬 웹앱.

## 2. MVP 목표
- [x] 공고문/RFP와 회사 자료를 프로젝트에 업로드하고 관리한다
- [x] 공고 파일을 복수 업로드하고 파일 역할을 지정할 수 있다
- [x] OpenAI API로 공고/RFP에서 `사업 개요 템플릿 / 요구사항`을 추출하고 사용자가 확정한다
- [x] 추출된 RFP 정보와 업로드 문서를 바탕으로 초안을 생성한다
- [x] 사용자가 초안을 보면서 AI와 왕복 편집 대화를 통해 수정/반영한다
- [x] 사용자가 초안을 다운로드해 최종 제안서를 수동 마감할 수 있다

## 3. 현재 결정된 사항(Decision Log)
1) 단일 사용자 로컬 실행(MVP)으로 시작한다.
2) 자료(회사소개/제품/실적/인력/특허/재무/레퍼런스)는 자동 태깅/분해하지 않고 업로드 시 사용자가 유형을 지정한다.
3) DB는 SQLite로 시작하되, DATABASE_URL 기반으로 Postgres 전환이 가능하도록 ORM+마이그레이션을 적용한다.
4) 초안 편집은 Markdown/Text 중심이며, HWP 최종 양식은 사람이 마무리한다.
5) 공고/RFP 추출은 규칙기반보다 OpenAI API 기반 정확도를 우선한다.
6) 업로드한 회사 자료는 retrieval context로 사용하며, 초기 구현은 경량 RAG로 시작한다.
7) 핵심 UX는 "초안 생성 1회"보다 "초안 생성 후 AI와 대화하며 반복 수정"에 둔다.
8) Export는 미리보기 화면을 기본으로 두고, 거기서 수정/다운로드로 분기한다.
9) 평가항목 매핑은 차별점이지만, 현재는 핵심 작성 루프가 먼저다.
10) OpenAI API 키는 `api/.env`의 `OPENAI_API_KEY`로만 받는다.
11) outline은 구조 정의 전용으로 두고, 계층은 `depth/title`로 입력받으며 `display_label`은 자동 번호로 저장한다.
12) RFP 원문 전체 PDF를 통째로 모델에 넣지 않고, 로컬 chunk 저장 후 관련 chunk만 추출/생성 프롬프트에 넣는다.
13) retrieval 저장소는 우선 SQLite 메타데이터 + 로컬 file chunk로 시작한다.
14) RFP 검토 화면의 canonical schema는 `사업 개요 템플릿 / 요구사항`으로 둔다.
15) 공고 파일은 업로드 시 자동 추출하지 않고, 사용자가 업로드된 파일 중 필요한 파일을 체크해 추출을 눌렀을 때만 OpenAI 호출을 수행한다.
16) RFP 추출 프롬프트는 섹션별로 분리하고, 수정 위치는 `api/app/services/rfp_prompts.py`로 고정한다.
17) 초안 생성 제어는 outline이 아니라 draft preparation 영역에서 수행한다.
18) 검색 대상 섹션 선택과 source pinning은 outline이 아니라 draft generation 단계에서 다룬다.
19) 초안 생성은 whole-document 1회 호출이 아니라 `draft plan -> section별 source pinning -> section별 LLM generation`으로 수행한다.

## 4. 현재 상태 요약
- 상태: `.env` 기반 OpenAI 설정 로딩, 멀티파일 RFP 대기 목록 업로드/role 지정, 체크한 파일만 section별 prompt로 `사업 개요 템플릿 / 요구사항` 추출, outline 구조 저장(depth/title + 자동 번호), draft preparation에서 section별 추천 요구사항/근거 확인 및 include/exclude 후 section별 AI 초안 생성, draft chat/apply 편집 루프까지 연결됨. 초기 MVP는 완료
- 우선순위: 1) RFP 추출 근거/evidence 가시화 2) draft preparation의 검색 대상 선택 추가 3) 매핑/서식 고도화

## 5. 다음 작업(Next Actions)
1) draft workspace에서 근거 삭제(너무 오래 걸리고 버벅거림. 또는 아주 간소화 하기)
2) draft workspace 전체적으로 기능 다시 확인
3) RFP 추출 결과별로 사용된 chunk 근거를 보여주고, 파일/근거를 수동 포함·제외할 수 있게 한다
4) Draft preparation에서 검색 대상 섹션 선택과 외부 검색 연결 방식을 추가한다
5) 평가항목 매핑과 export 서식 고도화를 재개한다

## 6. 중요한 제약/주의사항
- 공고 PDF는 텍스트/스캔 혼재: OCR은 옵션이며 기본은 텍스트 추출 우선
- 업로드 파일 크기 제한 및 경로 sanitize 필수
- OpenAI API 키는 .env로만 관리한다
- OpenAI 추출/생성은 관련 chunk만 사용하고 whole-document prompt는 피한다
- 기본 OpenAI request timeout은 120초이며, RFP section 추출은 timeout 1회 재시도를 사용한다
- 시스템 표기는 사용자 텍스트와 혼동되지 않게 UI/텍스트 모두에서 구분해야 한다
- 계획 문서는 Node.js 24.x를 권장하지만, 현재 스캐폴딩은 Node.js 22.22+에서도 동작하도록 구성한다
- 현재 RFP 업로드는 PDF 외에 `.txt`/`.md`도 로컬 부트스트랩 검증용으로 허용한다
- OpenAI 상태 확인은 `/api/health/openai`에서 수행한다

## 7. 미결 사항(Open Questions)
- 로컬 chunk retrieval에 embeddings를 추가할지, 현재 lexical scoring을 한동안 유지할지 결정 필요
