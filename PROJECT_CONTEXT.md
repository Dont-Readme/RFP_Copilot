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
12) RFP 원문 전체 PDF를 통째로 모델에 넣지 않고, 로컬 chunk 저장 후 관련 chunk만 추출/생성 프롬프트에 넣는다.
13) retrieval 저장소는 우선 SQLite 메타데이터 + 로컬 file chunk로 시작한다.
14) RFP 검토 화면의 canonical schema는 `사업 개요 템플릿 / 요구사항`으로 둔다.
15) 공고 파일은 업로드 시 자동 추출하지 않고, 사용자가 업로드된 파일 중 필요한 파일을 체크해 추출을 눌렀을 때만 OpenAI 호출을 수행한다.
16) RFP 추출 프롬프트는 섹션별로 분리하고, 수정 위치는 `api/app/services/rfp_prompts.py`로 고정한다.
17) 초안 생성 제어는 outline이 아니라 draft preparation 영역에서 수행한다.
18) 검색 출처 표기는 검색 기능에서만 다루고, 현재 draft generation 화면에는 노출하지 않는다.
19) 초안 생성은 planner(A) -> writer(B) -> researcher(C) -> reviewer(D) 순서의 섹션 파이프라인으로 수행하고, 최신 검색은 OpenAI `Responses API + web_search`에 절대 날짜를 명시하는 방식으로 수행한다.
20) `[확인 필요(시스템)]`는 draft 본문에 직접 쓰지 않고, `작성 확인 사항` 패널에 목차 라벨과 함께 별도 저장/표시한다.

## 4. 현재 상태 요약
- 상태: `.env` 기반 OpenAI 설정 로딩, 멀티파일 RFP 대기 목록 업로드/role 지정, 체크한 파일만 section별 prompt로 `사업 개요 템플릿 / 요구사항` 추출, outline 구조 저장(depth/title + 자동 번호), draft generation은 planner/writer/researcher/reviewer 섹션 파이프라인으로 수행됨. 최신 검색은 OpenAI `Responses API + web_search`에 절대 날짜를 명시하는 방식으로 수행되고, 검토 결과는 `작성 확인 사항` 패널에 목차와 함께 표시한다. draft chat/apply 편집 루프와 draft 내 다운로드까지 연결됨.
- 우선순위: 1) planner/researcher 결과 가시화 2) draft workspace의 생성/편집 UX 안정화 3) export 서식 고도화

## 5. 다음 작업(Next Actions)
1) section plan, search task, search result를 draft 화면에 얼마나 노출할지 결정
2) researcher(C)의 외부 검색 품질과 provider 범위를 다듬기
3) AI 편집(chat)도 section plan/search context를 더 활용할지 검토
4) export 서식 고도화와 최종 산출물 템플릿 정리를 진행한다

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
