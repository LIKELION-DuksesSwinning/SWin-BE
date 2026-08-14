from datetime import timedelta

from .models import Analysis
from .models import WeeklyReport, RoutineRecommendation

# Analysis에서 쓰던 1/3/5 숫자를 다시 low/mid/high로 되돌리는 역매핑
SCORE_TO_LEVEL = {1: "low", 3: "mid", 5: "high"}

SYMPTOM_TO_PRODUCTS = {}

def generate_weekly_report(user, week_start, week_end=None):
    """
    week_start 기준 7일치 Analysis를 모아서 WeeklyReport를 생성/갱신.
    보통 Celery beat 등으로 매주 월요일 06시에 실행하는 배치 함수로 사용.
    """
    week_end = week_end or (week_start + timedelta(days=6))

    week_analyses = Analysis.objects.filter(
        user=user,
        created_at__date__gte=week_start,
        created_at__date__lte=week_end,
    ).select_related("swim_record")

    # 1) 수영 횟수 / 평균 수영 시간 — AFTER 기록(swim_record) 기준
    swim_records = [a.swim_record for a in week_analyses if a.swim_record]
    swim_count = len(set(r.id for r in swim_records))
    durations = [r.swim_time for r in swim_records if getattr(r, "swim_time", None)]
    avg_swim_duration = round(sum(durations) / len(durations)) if durations else 0

    # 2) symptomTrend — 각 분석의 symptomChanges(after 값)를 날짜별로 펼침
    symptom_trend = []
    for analysis in week_analyses:
        date_str = analysis.created_at.date().isoformat()
        for change in analysis.symptom_changes:
            score = SCORE_TO_LEVEL.get(change["after"])
            if score:
                symptom_trend.append({
                    "date": date_str,
                    "symptomType": change["symptomType"],
                    "score": score,
                })
    symptom_trend.sort(key=lambda x: x["date"])

    # 3) 클리닉 연계 권장 — 이번 주 분석 중 하나라도 권장됐으면 true
    clinic_recommended = any(a.clinic_recommended for a in week_analyses)

    # 4) 다른 수영장 추천 — 같은 Pool에서 반복적으로 악화 패턴이 나오면 true (단순 규칙, 팀 확인 필요)
    other_pool_recommended = _check_pool_issue(swim_records, week_analyses)

    report, _ = WeeklyReport.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={
            "week_end": week_end,
            "swim_count": swim_count,
            "avg_swim_duration": avg_swim_duration,
            "symptom_trend": symptom_trend,
            "clinic_recommended": clinic_recommended,
            "other_pool_recommended": other_pool_recommended,
        },
    )
    return report

def _find_dominant_symptom(week_analyses):
    """이번 주 기록 중 after 점수가 가장 높게(심하게) 나온 증상 종류를 하나 고름"""
    worst_symptom = None
    worst_score = 0
    for analysis in week_analyses:
        for change in analysis.symptom_changes:
            if change["after"] > worst_score:
                worst_score = change["after"]
                worst_symptom = change["symptomType"]
    return worst_symptom


def _check_pool_issue(swim_records, week_analyses):
    """
    같은 수영장에서 계속 수영했는데 증상이 악화 경향이면 다른 수영장 추천.
    TODO: 팀과 정확한 기준(예: 같은 pool에서 N회 이상 + worsened 여부) 확정 필요.
    """
    pool_ids = set(getattr(r, "pool_id", None) for r in swim_records)
    pool_ids.discard(None)
    if len(pool_ids) != 1:
        return False  # 여러 수영장을 다녔으면 특정 수영장 탓이라 보기 어려움

    # 같은 수영장만 다녔는데, 이번 주 분석 중 절반 이상이 clinic_recommended면 의심 신호로 간주
    if not week_analyses:
        return False
    flagged = sum(1 for a in week_analyses if a.clinic_recommended)
    return flagged >= (len(week_analyses) / 2)

def _build_condition_text(dominant_symptom, worst_score):
    """회복 모드일 때만 '복귀 조건' 문구 생성. 화면 예시: '붉음·당김이 2일 연속 감소하면 기존 루틴으로'"""
    if worst_score >= 5 and dominant_symptom:
        return f"{dominant_symptom}이(가) 2일 연속 감소하면 기존 루틴으로 돌아가세요."
    return None 

# TODO: 피부 관리 루틴 내용 미정 — 아래는 구조(틀)만 잡아둔 상태
ROUTINE_STEPS = {
    # "여드름": {"name": "트러블 루틴", "steps": [...]},
    # "건조": {"name": "보습 강화 루틴", "steps": [...]},
    # ...
}


def generate_routine_recommendation(weekly_report, user):
    """
    WeeklyReport 생성 직후 호출해서 1:1 루틴 추천을 만듦.
    swim_period(평소 패턴) 기반 비율 조정 로직은 별도 확정 필요 — 여기선 임시 규칙 사용.
    """
    dominant_symptom = None
    worst_score = 0
    for change_entry in weekly_report.symptom_trend:
        score_num = {"low": 1, "mid": 3, "high": 5}[change_entry["score"]]
        if score_num > worst_score:
            worst_score = score_num
            dominant_symptom = change_entry["symptomType"]

    # 심각도에 따른 회복/보통 모드
    try:
        profile = user.skin_profile
        base_count = profile.weekly_swim_count or 3
        base_duration = profile.avg_swim_duration or 50
    except AttributeError:
        base_count, base_duration = 3, 50

    if worst_score >= 5:
        recommended_swim_count = max(1, round(base_count * 0.6))
        recommended_swim_minutes = max(20, round(base_duration * 0.6))
        intensity_note = "회복 전까지 강도는 가볍게"
    elif worst_score >= 3:
        recommended_swim_count = max(1, round(base_count * 0.85))
        recommended_swim_minutes = max(30, round(base_duration * 0.9))
        intensity_note = None
    else:
        recommended_swim_count = base_count
        recommended_swim_minutes = base_duration
        intensity_note = None

    condition_text = _build_condition_text(dominant_symptom, worst_score)
    skin_care_routine = _build_skin_care_routine(dominant_symptom)

    routine, _ = RoutineRecommendation.objects.update_or_create(
        weekly_report=weekly_report,
        defaults={
            "recommended_swim_count": recommended_swim_count,
            "recommended_swim_minutes": recommended_swim_minutes,
            "intensity_note": intensity_note,
            "condition_text": condition_text,
            "skin_care_routine": skin_care_routine,
        },
    )
    return routine



def _build_skin_care_routine(dominant_symptom):
    routines = []
    if dominant_symptom in ROUTINE_STEPS:
        routines.append({**ROUTINE_STEPS[dominant_symptom], "priority": 1})
    return routines
