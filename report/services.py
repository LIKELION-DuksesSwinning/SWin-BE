from datetime import timedelta

from AIanalysis.models import Analysis
from .models import WeeklyReport, RoutineRecommendation

# Analysis에서 쓰던 1~5 숫자를 low/mid/high로 묶는 매핑 (1~2: low, 3: mid, 4~5: high)
SCORE_TO_LEVEL = {1: "low", 2: "low", 3: "mid", 4: "high", 5: "high"}

# symptom_trend에 저장된 low/mid/high를 다시 대표 숫자로 되돌리는 역매핑 (심각도 비교/정렬용)
LEVEL_TO_SCORE_NUM = {"low": 1, "mid": 3, "high": 5}

# UserSkinProfile.weekly_swim_count/avg_swim_time은 accounts.OnboardingSerializer의
# VALID_SWIM_COUNTS/VALID_SWIM_TIMES 카테고리 문자열로 저장되므로, 숫자 연산 전에 대표값으로 변환한다.
WEEKLY_COUNT_TO_NUM = {"주 1~2회": 1.5, "주 3~4회": 3.5, "주 5회 이상": 5}
SWIM_TIME_TO_MINUTES = {"30분 미만": 20, "30~60분": 45, "60~90분": 75, "90분 이상": 100}

PITH_PRODUCT_CATALOG = {
    "코어 리빌드 크림": {
        "ingredients": ["글리세린", "세라마이드NP", "콜레스테롤", "스쿠알란", "지방산", "베타-시토스테롤"],
        "reason": "반복되는 건조·당김을 위한 데일리 장벽 관리",
    },
    "블루 리페어 하이드로 수딩 크림": {
        "ingredients": ["세라마이드NP", "판테놀", "알란토인", "스쿠알란", "글리세린", "히알루론산", "구아이아줄렌"],
        "reason": "수영 직후 가벼운 붉음·건조·열감 관리",
    },
    "블루 리페어 솔루션": {
        "ingredients": ["마데카소사이드", "마데카식애씨드", "아시아티코사이드", "아시아틱애씨드", "알란토인", "구아이아줄렌", "히알루론산"],
        "reason": "붉음과 건조가 함께 증가한 날의 집중 SOS 관리",
    },
    "클래리파이 겔 토너": {
        "ingredients": ["나이아신아마이드", "글리세린", "히알루론산"],
        "reason": "가벼운 수분 공급과 피부 컨디셔닝",
    },
    "판테티놀 선 에센스": {
        "ingredients": ["판테놀"],
        "reason": "야외 수영·일상 자외선 보호용",
    },
}


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
    durations = [r.duration_minutes for r in swim_records if getattr(r, "duration_minutes", None)]
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

    # 5) 맞춤 케어 추천(성분/제품) — 이번 주 가장 심했던 증상 기준
    recommended_ingredients, recommended_products = _build_care_recommendation(symptom_trend)

    report, _ = WeeklyReport.objects.update_or_create(
        user=user,
        week_start=week_start,
        defaults={
            "week_end": week_end,
            "swim_count": swim_count,
            "avg_swim_duration": avg_swim_duration,
            "symptom_trend": symptom_trend,
            "recommended_ingredients": recommended_ingredients,
            "recommended_products": recommended_products,
            "clinic_recommended": clinic_recommended,
            "other_pool_recommended": other_pool_recommended,
        },
    )
    return report

def _find_dominant_symptom(symptom_trend):
    """symptom_trend(주간 low/mid/high 트렌드) 중 가장 심각한 증상 종류와 대표 점수를 고름"""
    dominant_symptom = None
    worst_score = 0
    for entry in symptom_trend:
        score_num = LEVEL_TO_SCORE_NUM[entry["score"]]
        if score_num > worst_score:
            worst_score = score_num
            dominant_symptom = entry["symptomType"]
    return dominant_symptom, worst_score

def _select_pith_products(dominant_symptom, worst_score):
    """
    가장 심했던 증상 하나(SkinRecord.SymptomType 코드) + 그 심각도(점수)를 기준으로 제품을 고름.
    TODO: 가려움/트러블 전용 제품은 아직 카탈로그에 없어서 fallback(클래리파이 겔 토너)으로 처리 중.
    """
    selected = []

    if dominant_symptom == "dry":
        selected.append("코어 리빌드 크림")
    elif dominant_symptom == "redness":
        if worst_score >= 5:  # 상(HIGH) — 심한 붉음
            selected.append("블루 리페어 솔루션")
        else:  # 중(MID) 이하 — 가벼운 붉음
            selected.append("블루 리페어 하이드로 수딩 크림")
    else:
        # 가려움/트러블/없음/기록 없음 — 아직 전용 제품 없어서 기본 컨디셔닝 제품으로 대체
        selected.append("클래리파이 겔 토너")

    # 자외선 보호는 증상과 무관하게 항상 함께 안내 (야외 수영 전제)
    selected.append("판테티놀 선 에센스")

    return selected

def _build_care_recommendation(symptom_trend):
    """이번 주 가장 심했던 증상 하나 → 제품 선택 → 성분/제품 응답 형태로 변환"""
    dominant_symptom, worst_score = _find_dominant_symptom(symptom_trend)
    product_names = _select_pith_products(dominant_symptom, worst_score)

    recommended_products = [
        {"name": name, "reason": PITH_PRODUCT_CATALOG[name]["reason"]}
        for name in product_names
    ]

    # 성분은 선택된 제품들의 핵심 성분을 합쳐서 중복 제거, 상위 3개만
    seen = []
    for name in product_names:
        for ingredient in PITH_PRODUCT_CATALOG[name]["ingredients"]:
            if ingredient not in seen:
                seen.append(ingredient)
    recommended_ingredients = seen[:3]

    return recommended_ingredients, recommended_products

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



ROUTINE_CATEGORY_STEPS = {
    "장벽 보습 루틴": {
        "steps": [
            "수영 전: 건조한 부위에 보습제를 얇게 바르기",
            "수영 후: 미지근한 물로 충분히 헹구고 문지르지 않기",
            "샤워 후: 물기를 가볍게 닦고 촉촉한 상태에서 장벽 크림 바르기",
            "취침 전: 당김이 남은 부위에 크림 한 번 더 바르기",
            "오늘은 스크럽·필링·레티놀 등 자극 가능 성분 쉬기",
            "다음 날 아침 건조·당김 회복 정도 기록하기",
        ],
    },
    "진정·수분 루틴": {
        "steps": [
            "수영 후 가능한 한 빨리 미지근한 물로 헹구기",
            "수건으로 피부를 누르듯 물기 제거하기",
            "히알루론산 등 수분 제품을 가볍게 바르기",
            "그 위에 판테놀·알란토인·세라마이드 함유 수딩 크림 바르기",
            "붉음이나 열감이 뚜렷한 날은 집중 수딩 제품 사용하기",
            "사용 2시간 후 붉음·열감·당김 변화를 기록하기",
        ],
    },
    "트러블 최소자극 루틴": {
        "steps": [
            "수영 직후 얼굴과 헤어라인을 꼼꼼히 헹구기",
            "수영모·수건·고글이 닿은 부위를 부드럽게 세정하기",
            "손으로 트러블을 만지거나 짜지 않기",
            "유분감이 무거운 제품보다 가벼운 보습제 사용하기",
            "따갑거나 붉은 날에는 스크럽·필링·살리실산 사용하지 않기",
            "트러블 개수와 붉음 정도를 다음 수영 전까지 기록하기",
        ],
    },
    "진정·수분→장벽 보습": {
        # 붉음이 가라앉은 뒤에도 건조함이 남는 상황 → 1단계(진정·수분) 후 2단계(장벽 보습)로 이어짐
        "steps": [
            "[1단계 · 진정] 수영 후 가능한 한 빨리 미지근한 물로 헹구기",
            "[1단계 · 진정] 수건으로 피부를 누르듯 물기 제거하기",
            "[1단계 · 진정] 히알루론산 등 수분 제품을 가볍게 바르기",
            "[1단계 · 진정] 그 위에 판테놀·알란토인·세라마이드 함유 수딩 크림 바르기",
            "[2단계 · 보습] 붉음이 가라앉은 후에도 당김이 남아있으면 장벽 크림 한 번 더 바르기",
            "[2단계 · 보습] 오늘은 스크럽·필링·레티놀 등 자극 가능 성분 쉬기",
            "[2단계 · 보습] 다음 날 아침 붉음·건조·당김 회복 정도 기록하기",
        ],
    },
    "제품 추천 중단·상담": {
        "name": "제품 추천 중단·상담",
        "steps": [
        "증상의 원인이 다양할 수 있어 제품만으로 해결하기 어려워요.",
        "통증·고름·빠른 확산 등이 동반된다면 화장품 루틴보다 전문가 확인이 필요해요.",
        "가까운 더나 클리닉 상담을 받아보시는 걸 권장드려요."
    ],
        "priority": 1

    },
}

# 증상 코드(SkinRecord.SymptomType) → 루틴 카테고리(ROUTINE_CATEGORY_STEPS 키) 매핑.
# 가려움은 전용 루틴이 아직 없어 '진정·수분 루틴'으로 대체. none은 루틴 불필요.
SYMPTOM_TO_ROUTINE_CATEGORY = {
    "dry": "장벽 보습 루틴",
    "redness": "진정·수분 루틴",
    "itchy": "진정·수분 루틴",
    "trouble": "트러블 최소자극 루틴",
    "needs_check": "제품 추천 중단·상담",
}

MAX_ROUTINE_RECOMMENDATIONS = 2


def _rank_symptom_severities(symptom_trend):
    """symptom_type별 이번 주 최고 심각도(대표 점수)를 구해서 심각한 순으로 정렬"""
    worst_by_type = {}
    for entry in symptom_trend:
        score_num = LEVEL_TO_SCORE_NUM[entry["score"]]
        symptom_type = entry["symptomType"]
        if score_num > worst_by_type.get(symptom_type, 0):
            worst_by_type[symptom_type] = score_num
    return sorted(worst_by_type.items(), key=lambda item: item[1], reverse=True)


def _build_skin_care_routine(symptom_trend, max_routines=MAX_ROUTINE_RECOMMENDATIONS):
    """
    이번 주 가장 심각했던 증상 순으로 최대 max_routines개까지 루틴 추천(1순위/2순위).
    needs_check가 하나라도 있으면 안전을 위해 항상 1순위로 올림.
    같은 루틴 카테고리로 매핑되는 증상이 여러 개면(예: 붉음+가려움) 하나로 합침.
    """
    ranked_types = [t for t, _ in _rank_symptom_severities(symptom_trend) if t != "needs_check"]
    if any(entry["symptomType"] == "needs_check" for entry in symptom_trend):
        ranked_types = ["needs_check"] + ranked_types

    routines = []
    seen_categories = set()
    for symptom_type in ranked_types:
        category = SYMPTOM_TO_ROUTINE_CATEGORY.get(symptom_type)
        if not category or category in seen_categories:
            continue
        seen_categories.add(category)
        routines.append({**ROUTINE_CATEGORY_STEPS[category], "name": category, "priority": len(routines) + 1})
        if len(routines) >= max_routines:
            break

    return routines


def generate_routine_recommendation(weekly_report, user):
    """
    WeeklyReport 생성 직후 호출해서 1:1 루틴 추천을 만듦.
    swim_period(평소 패턴) 기반 비율 조정 로직은 별도 확정 필요
    """
    dominant_symptom, worst_score = _find_dominant_symptom(weekly_report.symptom_trend)

    # 심각도에 따른 회복/보통 모드
    try:
        profile = user.skin_profile
        base_count = WEEKLY_COUNT_TO_NUM.get(profile.weekly_swim_count, 3)
        base_duration = SWIM_TIME_TO_MINUTES.get(profile.avg_swim_time, 50)
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
    skin_care_routine = _build_skin_care_routine(weekly_report.symptom_trend)

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
