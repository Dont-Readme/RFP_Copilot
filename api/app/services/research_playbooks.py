from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ResearchPlaybook:
    pattern_key: str
    label_ko: str
    description_ko: str
    default_planned_search: str
    adaptive_search_allowed: bool = False
    adaptive_conditions: tuple[str, ...] = ()
    preferred_sources: tuple[str, ...] = ()
    must_capture: tuple[str, ...] = ()
    avoid_search_for: tuple[str, ...] = ()
    draft_expression: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()


RESEARCH_PLAYBOOKS: tuple[ResearchPlaybook, ...] = (
    ResearchPlaybook(
        pattern_key="policy_background",
        label_ko="정책·환경 배경형 검색 가이드",
        description_ko="정책, 시장, 행정 환경, 사업 추진 배경을 설명할 때 사용하는 검색 가이드입니다.",
        default_planned_search="always",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "planned search 결과만으로 정책/시장 연결이 약할 때",
            "국내외 시장/기업 현황이 더 필요할 때",
        ),
        preferred_sources=("정부부처", "지자체", "공공기관", "언론", "공공/산업 보고서"),
        must_capture=(
            "최신 정부 정책명",
            "현재 실제 추진 중인 정책인지 여부",
            "정책 핵심 방향",
            "국내외 시장 규모 통계",
            "국내외 기업 현황",
            "시장 변화/성장 방향",
        ),
        avoid_search_for=("회사 내부 강점 설명을 외부 검색으로 대체하는 것",),
        draft_expression=(
            "정책은 간략 표와 짧은 설명 문단으로 정리",
            "시장 현황은 문단 위주로 작성",
            "시장 규모와 기업 현황은 표 병행",
        ),
        notes=(
            "아이템과 정책 연결이 핵심",
            "너무 일반적인 산업 소개로 흐르지 않게 주의",
        ),
    ),
    ResearchPlaybook(
        pattern_key="business_need",
        label_ko="사업 필요성형 검색 가이드",
        description_ko="문제 정의, 추진 필요성, 개선 목표를 설명할 때 사용하는 검색 가이드입니다.",
        default_planned_search="always",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "문제 상황을 입증할 통계가 부족할 때",
            "지역/산업별 필요성 근거가 더 필요할 때",
        ),
        preferred_sources=("KOSIS", "정부부처", "공공연구기관", "산업 보고서", "언론"),
        must_capture=(
            "현행 문제와 사업 필요성 연결 근거",
            "생산성/운영 비효율 관련 통계",
            "고령화/청년 유출/지역 소멸 등 문제 근거",
        ),
        avoid_search_for=("policy_background와 동일한 시장 규모 설명을 반복하는 것",),
        draft_expression=(
            "문제 현황은 문단으로 정리",
            "필요성 근거 통계는 표로 정리",
            "문제 -> 필요성 -> 사업 연결 구조 유지",
        ),
        notes=(
            "policy_background는 환경/정책/시장 중심",
            "business_need는 왜 지금 해야 하는가 중심",
        ),
    ),
    ResearchPlaybook(
        pattern_key="delivery_method",
        label_ko="수행 방법론형 검색 가이드",
        description_ko="애자일, 단계적 구축, 시범 적용 후 확산 같은 수행 전략 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "특정 방법론을 공공사업 맥락에서 정당화할 최신 사례가 필요할 때",
            "단계적 구축/실증 후 확산 사례를 보강해야 할 때",
        ),
        preferred_sources=("정부부처", "공공기관", "연구기관"),
        must_capture=("유사 사업 추진 방식 사례", "단계적 구축 또는 확산 방식 사례"),
        avoid_search_for=("일반적인 방법론 소개만 반복하는 검색",),
        draft_expression=("문단 위주 작성", "필요 시 단계별 추진 표와 도식 병행"),
        notes=("기본은 내부 논리로 쓰고, 필요 시만 adaptive search",),
    ),
    ResearchPlaybook(
        pattern_key="governance_collaboration",
        label_ko="거버넌스·협업형 검색 가이드",
        description_ko="컨소시엄, 전문가 자문, PMO, 의사결정 구조, 협업 체계 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        notes=("검색 없이 내부 제안 논리 우선",),
    ),
    ResearchPlaybook(
        pattern_key="schedule_risk",
        label_ko="일정·리스크 관리형 검색 가이드",
        description_ko="일정, 마일스톤, 리스크 대응, 형상/문서 관리 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        notes=("제안서 내부 계획이 더 중요",),
    ),
    ResearchPlaybook(
        pattern_key="system_configuration",
        label_ko="시스템 장비구성형 검색 가이드",
        description_ko="하드웨어, 소프트웨어, 네트워크, 개발·운영 환경 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        preferred_sources=("내부 자료", "RFP 요구 스펙"),
        must_capture=("현재 회사 보유 환경", "기관이 요구한 장비/스펙"),
        avoid_search_for=("외부 일반 장비 소개",),
        draft_expression=("시스템 구성 표", "구성도 도식"),
        notes=("외부 검색보다 요구사항/RFP/회사자료 반영이 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="functional_workflow",
        label_ko="기능·업무 흐름형 검색 가이드",
        description_ko="기능 요구, 서비스 흐름, 화면/업무 프로세스 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        preferred_sources=("내부 설계", "요구사항"),
        avoid_search_for=("일반 서비스 기능 사례",),
        draft_expression=("기능 정의 표", "업무 흐름 도식"),
        notes=("검색보다 요구사항 반영이 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="data_pipeline",
        label_ko="데이터 구축·연계형 검색 가이드",
        description_ko="데이터 수집, 연계, 변환, 전처리, 표준화, 적재 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "요구사항에 외부 데이터 연계가 있을 때",
            "공공데이터 활용이 핵심일 때",
            "실제 데이터 수집원 발굴이 필요할 때",
        ),
        preferred_sources=("공공데이터포털", "정부부처", "KOSIS", "표준기관"),
        must_capture=(
            "실제 활용 가능한 데이터 출처",
            "제공 항목",
            "갱신 주기",
            "연계 방식 힌트",
            "표준 분류/코드 체계",
        ),
        avoid_search_for=("이미 내부 데이터 정의가 확정된 부분",),
        draft_expression=(
            "데이터 항목 정의 표",
            "수집원/연계 방식/전처리/저장 구조 표",
            "데이터 흐름 도식",
        ),
        notes=(
            "기본은 검색 없음",
            "외부 데이터가 핵심인 사업에서만 adaptive search 적극 활용",
        ),
    ),
    ResearchPlaybook(
        pattern_key="interface_ux",
        label_ko="인터페이스·사용자 경험형 검색 가이드",
        description_ko="외부 시스템 연계, UI/UX, 프로토콜, 정보교환 방식 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("특정 인터페이스 표준/가이드라인이 필요한 경우",),
        preferred_sources=("표준기관", "공공 가이드"),
        must_capture=("연계 표준", "UX 가이드"),
        avoid_search_for=("일반 UI 사례 나열",),
        draft_expression=("인터페이스 정의 표", "연계 흐름 도식"),
        notes=("기본은 요구사항 기반 작성",),
    ),
    ResearchPlaybook(
        pattern_key="performance_capacity",
        label_ko="성능·용량형 검색 가이드",
        description_ko="응답시간, 처리량, 가용성, 확장성 설명에 대한 검색 가이드입니다.",
        default_planned_search="always",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "planned search만으로 최신 성능 기준이 부족할 때",
            "목표 기술의 최신 벤치마크가 더 필요할 때",
        ),
        preferred_sources=("논문", "학회/전문기관", "기술 보고서"),
        must_capture=("개발 목표와 관련된 최신 성능 수준", "비교 가능한 벤치마크", "성능 지표 정의"),
        avoid_search_for=("너무 일반적인 고성능 필요 수준의 자료",),
        draft_expression=("성능 비교 표 중심", "필요 시 성능 목표/검증 기준 표"),
        notes=("최신성 중요", "숫자와 기준 중심"),
    ),
    ResearchPlaybook(
        pattern_key="analytics_ai",
        label_ko="분석·AI 활용형 검색 가이드",
        description_ko="분석 로직, 예측, 추천, 모델 적용과 결과 활용 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "특정 기술 선택의 정당화가 필요할 때",
            "최신 벤치마크/적용 사례가 필요할 때",
        ),
        preferred_sources=("논문", "연구기관", "산업협회"),
        must_capture=("기술 적용 사례", "벤치마크", "활용 효과 근거"),
        avoid_search_for=("일반적인 AI 트렌드 소개",),
        draft_expression=("분석 대상/입력/결과 활용 표", "분석 흐름 도식"),
        notes=("일반론이 많아질 위험이 있어 검색은 엄격히 제한",),
    ),
    ResearchPlaybook(
        pattern_key="testing_validation",
        label_ko="테스트·검증형 검색 가이드",
        description_ko="단위/통합/시스템/성능 테스트, BMT, 적합성 검증 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("특정 검증 표준이나 지침이 필요한 경우",),
        preferred_sources=("공공 가이드", "표준기관"),
        must_capture=("테스트 기준", "검증 절차"),
        avoid_search_for=("일반 테스트 원칙 나열",),
        draft_expression=("테스트 유형·절차 표",),
        notes=("기본은 요구사항과 사업 내용 기반 작성",),
    ),
    ResearchPlaybook(
        pattern_key="security_privacy",
        label_ko="보안·개인정보형 검색 가이드",
        description_ko="접근통제, 저장보안, 통신보안, 로그, 개인정보보호 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "의료/교육/공공행정/위치정보 등 도메인 특화 규제가 걸릴 때",
            "최신 개인정보보호 기준 확인이 필요할 때",
        ),
        preferred_sources=("정부부처", "보안기관", "공공 가이드"),
        must_capture=("최신 보안 가이드", "개인정보 보호 기준"),
        avoid_search_for=("일반적인 보안 상식 나열",),
        draft_expression=("보안 통제 표", "접근통제/로그관리 구조 문단"),
        notes=("기본은 내부 설계", "특수 규제 도메인일 때 adaptive search 권장"),
    ),
    ResearchPlaybook(
        pattern_key="quality_management",
        label_ko="품질 관리형 검색 가이드",
        description_ko="품질 목표, 품질 항목, 점검 체계 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("특정 품질 기준 인용이 필요한 경우",),
        preferred_sources=("표준기관", "공공 가이드"),
        must_capture=("품질 항목", "점검 기준"),
        avoid_search_for=("일반 품질 개념 나열",),
        draft_expression=("품질 목표/관리 항목 표",),
        notes=("기본은 내부 수행 방안이 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="constraints_compliance",
        label_ko="제약·준수형 검색 가이드",
        description_ko="법, 제도, 표준, 규정, 준수사항 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=(
            "요구사항에 법/표준/규정/지침이 직접 언급될 때",
            "최신 제도 확인이 필요할 때",
        ),
        preferred_sources=("정부부처", "법령정보", "표준기관"),
        must_capture=("관련 법/제도/표준", "최신 준수 포인트"),
        avoid_search_for=("법령과 무관한 일반 설명",),
        draft_expression=("준수사항 표", "제약조건 설명 문단"),
        notes=("기본은 OFF지만 필요 시 검색 가치가 큼",),
    ),
    ResearchPlaybook(
        pattern_key="project_management_execution",
        label_ko="프로젝트 관리 실행형 검색 가이드",
        description_ko="사업관리, 투입인력, 진도, 성과물, 형상관리 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        notes=("기본은 내부 관리체계 중심",),
    ),
    ResearchPlaybook(
        pattern_key="operations_support_transition",
        label_ko="운영 지원·안정화형 검색 가이드",
        description_ko="안정화, 운영지원, 교육, 기술지원, 유지관리 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        notes=("기본은 사업 내용에 맞는 운영 계획이 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="transition_acceptance",
        label_ko="이행·검수·인수형 검색 가이드",
        description_ko="산출물, 검수, 인수인계, 완료 기준 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("특별한 검수 기준이 요구될 때만",),
        preferred_sources=("요구사항", "내부 수행계획"),
        must_capture=("과업별 산출물", "검수 기준", "인수 절차"),
        avoid_search_for=("일반적인 인수 문구",),
        draft_expression=("산출물 표", "검수/인수 절차 표"),
        notes=("사업 내용에 쓴 과업별 산출물이 잘 연결되는 게 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="consulting_methodology",
        label_ko="컨설팅 수행형 검색 가이드",
        description_ko="컨설팅 방법론, 세부 활동, 진단/분석, 산출물 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("특정 컨설팅 프레임워크 인용이 필요할 때",),
        preferred_sources=("공공 가이드", "연구기관"),
        must_capture=("수행 프레임워크",),
        avoid_search_for=("일반 컨설팅 방법론 소개",),
        draft_expression=("활동별 표", "수행 흐름 도식"),
        notes=("기본은 내부 방법론이 중요",),
    ),
    ResearchPlaybook(
        pattern_key="capability_evidence",
        label_ko="회사 역량 근거형 검색 가이드",
        description_ko="회사 소개, 수행 역량, 조직, 인력, 유사 실적 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        preferred_sources=("사용자가 첨부한 회사 자료",),
        must_capture=("회사 소개", "수행 역량", "전담 조직/인력", "유사 실적"),
        avoid_search_for=("외부 검색으로 회사 정보 대체",),
        draft_expression=("역량/실적 표", "근거 문단"),
        notes=("내부 자료가 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="patent_ip_evidence",
        label_ko="특허·지식재산 근거형 검색 가이드",
        description_ko="특허, 인증, 저작권, 지재권, 보유 기술 설명에 대한 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=False,
        preferred_sources=("사용자가 첨부한 특허/인증 자료",),
        must_capture=("보유 특허", "인증", "지식재산", "기술적 강점"),
        draft_expression=("특허/인증 표", "기술 강점 문단"),
        notes=("내부 자료가 핵심",),
    ),
    ResearchPlaybook(
        pattern_key="evaluation_response",
        label_ko="평가항목 대응형 검색 가이드",
        description_ko="평가항목 대응 논리를 강화해야 할 때 참고하는 보조 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("평가항목 대응 논리를 보강할 정책/사례/정량 근거가 필요할 때",),
        preferred_sources=("정부부처", "공공기관", "유관 협회"),
        must_capture=("평가 관점과 연결되는 정책/가이드", "유사 사업 추진 사례", "정량 근거"),
        avoid_search_for=("평가항목 자체를 외부 자료로 대체하는 것",),
        draft_expression=("평가 대응 비교 표",),
    ),
    ResearchPlaybook(
        pattern_key="implementation_case",
        label_ko="유사 구축 사례형 검색 가이드",
        description_ko="실행안이나 추진 전략을 구체화할 외부 사례가 필요할 때 참고하는 보조 검색 가이드입니다.",
        default_planned_search="none",
        adaptive_search_allowed=True,
        adaptive_conditions=("실행안이나 추진 전략을 구체화할 외부 사례가 꼭 필요할 때",),
        preferred_sources=("정부부처", "공공기관", "연구기관"),
        must_capture=("유사 공공 구축 사례", "단계별 추진 결과", "운영 전환 사례"),
        draft_expression=("사례 비교 표", "단계별 흐름 도식"),
    ),
)

PLAYBOOK_BY_KEY = {item.pattern_key: item for item in RESEARCH_PLAYBOOKS}

UNIT_PATTERN_PLAYBOOK_MAP: dict[str, tuple[str, ...]] = {
    "policy_background": ("policy_background",),
    "business_need": ("business_need",),
    "delivery_method": ("delivery_method",),
    "governance_collaboration": ("governance_collaboration",),
    "schedule_risk": ("schedule_risk",),
    "system_configuration": ("system_configuration",),
    "functional_workflow": ("functional_workflow",),
    "data_pipeline": ("data_pipeline",),
    "interface_ux": ("interface_ux",),
    "performance_capacity": ("performance_capacity",),
    "analytics_ai": ("analytics_ai",),
    "testing_validation": ("testing_validation",),
    "security_privacy": ("security_privacy",),
    "quality_management": ("quality_management",),
    "constraints_compliance": ("constraints_compliance",),
    "project_management_execution": ("project_management_execution",),
    "operations_support_transition": ("operations_support_transition",),
    "transition_acceptance": ("transition_acceptance",),
    "consulting_methodology": ("consulting_methodology",),
    "capability_evidence": ("capability_evidence",),
    "patent_ip_evidence": ("patent_ip_evidence",),
}

HEADING_PLAYBOOK_HINTS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("배경", "정책", "환경", "시장", "동향", "여건"), ("policy_background", "business_need")),
    (("필요성", "문제", "효과", "목적"), ("business_need",)),
    (("평가", "평가항목"), ("evaluation_response",)),
    (("전략", "방법론", "추진방안", "수행방안"), ("delivery_method", "implementation_case")),
    (("거버넌스", "협업", "컨소시엄", "자문", "조직", "인력", "수행체계"), ("governance_collaboration",)),
    (("일정", "로드맵", "마일스톤", "리스크"), ("schedule_risk",)),
    (("장비", "서버", "인프라", "네트워크", "구성"), ("system_configuration",)),
    (("기능", "서비스", "업무", "화면", "프로세스"), ("functional_workflow",)),
    (("데이터", "수집", "연계", "변환", "전처리"), ("data_pipeline",)),
    (("인터페이스", "연동", "ui", "ux"), ("interface_ux",)),
    (("성능", "가용성", "용량"), ("performance_capacity",)),
    (("ai", "분석", "모델", "예측", "추천"), ("analytics_ai",)),
    (("테스트", "검증", "bmt"), ("testing_validation",)),
    (("보안", "개인정보", "권한"), ("security_privacy",)),
    (("품질", "유지보수"), ("quality_management",)),
    (("법", "표준", "규제", "제약", "준수"), ("constraints_compliance",)),
    (("프로젝트", "사업관리", "pm", "형상관리", "성과물"), ("project_management_execution",)),
    (("안정화", "운영지원", "유지관리", "기술지원", "교육"), ("operations_support_transition",)),
    (("산출물", "검수", "인수", "인계"), ("transition_acceptance",)),
    (("컨설팅", "진단", "자문"), ("consulting_methodology",)),
    (("회사", "소개", "역량", "실적", "레퍼런스", "인력"), ("capability_evidence",)),
    (("특허", "지식재산", "지재권", "저작권", "인증", "기술력"), ("patent_ip_evidence",)),
)


def _dedupe_keys(keys: list[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for key in keys:
        if key in seen or key not in PLAYBOOK_BY_KEY:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def select_research_playbook_keys(
    *,
    writing_mode: str = "",
    unit_pattern: str = "",
    heading_text: str = "",
) -> list[str]:
    keys: list[str] = []
    if unit_pattern:
        keys.extend(UNIT_PATTERN_PLAYBOOK_MAP.get(unit_pattern, ()))

    normalized_heading = re.sub(r"\s+", "", heading_text).lower()
    for keywords, mapped_keys in HEADING_PLAYBOOK_HINTS:
        if any(keyword.lower() in normalized_heading for keyword in keywords):
            keys.extend(mapped_keys)

    if not keys:
        if writing_mode == "background":
            keys.extend(("policy_background", "business_need"))
        elif writing_mode == "need":
            keys.extend(("business_need",))
        elif writing_mode == "strategy":
            keys.extend(("delivery_method",))
        elif writing_mode == "execution":
            keys.extend(("functional_workflow",))
        elif writing_mode == "operations":
            keys.extend(("quality_management",))
        elif writing_mode == "evidence":
            keys.extend(("capability_evidence",))

    return _dedupe_keys(keys)


def selected_research_playbooks(
    *,
    writing_mode: str = "",
    unit_pattern: str = "",
    heading_text: str = "",
) -> list[ResearchPlaybook]:
    return [
        PLAYBOOK_BY_KEY[key]
        for key in select_research_playbook_keys(
            writing_mode=writing_mode,
            unit_pattern=unit_pattern,
            heading_text=heading_text,
        )
    ]


def _playbook_lines(item: ResearchPlaybook) -> list[str]:
    return [
        f"- pattern_key={item.pattern_key}",
        f"  label={item.label_ko}",
        f"  description={item.description_ko}",
        f"  default_planned_search={item.default_planned_search}",
        f"  adaptive_search_allowed={'yes' if item.adaptive_search_allowed else 'no'}",
        f"  adaptive_conditions={', '.join(item.adaptive_conditions) if item.adaptive_conditions else '-'}",
        f"  preferred_sources={', '.join(item.preferred_sources) if item.preferred_sources else '-'}",
        f"  must_capture={', '.join(item.must_capture) if item.must_capture else '-'}",
        f"  avoid_search_for={', '.join(item.avoid_search_for) if item.avoid_search_for else '-'}",
        f"  draft_expression={', '.join(item.draft_expression) if item.draft_expression else '-'}",
        f"  notes={', '.join(item.notes) if item.notes else '-'}",
    ]


def build_selected_research_playbook_reference_text(
    *,
    writing_mode: str = "",
    unit_pattern: str = "",
    heading_text: str = "",
) -> str:
    selected = selected_research_playbooks(
        writing_mode=writing_mode,
        unit_pattern=unit_pattern,
        heading_text=heading_text,
    )
    if not selected:
        return "별도 선택된 검색 가이드 없음"

    lines = [
        "다음 항목은 현재 파트에 우선적으로 참고할 검색 가이드입니다.",
        "이 가이드는 하드 규칙이 아니라 1차 참고자료이며, 현재 요구사항과 초안 목적에 맞게 필요한 항목만 선별해서 사용하세요.",
        "공통 원칙: 모든 외부 검색은 최신 정보 기준으로 수행하고, 오늘 날짜를 질의/판단 문맥에 명시하며, 정책은 현재 실제 수행 중인 정책인지 확인하고, 출처와 날짜가 분명한 자료를 우선합니다.",
    ]
    for item in selected:
        lines.append("\n".join(_playbook_lines(item)))
    return "\n".join(lines)


def select_research_playbook_keys_for_headings(headings: list[str]) -> list[str]:
    keys: list[str] = []
    for heading in headings:
        keys.extend(select_research_playbook_keys(heading_text=heading))
    return _dedupe_keys(keys)


def build_selected_research_playbook_reference_text_for_headings(headings: list[str]) -> str:
    selected = [PLAYBOOK_BY_KEY[key] for key in select_research_playbook_keys_for_headings(headings)]
    if not selected:
        return "별도 선택된 검색 가이드 없음"

    lines = [
        "다음 항목은 현재 목차 묶음에 우선적으로 참고할 검색 가이드입니다.",
        "이 가이드는 하드 규칙이 아니라 1차 참고자료이며, 현재 목차 목적과 요구사항에 맞게 필요한 항목만 선별해서 사용하세요.",
        "공통 원칙: 모든 외부 검색은 최신 정보 기준으로 수행하고, 오늘 날짜를 질의/판단 문맥에 명시하며, 정책은 현재 실제 수행 중인 정책인지 확인하고, 출처와 날짜가 분명한 자료를 우선합니다.",
    ]
    for item in selected:
        lines.append("\n".join(_playbook_lines(item)))
    return "\n".join(lines)


def build_research_playbook_reference_text() -> str:
    lines = [
        "다음 항목은 검색 의도를 고정 규칙으로 강제하는 목록이 아니라, LLM이 검색 필요성과 질의를 판단할 때 참고하는 1차 가이드입니다.",
        "현재 generation unit의 목적과 요구사항에 맞게 필요한 항목만 선별하고, 회사 내부 근거로 충분한 경우에는 외부 검색을 생략합니다.",
        "공통 원칙: 모든 외부 검색은 최신 정보 기준으로 수행하고, 오늘 날짜를 질의/판단 문맥에 명시하며, 정책은 현재 실제 수행 중인 정책인지 확인하고, 출처와 날짜가 분명한 자료를 우선합니다.",
    ]
    for item in RESEARCH_PLAYBOOKS:
        lines.append("\n".join(_playbook_lines(item)))
    return "\n".join(lines)
