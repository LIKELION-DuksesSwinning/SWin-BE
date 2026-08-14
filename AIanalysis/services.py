import base64
import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Analysis

client = OpenAI(api_key=settings.OPENAI_API_KEY)

LEVEL_TO_SCORE = {"low": 1, "mid": 3, "high": 5}

SKIN_ANALYSIS_SCHEMA = {
    "name": "skin_analysis",
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
        "required": ["patternTypes", "patternDescription", "symptomChanges"],
        "additionalProperties": False,
    },
    "strict": True,
}


def _encode_image(photo_field):
    with photo_field.open("rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def _build_skin_profile_text(user):
    """UserSkinProfile + UserSkinSymptom + UserSkinArea를 프롬프트용 텍스트로 변환"""
    try:
        profile = user.skin_profile  # related_name="skin_profile"
    except AttributeError:
        return "등록된 기본 피부 정보 없음"

    chronic_symptoms = ", ".join(
        s.get_symptom_type_display() for s in profile.symptoms.all()
    ) or "없음" 
    problem_areas = ", ".join(
        a.get_area_type_display() for a in profile.areas.all()
    ) or "특정 없음"

    return f"""
- 피부 타입: {profile.skin_type_display}
- 평소 반복적으로 겪는 증상: {chronic_symptoms}
- 증상이 주로 나타나는 부위: {problem_areas}
"""


def call_gpt_pattern_analysis(user, before_symptom, after_symptom):
    before_image_url = _encode_image(before_symptom.photo)
    after_image_url = _encode_image(after_symptom.photo)
    skin_profile_text = _build_skin_profile_text(user)

    before_levels_text = (
        ", ".join(f"{k}: {v}" for k, v in before_symptom.symptom_levels.items())
        if before_symptom.symptom_levels else "기록 없음"
    )

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
예: "수영 후 새로 생긴 오돌토돌한 돌기, 붉은 자국이 발견됐어요"처럼 관찰된 사실 위주로.
- 증상의 강도(숫자)는 판단하지 않아도 돼. 이건 사용자가 직접 입력한 값을 따로 쓸 거야.
"""


    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt_text},
                    {"type": "image_url", "image_url": {"url": before_image_url}},
                    {"type": "image_url", "image_url": {"url": after_image_url}},
                ],
            }
        ],
        response_format={"type": "json_schema", "json_schema": SKIN_ANALYSIS_SCHEMA},
    )
    return json.loads(response.choices[0].message.content)

def build_symptom_changes(before_symptom, after_symptom):
    """사용자가 직접 입력한 하/중/상 값만으로 계산. GPT 안 씀."""
    all_types = set(before_symptom.symptom_types) | set(after_symptom.symptom_types)
    changes = []
    for symptom_type in sorted(all_types):
        before_level = before_symptom.symptom_levels.get(symptom_type)
        after_level = after_symptom.symptom_levels.get(symptom_type)
        if before_level is None or after_level is None:
            continue  # 전/후 둘 다 강도가 있어야 비교 가능
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


def determine_clinic_recommendation(user, symptom_changes, four_week_trend, today=None):
    today = today or timezone.now()

    for change in symptom_changes:
        if change["after"] - change["before"] >= 3:
            return True, Analysis.TriggerReason.PHOTO_DIFF_SEVERE

    if any(t["trend"] == "worsened" for t in four_week_trend):
        return True, Analysis.TriggerReason.RECURRING_2W

    for change in symptom_changes:
        symptom_type = change["symptomType"]
        recent_three = (
            Analysis.objects.filter(user=user, created_at__lte=today)
            .order_by("-created_at")[:3]
        )
        after_scores = []
        for a in reversed(list(recent_three)):
            for c in a.symptom_changes:
                if c["symptomType"] == symptom_type:
                    after_scores.append(c["after"])
        if len(after_scores) == 3 and after_scores[0] < after_scores[1] < after_scores[2]:
            return True, Analysis.TriggerReason.SCORE_STREAK

    # TODO: persisted_72h — SwimRecordSymptom 쪽 timestamp 기준 추적 로직 필요, 팀 논의 후 구현

    return False, None


def run_skin_analysis(user, swim_record):
    before_symptom = swim_record.symptoms.get(timing="before")
    after_symptom = swim_record.symptoms.get(timing="after")

    pattern_result = call_gpt_pattern_analysis(user, before_symptom, after_symptom)
    symptom_changes = build_symptom_changes(before_symptom, after_symptom)
    four_week_trend = build_four_week_trend(user, symptom_changes)


    clinic_recommended, trigger_reason = determine_clinic_recommendation(
user, symptom_changes, four_week_trend
    )

    analysis = Analysis.objects.create(
        user=user,
        swim_record=swim_record,
        pattern_types=pattern_result["patternTypes"],
        pattern_description=pattern_result["patternDescription"],
        symptom_changes=pattern_result["symptomChanges"],
        four_week_trend=four_week_trend,
        clinic_recommended=clinic_recommended,
        clinic_trigger_reason=trigger_reason,
    )
    return analysis