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
8) 다운로드는 별도 export 페이지가 아니라 draft 편집기 안에서 바로 수행한다.
9) 평가항목 추출 데이터는 유지하되, 별도 매핑 기능/페이지는 현재 범위에서 제거한다.
10) OpenAI API 키는 `api/.env`의 `OPENAI_API_KEY`로만 받는다.
11) outline은 구조 정의 전용으로 두고, 계층은 `depth/title`로 입력받으며 `display_label`은 자동 번호로 저장한다.
12) RFP 원문 전체 PDF를 통째로 모델에 넣지 않고, 로컬 chunk 저장 후 관련 chunk만 추출/생성 프롬프트에 넣는다. 요구사항 추출은 generic chunk를 그대로 저장하되, 추출 직전에 요구사항 후보 단위로 다시 분해해 배치 처리한다.
13) retrieval 저장소는 우선 SQLite 메타데이터 + 로컬 file chunk로 시작한다.
14) RFP 검토 화면의 canonical schema는 `사업 개요 템플릿 / 요구사항`으로 둔다.
15) 공고 파일은 업로드 시 자동 추출하지 않고, 사용자가 업로드된 파일 중 필요한 파일을 체크해 추출을 눌렀을 때만 OpenAI 호출을 수행한다.
16) LLM 프롬프트는 `api/app/services/prompts/` 아래 기능별 파일에 모아 직접 수정하기 쉽게 유지한다.
17) 초안 생성 제어는 outline이 아니라 draft preparation 영역에서 수행한다.
18) 검색 출처 표기는 검색 기능에서만 다루고, 현재 draft generation 화면에는 노출하지 않는다.
19) 초안 생성은 `작성 의도`를 입력받는 AI planner가 먼저 outline 역할을 해석하고, 이후 요구사항 배치별 `generation unit`과 requirement coverage를 설계하는 2단계 파이프라인으로 수행한다. `execution/strategy` unit은 writer 전에 별도 designer 단계가 구조화된 실행 blueprints를 만들고, writer는 그 blueprint를 바탕으로 본문을 생성한다. 목차가 부적절하면 coverage warning을 만들고 사용자 확인 후 생성한다.
20) `[확인 필요(시스템)]` 표기는 현재 별도 패널로 노출하지 않으며, draft 본문에서도 제거한다. 초안은 가능한 한 본문 완결형으로 생성한다.
21) 요구사항 추출은 사용자가 업로드 파일 중 요구사항 소스 파일과 페이지 범위를 명시해야 하며, 현재 그 설정은 `rfp_extractions.source_file_path` 텍스트 필드에 JSON으로 저장한다.
22) 회사 자료는 PDF/TXT/MD 외에 XLSX/CSV/TSV도 chunk로 파싱하고, PDF 텍스트가 비어 있으면 OpenAI OCR fallback을 시도한다.
23) draft planner/writer는 회사 자료 제목만이 아니라 실제 chunk 본문 일부를 내부 근거로 사용하며, 회사 소개/특허/실적류 섹션에서는 내부 자료가 있으면 일반 외부 검색을 줄인다.
24) draft generation unit 분류 기준과 `execution` 세부 패턴, 권장 표/그림/도식 힌트는 `api/app/services/draft_generation_taxonomy.py`에 중앙 정의하고, planner/designer/writer가 공통으로 참조한다.
25) draft writer는 기본적으로 `☐ / ○ / -` 기호 체계의 개조식 Markdown을 사용하며, 필요 시 Markdown 표와 `<그림>`, `<도식>` placeholder를 본문에 직접 포함한다.
26) 외부 검색은 파트 전용 하드코딩 규칙 대신 공통 `research` API를 사용한다. planner가 planned search intent를 만들고, unit 생성 직전 LLM이 adaptive search 필요 여부를 한 번 더 판단한다. 검색 관점 설명서는 `api/app/services/research_playbooks.py`에 저장하지만, 실제 query/purpose 생성은 LLM이 담당한다.
27) 외부 검색은 사용자 입력 규칙이 아니라 백엔드의 `research_playbooks.py` 가이드를 1차 참고자료로 삼아 planner와 adaptive search 단계의 LLM이 판단한다. 이 가이드는 `unit_pattern`별 기본 planned search 여부, adaptive search 허용 조건, 우선 출처, 반드시 뽑을 정보, 초안 표현 힌트까지 포함한다. draft의 검색 실행 로그는 `draft_search_tasks`에 저장하고, 같은 프로젝트에서 같은 날 같은 query/purpose/allowed_domains 조합이면 재검색 대신 기존 결과를 재사용한다.

## 4. 현재 상태 요약
- 상태: `.env` 기반 OpenAI 설정 로딩, 멀티파일 RFP 대기 목록 업로드/role 지정, 파일 선택 즉시 업로드 대기 목록 반영, 체크한 파일만 section별 prompt로 `사업 개요 템플릿 / 요구사항` 추출, outline 구조 저장(depth/title + 자동 번호), draft generation은 `작성 의도 -> AI planner overview -> 요구사항 배치 planner -> generation unit planned search -> adaptive search 판단 -> generation unit designer/writer` 흐름으로 수행됨. 요구사항 추출은 사용자가 지정한 소스 파일과 페이지 범위만 대상으로 generic chunk를 후보 단위로 다시 분해하고 배치별 OpenAI structured extraction으로 합친다. 회사 자료는 PDF/TXT/MD/XLSX/CSV/TSV를 chunk로 저장하고, PDF 텍스트가 비어 있으면 OCR fallback을 시도한다. draft planner/writer는 회사 자료 제목뿐 아니라 실제 asset chunk 본문 일부를 내부 근거로 사용하며, planner는 requirement coverage matrix로 모든 요구사항이 최소 1회 이상 primary generation unit에 배정되도록 보정한다. 목차가 요구사항 커버에 부적절하면 coverage warning과 사용자 확인 흐름을 거친다. `execution/strategy` unit은 writer 전에 구조화 blueprint를 만들고, writer는 `☐ / ○ / -` 개조식과 Markdown 표, `<그림>`, `<도식>` placeholder를 포함한 초안을 생성한다. 최신 검색은 공통 `research` API를 통해 OpenAI `Responses API + web_search`에 절대 날짜를 명시하는 방식으로 수행되며, planner의 planned search와 unit별 adaptive search 결과를 결합해 writer 입력으로 넣는다. 검색 intent는 사용자 입력이 아니라 백엔드 `research_playbooks.py`를 1차 가이드로 삼아 LLM이 생성한다. draft의 검색 실행 로그와 요약 결과는 `draft_search_tasks`에 저장되고, 같은 프로젝트에서 당일 동일 query는 재사용된다. Draft 화면에서는 검색 내역 모달로 planned/adaptive 결과를 검토할 수 있다.
- 우선순위: 1) search result / coverage 가시화 2) draft workspace의 생성/편집 UX 안정화 3) export 서식 고도화

## 5. 다음 작업(Next Actions)
1) draft 화면이나 debug에서 planned/adaptive search 결과를 어디까지 노출할지 결정
2) search playbook과 planner/designer 검색 품질을 더 다듬기
3) AI 편집(chat)도 section plan/search context를 더 활용할지 검토
4) export 서식 고도화와 최종 산출물 템플릿 정리를 진행한다

## 6. 중요한 제약/주의사항
- 공고 PDF와 회사 자료 PDF는 텍스트/스캔 혼재: 텍스트 추출 우선, 비어 있을 때만 OCR fallback을 시도한다
- OCR 품질은 원본 PDF 해상도/내장 이미지 품질/모델 성능에 크게 좌우되며, 특히 스캔 브로슈어형 PDF에서는 잡음이 남을 수 있다
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
