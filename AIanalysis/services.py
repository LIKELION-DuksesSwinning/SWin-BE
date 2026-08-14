import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Analysis

client = OpenAI(api_key=settings.OPENAI_API_KEY)

LEVEL_TO_SCORE = {"LOW": 1, "MID": 3, "HIGH": 5}

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
        profile = user.userskinprofile
    except AttributeError:
        return "등록된 기본 피부 정보 없음"

    chronic_symptoms = ", ".join(s.symptom_type for s in profile.userskinsymptom_set.all()) or "없음"
    problem_areas = ", ".join(a.area_type for a in profile.userskinarea_set.all()) or "특정 없음"

    return f"""
- 피부 타입: {profile.skin_type}
- 평소 반복적으로 겪는 증상: {chronic_symptoms}
- 증상이 주로 나타나는 부위: {problem_areas}
"""


def find_before_after_records(after_record):
    """AFTER SwimRecord를 기준으로, 같은 schedule_id의 BEFORE 기록을 찾음"""
    from records.models import SwimRecord

    before_record = SwimRecord.objects.filter(
        schedule_id=after_record.schedule_id, timing="BEFORE"
    ).first()
    return before_record


def call_gpt_pattern_analysis(user, before_record, after_record):
    """
    photo_url이 외부에서 접근 가능한 URL이라는 전제로, base64 인코딩 없이 URL을 그대로 전달합니다.
    (로컬 파일 경로라면 이 부분을 다시 고쳐야 해요 — 아래 확인사항 참고)
    """
    skin_profile_text = _build_skin_profile_text(user)

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
                    {"type": "image_url", "image_url": {"url": before_record.photo.url}},
                    {"type": "image_url", "image_url": {"url": after_record.photo.url}},
                ],
            }
        ],
        response_format={"type": "json_schema", "json_schema": SKIN_PATTERN_SCHEMA},
    )
    return json.loads(response.choices[0].message.content)


def build_symptom_changes(before_record, after_record):
    """
    증상 하나당 행이 하나씩인 구조 반영.
    related_name을 가정하지 않고 SwimRecordSymptom을 직접 필터링해서 조회.
    symptom_type이 before/after 둘 다에 있는 것만 비교 대상으로 삼음.
    """
    from records.models import SwimRecordSymptom 

    before_symptoms = SwimRecordSymptom.objects.filter(swim_record=before_record)
    after_symptoms = SwimRecordSymptom.objects.filter(swim_record=after_record)

    before_map = {s.symptom_type: s.score for s in before_symptoms}
    after_map = {s.symptom_type: s.score for s in after_symptoms}

    common_types = set(before_map) & set(after_map)
    changes = []
    for symptom_type in sorted(common_types):
        before_level = before_map[symptom_type]
        after_level = after_map[symptom_type]
        if before_level not in LEVEL_TO_SCORE or after_level not in LEVEL_TO_SCORE:
            continue  # intensity 값이 예상 형식(LOW/MID/HIGH)이 아니면 건너뜀
        changes.append({
            "symptomType": symptom_type,
            "before": LEVEL_TO_SCORE[before_level],
            "after": LEVEL_TO_SCORE[after_level],
        })
    return changes


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


def run_skin_analysis(user, swim_record_id):
    """
    swim_record_id: '수영 후(AFTER)' SwimRecord의 id.
    ERD상 Analysis가 SwimRecord와 (1:N)으로 직접 연결되는 구조라,
    이 AFTER 기록을 기준(FK)으로 삼고 짝이 되는 BEFORE 기록은 schedule_id로 내부에서 찾음.
    """
    from records.models import SwimRecord

    after_record = SwimRecord.objects.get(id=swim_record_id, user=user, timing="AFTER")
    before_record = find_before_after_records(after_record)
    if not before_record:
        raise ValueError("짝이 되는 수영 전(BEFORE) 기록을 찾을 수 없습니다.")

    pattern_result = call_gpt_pattern_analysis(user, before_record, after_record)
    symptom_changes = build_symptom_changes(before_record, after_record)
    four_week_trend = build_four_week_trend(user, symptom_changes)  # 2.1.2 분석화면 "과거 기록 비교" 표시용
    clinic_recommended, trigger_reason = determine_clinic_recommendation(
        user, symptom_changes
    )

    analysis = Analysis.objects.create(
        user=user,
        swim_record=after_record,
        before_record=before_record,  # 추적용으로 추가 보관
        pattern_types=pattern_result["patternTypes"],
        pattern_description=pattern_result["patternDescription"],
        symptom_changes=symptom_changes,
        four_week_trend=four_week_trend,
        clinic_recommended=clinic_recommended,
        clinic_trigger_reason=trigger_reason,
    )
    return analysis