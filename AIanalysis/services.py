import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Analysis

client = OpenAI(api_key=settings.OPENAI_API_KEY)

SKIN_PATTERN_SCHEMA = {
    "name": "skin_pattern",
    "schema": {
        "type": "object",
        "properties": {
            "patternTypes": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [
                        "redness_type", "dry_tight_type", "itch_type",
                        "trouble_type", "normal", "need_expert",
                    ],
                },
            },
            "patternDescription": {"type": "string"},
        },
        "required": ["patternTypes", "patternDescription"],
        "additionalProperties": False,
    },
    "strict": True,
}


def _build_skin_profile_text(user):
    try:
        profile = user.skin_profile
    except AttributeError:
        return "등록된 기본 피부 정보 없음"

    chronic_symptoms = ", ".join(s.symptom for s in profile.symptoms.all()) or "없음"
    problem_areas = ", ".join(a.area for a in profile.areas.all()) or "특정 없음"

    return f"""
- 피부 타입: {profile.skin_type}
- 평소 반복적으로 겪는 증상: {chronic_symptoms}
- 증상이 주로 나타나는 부위: {problem_areas}
"""


def find_before_after_skin_records(swim_record):
    """
    같은 SwimRecord(수영 세션)에 속한 수영 전/후 SkinRecord를 각각 찾음.
    한 시점(before/after)에 증상 타입별로 여러 SkinRecord가 있을 수 있음(가려움/붉음/트러블 등 동시 기록).
    """
    before_records = list(swim_record.skin_records.filter(timing="before"))
    after_records = list(swim_record.skin_records.filter(timing="after"))
    return before_records, after_records


def _representative_photo(records):
    """같은 시점(before/after)의 SkinRecord들 중 사진이 첨부된 첫 번째 것을 대표 사진으로 사용"""
    for record in records:
        if record.photo:
            return record.photo
    return None


def call_gpt_pattern_analysis(user, before_records, after_records):
    """
    photo_url이 외부에서 접근 가능한 URL이라는 전제로, base64 인코딩 없이 URL을 그대로 전달합니다.
    """
    skin_profile_text = _build_skin_profile_text(user)

    before_photo = _representative_photo(before_records)
    after_photo = _representative_photo(after_records)
    if not before_photo or not after_photo:
        raise ValueError("수영 전/후 사진이 첨부된 기록을 찾을 수 없습니다.")

    prompt_text = f"""
아래 두 장의 사진은 같은 사용자의 수영 전(첫 번째)과 수영 후(두 번째) 얼굴 사진이야.
두 사진을 비교해서 피부에 어떤 패턴의 변화가 나타났는지 판단해줘.

[사용자 기본 피부 정보 (참고용, 평소 상태)]
{skin_profile_text}

[판단 기준]
- patternTypes: 사진에서 관찰되는 변화를 아래 유형 중 해당하는 것 전부 선택 (복수 가능)
  redness_type(붉음), dry_tight_type(건조·당김), itch_type(가려움 반응),
  trouble_type(트러블/돌기), normal(이상 없음), need_expert(육안 판단이 어려워 전문가 확인 필요)
- patternDescription: 수영 전후 사진에서 실제로 눈에 보이는 변화를 한두 문장으로 구체적으로 설명해줘.
- 증상의 강도(숫자)는 판단하지 않아도 돼. 이건 사용자가 직접 입력한 값을 따로 쓸 거야.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": before_photo.url}},
                    {"type": "image_url", "image_url": {"url": after_photo.url}},
                ],
            }
        ],
        response_format={"type": "json_schema", "json_schema": SKIN_PATTERN_SCHEMA},
    )
    return json.loads(response.choices[0].message.content)


def build_symptom_changes(before_records, after_records):
    """
    같은 timing 안에서 symptom_type별로 SkinRecord가 하나씩 있다는 전제로,
    before/after 양쪽에 다 있는 symptom_type만 비교 대상으로 삼음(예: 가려움/붉음/트러블 동시 비교).
    """
    before_map = {r.symptom_type: r.symptom_level for r in before_records}
    after_map = {r.symptom_type: r.symptom_level for r in after_records}

    common_types = set(before_map) & set(after_map)
    return [
        {
            "symptomType": symptom_type,
            "before": before_map[symptom_type],
            "after": after_map[symptom_type],
        }
        for symptom_type in sorted(common_types)
    ]


def calculate_four_week_trend(user, symptom_type, today=None):
    today = today or timezone.now()
    four_weeks_ago = today - timedelta(weeks=4)
    two_weeks_ago = today - timedelta(weeks=2)

    past_analyses = Analysis.objects.filter(
        user=user, created_at__gte=four_weeks_ago, created_at__lte=today
    ).order_by("created_at")

    scores = []
    for analysis in past_analyses:
        for change in analysis.symptom_changes:
            if change["symptomType"] == symptom_type:
                scores.append((analysis.created_at, change["after"]))

    if not scores:
        return "no_record"

    older_half = [s for dt, s in scores if dt < two_weeks_ago]
    recent_half = [s for dt, s in scores if dt >= two_weeks_ago]

    if older_half and recent_half:
        diff = (sum(recent_half) / len(recent_half)) - (sum(older_half) / len(older_half))
    else:
        diff = scores[-1][1] - scores[0][1]

    if diff >= 1:
        return "worsened"
    elif diff <= -1:
        return "improved"
    return "maintained"


def build_four_week_trend(user, symptom_changes, today=None):
    return [
        {"symptomType": c["symptomType"], "trend": calculate_four_week_trend(user, c["symptomType"], today)}
        for c in symptom_changes
    ]


def determine_clinic_recommendation(user, symptom_changes, today=None):
    """
    기능명세서 기준 트리거 2가지만 판단:
    1) 얼굴 사진에서 수영 전후 차이가 심함 (before-after 차이 3점 이상)
    2) 증상 점수가 연속 3회 이상 '상'(HIGH=5)으로 측정됨
    """
    today = today or timezone.now()

    # 1) 사진 기반: 이번 분석에서 before/after 차이가 3점 이상인 증상이 있는지
    for change in symptom_changes:
        if change["after"] - change["before"] >= 3:
            return True, Analysis.TriggerReason.PHOTO_DIFF_SEVERE

    # 2) 증상 점수 연속 3회 이상 '상'(HIGH) 측정 — 동일 증상 기준, 최근 3개 분석 확인
    for change in symptom_changes:
        symptom_type = change["symptomType"]
        recent_three = (
            Analysis.objects.filter(user=user, created_at__lte=today)
            .order_by("-created_at")[:3]
        )
        after_scores = []
        for a in recent_three:
            for c in a.symptom_changes:
                if c["symptomType"] == symptom_type:
                    after_scores.append(c["after"])
                    break
        if len(after_scores) == 3 and all(score == 5 for score in after_scores):  # 5 = HIGH
            return True, Analysis.TriggerReason.SCORE_STREAK

    return False, None


def run_skin_analysis(user, swim_record):
    """
    swim_record: 분석 대상 SwimRecord(수영 세션) 인스턴스.
    view/serializer에서 이미 소유권 검증 및 전/후 기록 존재 여부를 확인했으므로 여기서 재조회하지 않는다.
    """
    before_records, after_records = find_before_after_skin_records(swim_record)
    if not before_records or not after_records:
        raise ValueError("수영 전/후 피부 기록을 찾을 수 없습니다.")

    pattern_result = call_gpt_pattern_analysis(user, before_records, after_records)
    symptom_changes = build_symptom_changes(before_records, after_records)
    four_week_trend = build_four_week_trend(user, symptom_changes)  # 2.1.2 분석화면 "과거 기록 비교" 표시용
    clinic_recommended, trigger_reason = determine_clinic_recommendation(
        user, symptom_changes
    )

    analysis = Analysis.objects.create(
        user=user,
        swim_record=swim_record,
        pattern_types=pattern_result["patternTypes"],
        pattern_description=pattern_result["patternDescription"],
        symptom_changes=symptom_changes,
        four_week_trend=four_week_trend,
        clinic_recommended=clinic_recommended,
        clinic_trigger_reason=trigger_reason,
    )
    return analysis