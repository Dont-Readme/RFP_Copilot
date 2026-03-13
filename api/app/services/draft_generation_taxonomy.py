from __future__ import annotations

from dataclasses import dataclass
import re

from app.models.rfp import RfpRequirementItem


VALID_WRITING_MODES = {"background", "need", "strategy", "execution", "operations", "evidence"}


@dataclass(frozen=True)
class UnitPatternDefinition:
    key: str
    writing_mode: str
    label_ko: str
    description_ko: str
    required_aspects: tuple[str, ...]
    keyword_hints: tuple[str, ...] = ()


UNIT_PATTERN_DEFINITIONS: tuple[UnitPatternDefinition, ...] = (
    UnitPatternDefinition(
        key="policy_background",
        writing_mode="background",
        label_ko="정책·환경 배경형",
        description_ko="정책, 시장, 행정 환경, 기존 문제 상황, 사업 추진 배경을 설명할 때 사용합니다.",
        required_aspects=("정책·사업 환경", "현안 또는 문제 상황", "사업 추진 배경", "제안 필요성과의 연결"),
        keyword_hints=("배경", "환경", "동향", "시장", "정책", "현황", "여건"),
    ),
    UnitPatternDefinition(
        key="business_need",
        writing_mode="need",
        label_ko="사업 필요성형",
        description_ko="문제 정의, 추진 필요성, 기대 효과를 설명할 때 사용합니다.",
        required_aspects=("문제 정의", "사업 필요성", "개선 목표", "기대 효과"),
        keyword_hints=("필요성", "목적", "효과", "문제", "개선"),
    ),
    UnitPatternDefinition(
        key="delivery_method",
        writing_mode="strategy",
        label_ko="수행 방법론형",
        description_ko="애자일, 단계적 구축, 시범 적용 후 확산 등 수행 방식과 방법론을 설명할 때 사용합니다.",
        required_aspects=("수행 방법론", "단계별 추진 접근", "핵심 차별화 포인트", "적용·확산 방식"),
        keyword_hints=("전략", "방법론", "추진방안", "수행방안", "접근"),
    ),
    UnitPatternDefinition(
        key="governance_collaboration",
        writing_mode="strategy",
        label_ko="거버넌스·협업형",
        description_ko="컨소시엄, 전문가 자문, PMO, 의사결정, 보고체계, 역할 분담을 설명할 때 사용합니다.",
        required_aspects=("조직 및 역할", "의사결정 체계", "협업 구조", "보고 및 의사소통", "외부 협력·자문 체계"),
        keyword_hints=("수행체계", "조직", "역할", "협업", "컨소시엄", "거버넌스", "인력"),
    ),
    UnitPatternDefinition(
        key="schedule_risk",
        writing_mode="strategy",
        label_ko="일정·리스크 관리형",
        description_ko="마일스톤, 일정 운영, 위험관리, 형상관리, 진도관리 등을 설명할 때 사용합니다.",
        required_aspects=("단계별 일정", "마일스톤", "진도관리", "리스크 대응", "형상·문서 관리"),
        keyword_hints=("일정", "로드맵", "마일스톤", "위험", "리스크", "관리"),
    ),
    UnitPatternDefinition(
        key="system_configuration",
        writing_mode="execution",
        label_ko="시스템 장비구성형",
        description_ko="하드웨어, 소프트웨어, 네트워크, 개발·운영 환경, 도입 장비 및 구성요소를 설명할 때 사용합니다.",
        required_aspects=("구성 범위", "하드웨어·소프트웨어 구성", "네트워크 및 배치", "개발·운영 환경", "도입 및 적용 방식"),
        keyword_hints=("장비", "서버", "인프라", "네트워크", "구성", "하드웨어", "소프트웨어"),
    ),
    UnitPatternDefinition(
        key="functional_workflow",
        writing_mode="execution",
        label_ko="기능·업무 흐름형",
        description_ko="사용자 기능, 업무 흐름, 서비스 동작, 화면·프로세스 흐름을 설명할 때 사용합니다.",
        required_aspects=("대상 사용자·업무", "핵심 기능", "처리 흐름", "입력·출력", "예외 처리", "운영 포인트"),
        keyword_hints=("기능", "서비스", "업무", "화면", "프로세스", "workflow", "동작"),
    ),
    UnitPatternDefinition(
        key="data_pipeline",
        writing_mode="execution",
        label_ko="데이터 구축·연계형",
        description_ko="초기자료 구축, 데이터 수집·연계·변환·전처리·표준화·적재를 설명할 때 사용합니다.",
        required_aspects=("데이터 범위 정의", "수집·연계 원천", "데이터 구축 역할분담", "변환·정제·전처리", "표준화 및 저장 구조", "서비스·분석 반영", "데이터 보안·검증"),
        keyword_hints=("데이터", "수집", "연계", "변환", "전처리", "정제", "적재", "초기자료"),
    ),
    UnitPatternDefinition(
        key="interface_ux",
        writing_mode="execution",
        label_ko="인터페이스·사용자 경험형",
        description_ko="외부 시스템 인터페이스, 사용자 인터페이스, 프로토콜 연계, UX 고려사항을 설명할 때 사용합니다.",
        required_aspects=("연계 대상", "인터페이스 방식·프로토콜", "정보 교환 흐름", "화면·UI/UX 설계", "오류·예외 처리", "사용자 편의성"),
        keyword_hints=("인터페이스", "연동", "연계", "ui", "ux", "프로토콜", "정보교환"),
    ),
    UnitPatternDefinition(
        key="performance_capacity",
        writing_mode="execution",
        label_ko="성능·용량형",
        description_ko="응답시간, 처리량, 가용성, 확장성, 운영시간 등 성능과 용량 요구를 설명할 때 사용합니다.",
        required_aspects=("성능 목표", "처리량·응답시간", "용량 및 확장성", "가용성", "운영시간·운용조건", "성능 확보 방안"),
        keyword_hints=("성능", "처리량", "응답시간", "가용성", "용량", "확장"),
    ),
    UnitPatternDefinition(
        key="analytics_ai",
        writing_mode="execution",
        label_ko="분석·AI 활용형",
        description_ko="분석 로직, 예측, 추천, 모델·규칙 적용, 결과 활용을 설명할 때 사용합니다.",
        required_aspects=("분석 목표", "입력 데이터", "전처리 및 분석 준비", "규칙·모델 적용", "결과 해석 및 활용", "정확도·검증", "운영·개선"),
        keyword_hints=("분석", "예측", "ai", "모델", "추천", "의사결정", "알고리즘"),
    ),
    UnitPatternDefinition(
        key="testing_validation",
        writing_mode="execution",
        label_ko="테스트·검증형",
        description_ko="단위/통합/시스템/성능 테스트, BMT, 표준 적합성 검증 등을 설명할 때 사용합니다.",
        required_aspects=("테스트 대상", "테스트 유형", "테스트 환경", "절차 및 방법", "샘플·모의 데이터 활용", "검증 기준 및 판정"),
        keyword_hints=("테스트", "검증", "bmt", "단위테스트", "통합테스트", "시스템테스트"),
    ),
    UnitPatternDefinition(
        key="security_privacy",
        writing_mode="operations",
        label_ko="보안·개인정보형",
        description_ko="기밀성·무결성, 접근통제, 문서보관, 통신보안, 개인정보보호를 설명할 때 사용합니다.",
        required_aspects=("접근통제 및 권한", "통신·저장 보안", "문서·로그 보관", "개인정보보호", "기밀성·무결성 확보", "보안 운영 절차"),
        keyword_hints=("보안", "권한", "접근통제", "개인정보", "암호화", "기밀성", "무결성"),
    ),
    UnitPatternDefinition(
        key="quality_management",
        writing_mode="operations",
        label_ko="품질 관리형",
        description_ko="신뢰성, 사용성, 유지보수성, 이식성, 보안성 등 품질 목표와 관리 체계를 설명할 때 사용합니다.",
        required_aspects=("품질 목표", "품질 항목", "평가 대상", "품질 확보 활동", "유지보수성·이식성", "품질 점검 체계"),
        keyword_hints=("품질", "신뢰성", "사용성", "유지보수", "이식성", "품질관리"),
    ),
    UnitPatternDefinition(
        key="constraints_compliance",
        writing_mode="operations",
        label_ko="제약·준수형",
        description_ko="기술, 표준, 법·제도, 업무상 제약과 대응 방안을 설명할 때 사용합니다.",
        required_aspects=("제약 조건", "관련 표준·법제도", "업무상 영향", "대응 원칙", "설계·운영 반영 방안"),
        keyword_hints=("제약", "법", "규정", "표준", "준수", "규제"),
    ),
    UnitPatternDefinition(
        key="project_management_execution",
        writing_mode="operations",
        label_ko="프로젝트 관리 실행형",
        description_ko="사업관리, 투입인력, 일정, 형상관리, 보안관리, 성과물 관리 등 프로젝트 관리 요구를 설명할 때 사용합니다.",
        required_aspects=("사업관리 조직", "투입인력·역할", "일정·진도 관리", "보안·위험 관리", "성과물·형상 관리", "협력사 연계"),
        keyword_hints=("사업관리", "pm", "투입인력", "형상관리", "진도", "성과물", "프로젝트"),
    ),
    UnitPatternDefinition(
        key="operations_support_transition",
        writing_mode="operations",
        label_ko="운영 지원·안정화형",
        description_ko="안정화, 운영지원, 교육훈련, 기술지원, 하자보수, 유지관리를 설명할 때 사용합니다.",
        required_aspects=("안정화 지원", "운영지원 체계", "교육·기술이전", "하자보수·유지관리", "장애 대응", "지속 운영 방안"),
        keyword_hints=("운영", "안정화", "교육", "기술지원", "유지관리", "하자보수", "지원"),
    ),
    UnitPatternDefinition(
        key="transition_acceptance",
        writing_mode="operations",
        label_ko="이행·검수·인수형",
        description_ko="산출물, 검수, 인수인계, 문서화, 완료 기준을 설명할 때 사용합니다.",
        required_aspects=("산출물 목록", "검수 기준", "인수인계 절차", "문서화", "완료 판정 및 종료 조건"),
        keyword_hints=("산출물", "검수", "인수", "인계", "문서", "완료"),
    ),
    UnitPatternDefinition(
        key="consulting_methodology",
        writing_mode="execution",
        label_ko="컨설팅 수행형",
        description_ko="컨설팅 방법론, 세부 활동, 결과 적정성 확인, 산출물 중심 수행을 설명할 때 사용합니다.",
        required_aspects=("컨설팅 목표", "세부 활동", "분석·진단 방법", "결과 검토", "산출물", "적용 및 후속 조치"),
        keyword_hints=("컨설팅", "진단", "분석", "자문", "방법론"),
    ),
    UnitPatternDefinition(
        key="capability_evidence",
        writing_mode="evidence",
        label_ko="회사 역량 근거형",
        description_ko="회사 소개, 수행 역량, 조직, 인력, 유사 실적을 근거 중심으로 설명할 때 사용합니다.",
        required_aspects=("회사 개요", "관련 수행 역량", "전담 조직·인력", "유사 실적", "본 사업 적용 근거"),
        keyword_hints=("회사", "소개", "역량", "실적", "레퍼런스", "인력"),
    ),
    UnitPatternDefinition(
        key="patent_ip_evidence",
        writing_mode="evidence",
        label_ko="특허·지식재산 근거형",
        description_ko="특허, 인증, 저작권, 지식재산, 보유 기술을 근거 중심으로 설명할 때 사용합니다.",
        required_aspects=("보유 특허·지식재산", "기술적 강점", "관련성", "사업 적용 시 기대 효과"),
        keyword_hints=("특허", "지식재산", "지재권", "저작권", "인증", "기술력"),
    ),
)


PATTERN_BY_KEY = {pattern.key: pattern for pattern in UNIT_PATTERN_DEFINITIONS}

PATTERN_OUTPUT_GUIDANCE: dict[str, dict[str, tuple[str, ...]]] = {
    "policy_background": {
        "tables": ("정책·환경 변화 요약 표",),
        "figures": ("사업 추진 배경을 보여주는 환경 변화 개념 그림",),
        "diagrams": ("정책 변화 -> 현안 심화 -> 사업 추진 필요성 흐름 도식",),
    },
    "business_need": {
        "tables": ("현행 문제점과 개선 목표 비교 표",),
        "figures": ("현행 대비 목표 상태 비교 그림",),
        "diagrams": ("문제 현황 -> 개선 방향 -> 기대 효과 흐름 도식",),
    },
    "delivery_method": {
        "tables": ("단계별 수행 전략 및 적용 범위 표",),
        "figures": ("전체 수행 방법론 개념 그림",),
        "diagrams": ("착수 -> 분석 -> 설계 -> 구축 -> 검증 -> 확산 흐름 도식",),
    },
    "governance_collaboration": {
        "tables": ("조직별 역할 및 책임 분담 표",),
        "figures": ("거버넌스 및 협업 체계 그림",),
        "diagrams": ("발주기관 -> PMO/총괄 -> 수행조직 -> 자문체계 협업 도식",),
    },
    "schedule_risk": {
        "tables": ("단계별 일정·마일스톤·주요 산출물 표", "리스크 항목 및 대응 방안 표"),
        "figures": ("연차별 추진 로드맵 그림",),
        "diagrams": ("1차년도 -> 2차년도 -> 안정화 단계 흐름 도식",),
    },
    "system_configuration": {
        "tables": ("시스템 장비 및 소프트웨어 구성 표",),
        "figures": ("시스템 구성도 그림",),
        "diagrams": ("사용자/단말 -> 응용서비스 -> 데이터/연계 계층 도식",),
    },
    "functional_workflow": {
        "tables": ("기능별 입력·처리·출력 정의 표",),
        "figures": ("주요 사용자 기능 화면 흐름 그림",),
        "diagrams": ("업무 요청 -> 처리 -> 결과 확인 workflow 도식",),
    },
    "data_pipeline": {
        "tables": (
            "데이터 항목 정의 및 출처 표",
            "수집원·연계 방식·전처리·저장 구조 표",
        ),
        "figures": ("데이터 수집 및 활용 체계 그림",),
        "diagrams": ("수집원 -> 연계/수집 -> 정제/표준화 -> 저장 -> 분석/서비스 반영 도식",),
    },
    "interface_ux": {
        "tables": ("인터페이스 대상·방식·주기·오류 대응 표",),
        "figures": ("사용자 화면 흐름 및 UX 개념 그림",),
        "diagrams": ("외부 시스템 -> 연계 인터페이스 -> 내부 서비스 화면 도식",),
    },
    "performance_capacity": {
        "tables": ("성능 목표 및 검증 기준 표",),
        "figures": ("성능 확보 구조 개념 그림",),
        "diagrams": ("요청 유입 -> 처리 -> 확장/분산 -> 모니터링 도식",),
    },
    "analytics_ai": {
        "tables": ("분석 대상·입력 데이터·활용 결과 표",),
        "figures": ("분석/AI 활용 개념 그림",),
        "diagrams": ("데이터 준비 -> 분석/모델 적용 -> 결과 해석 -> 서비스 활용 도식",),
    },
    "testing_validation": {
        "tables": ("테스트 유형·환경·절차·판정 기준 표",),
        "figures": ("검증 체계 그림",),
        "diagrams": ("단위 테스트 -> 통합 테스트 -> 시스템 테스트 -> 성능 검증 도식",),
    },
    "security_privacy": {
        "tables": ("보안 통제 항목 및 적용 방안 표",),
        "figures": ("보안 적용 영역 그림",),
        "diagrams": ("접근 통제 -> 암호화 -> 로그/감사 -> 모니터링 도식",),
    },
    "quality_management": {
        "tables": ("품질 항목·목표·점검 방법 표",),
        "figures": ("품질 관리 체계 그림",),
        "diagrams": ("품질 계획 -> 점검 -> 보완 -> 승인 도식",),
    },
    "constraints_compliance": {
        "tables": ("제약 조건 및 대응 원칙 표",),
        "figures": ("준수 체계 그림",),
        "diagrams": ("제약 확인 -> 설계 반영 -> 점검/준수 확인 도식",),
    },
    "project_management_execution": {
        "tables": ("사업관리 체계·투입인력·산출물 관리 표",),
        "figures": ("사업관리 운영 체계 그림",),
        "diagrams": ("계획 -> 진도관리 -> 리스크/보안 관리 -> 보고/승인 도식",),
    },
    "operations_support_transition": {
        "tables": ("운영지원·교육·하자보수 계획 표",),
        "figures": ("안정화 및 운영지원 체계 그림",),
        "diagrams": ("구축 완료 -> 안정화 -> 운영지원 -> 유지관리 도식",),
    },
    "transition_acceptance": {
        "tables": ("산출물·검수·인수인계 기준 표",),
        "figures": ("검수 및 인수 절차 그림",),
        "diagrams": ("산출물 제출 -> 검수 -> 보완 -> 인수인계 도식",),
    },
    "consulting_methodology": {
        "tables": ("컨설팅 단계별 활동 및 산출물 표",),
        "figures": ("컨설팅 수행 체계 그림",),
        "diagrams": ("진단 -> 분석 -> 개선안 도출 -> 결과 검토 -> 적용 도식",),
    },
    "capability_evidence": {
        "tables": ("회사 역량·인력·실적 근거 표",),
        "figures": ("회사 역량 체계 그림",),
        "diagrams": ("보유 역량 -> 적용 경험 -> 본 사업 적용 가치 도식",),
    },
    "patent_ip_evidence": {
        "tables": ("특허·지식재산·보유기술 목록 표",),
        "figures": ("기술 자산 포트폴리오 그림",),
        "diagrams": ("보유 기술 -> 사업 적용 기능 -> 기대 효과 도식",),
    },
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text or "").lower()


def get_unit_pattern_definition(pattern_key: str) -> UnitPatternDefinition | None:
    return PATTERN_BY_KEY.get(pattern_key)


def normalize_writing_mode(mode: str, *, heading_text: str = "") -> str:
    normalized = (mode or "").strip().lower()
    if normalized in VALID_WRITING_MODES:
        return normalized
    compact_heading = _compact(heading_text)
    if any(keyword in compact_heading for keyword in ("배경", "시장", "환경", "현황", "정책")):
        return "background"
    if any(keyword in compact_heading for keyword in ("필요", "목적", "효과", "개선")):
        return "need"
    if any(keyword in compact_heading for keyword in ("전략", "방법론", "체계", "추진")):
        return "strategy"
    if any(keyword in compact_heading for keyword in ("운영", "품질", "보안", "유지보수", "지원")):
        return "operations"
    if any(keyword in compact_heading for keyword in ("실적", "특허", "회사", "소개", "역량", "인력")):
        return "evidence"
    return "execution"


def infer_unit_pattern(
    *,
    writing_mode: str,
    heading_text: str,
    requirements: list[RfpRequirementItem],
    requested_pattern: str = "",
) -> str:
    if requested_pattern in PATTERN_BY_KEY:
        return requested_pattern

    search_space = " ".join(
        [
            heading_text,
            *[
                " ".join(
                    filter(
                        None,
                        [
                            requirement.requirement_no,
                            requirement.name,
                            requirement.definition,
                            requirement.details,
                        ],
                    )
                )
                for requirement in requirements
            ],
        ]
    )
    compact_text = _compact(search_space)

    candidates = [
        pattern
        for pattern in UNIT_PATTERN_DEFINITIONS
        if pattern.writing_mode == writing_mode
    ]
    if not candidates:
        candidates = [pattern for pattern in UNIT_PATTERN_DEFINITIONS if pattern.writing_mode == "execution"]

    best_pattern = None
    best_score = -1
    for pattern in candidates:
        score = sum(3 if hint in _compact(heading_text) else 1 for hint in pattern.keyword_hints if hint in compact_text)
        if score > best_score:
            best_pattern = pattern
            best_score = score

    if best_pattern is not None and best_score > 0:
        return best_pattern.key

    fallback_by_mode = {
        "background": "policy_background",
        "need": "business_need",
        "strategy": "delivery_method",
        "execution": "functional_workflow",
        "operations": "operations_support_transition",
        "evidence": "capability_evidence",
    }
    return fallback_by_mode.get(writing_mode, "functional_workflow")


def default_required_aspects_for_pattern(pattern_key: str) -> list[str]:
    pattern = get_unit_pattern_definition(pattern_key)
    if pattern is None:
        return []
    return list(pattern.required_aspects)


def build_pattern_reference_text(*, writing_mode: str | None = None) -> str:
    patterns = [
        pattern
        for pattern in UNIT_PATTERN_DEFINITIONS
        if writing_mode is None or pattern.writing_mode == writing_mode
    ]
    lines = []
    for pattern in patterns:
        lines.append(
            "\n".join(
                [
                    f"- pattern_key={pattern.key}",
                    f"  mode={pattern.writing_mode}",
                    f"  label={pattern.label_ko}",
                    f"  description={pattern.description_ko}",
                    f"  required_aspects={', '.join(pattern.required_aspects)}",
                ]
            )
        )
    return "\n".join(lines)


def summarize_pattern(pattern_key: str) -> str:
    pattern = get_unit_pattern_definition(pattern_key)
    if pattern is None:
        return ""
    return f"{pattern.label_ko}: {pattern.description_ko}"


def recommended_tables_for_pattern(pattern_key: str) -> list[str]:
    return list(PATTERN_OUTPUT_GUIDANCE.get(pattern_key, {}).get("tables", ()))


def recommended_figures_for_pattern(pattern_key: str) -> list[str]:
    return list(PATTERN_OUTPUT_GUIDANCE.get(pattern_key, {}).get("figures", ()))


def recommended_diagrams_for_pattern(pattern_key: str) -> list[str]:
    return list(PATTERN_OUTPUT_GUIDANCE.get(pattern_key, {}).get("diagrams", ()))


def summarize_output_guidance(pattern_key: str) -> str:
    tables = recommended_tables_for_pattern(pattern_key)
    figures = recommended_figures_for_pattern(pattern_key)
    diagrams = recommended_diagrams_for_pattern(pattern_key)
    lines: list[str] = []
    if tables:
        lines.append("권장 표: " + "; ".join(tables))
    if figures:
        lines.append("권장 그림: " + "; ".join(figures))
    if diagrams:
        lines.append("권장 도식: " + "; ".join(diagrams))
    return "\n".join(lines)
