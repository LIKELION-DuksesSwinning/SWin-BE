import base64
import json
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from openai import OpenAI

from .models import Analysis

client = OpenAI(api_key=settings.OPENAI_API_KEY)

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
            "symptomChanges": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "symptomType": {
                            "type": "string",
                            "enum": ["dryness", "tightness", "itchiness", "redness", "trouble"],
                        },
                        "before": {"type": "integer", "minimum": 1, "maximum": 5},
                        "after": {"type": "integer", "minimum": 1, "maximum": 5},
                    },
                    "required": ["symptomType", "before", "after"],
                    "additionalProperties": False,
                },
            },
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


def call_gpt_skin_analysis(user, before_symptom, after_symptom):
    before_image_url = _encode_image(before_symptom.photo)
    after_image_url = _encode_image(after_symptom.photo)
    skin_profile_text = _build_skin_profile_text(user)

    before_levels_text = (
        ", ".join(f"{k}: {v}" for k, v in before_symptom.symptom_levels.items())
        if before_symptom.symptom_levels else "기록 없음"
    )

    prompt_text = f"""
아래는 한 사용자의 기본 피부 정보와, 이번 수영 전/후 사진 및 기록이야.
기본 피부 정보를 배경 지식으로 참고하고, 이번 수영으로 인한 실제 변화는 사진과 이번 기록을 기준으로 판단해줘.

[사용자 기본 피부 정보 (온보딩 시 입력, 평소 상태)]
{skin_profile_text}
※ 이건 "평소" 상태야. 이번 분석은 어디까지나 "이번 수영 전후 변화"에 집중하되,
평소 취약한 부위/증상과 일치하는 변화가 보이면 patternDescription에 그 맥락을 반영해줘.

[이번 수영 전 기록 (사용자 입력)]
- 선택한 증상: {", ".join(before_symptom.symptom_types) or "없음"}
- 증상별 강도(사용자가 직접 매김): {before_levels_text}
- 특이사항: {before_symptom.note or "없음"}

[이번 수영 후 기록 (사용자 입력)]
- 선택한 증상: {", ".join(after_symptom.symptom_types) or "없음"}
- 특이사항: {after_symptom.note or "없음"}
※ 수영 후 강도는 사용자가 따로 입력하지 않았어. 두 번째로 첨부한 "수영 후" 사진과
선택한 증상 종류를 참고해서, 네가 직접 1(약함)~5(심함)로 판단해줘.

[분석 시 참고할 것]
- 수영 전 강도(하/중/상)는 1~2(하), 3(중), 4~5(상) 정도로 환산해서 참고하되,
사진에서 실제로 보이는 정도와 종합해서 최종 판단해줘.
- symptomChanges는 두 사진에서 공통으로 판단 가능한 증상 종류만 포함해줘.
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

    gpt_result = call_gpt_skin_analysis(user, before_symptom, after_symptom)

    four_week_trend = build_four_week_trend(user, gpt_result["symptomChanges"])
    clinic_recommended, trigger_reason = determine_clinic_recommendation(
        user, gpt_result["symptomChanges"], four_week_trend
    )

    analysis = Analysis.objects.create(
        user=user,
        swim_record=swim_record,
        pattern_types=gpt_result["patternTypes"],
        pattern_description=gpt_result["patternDescription"],
        symptom_changes=gpt_result["symptomChanges"],
        four_week_trend=four_week_trend,
        clinic_recommended=clinic_recommended,
        clinic_trigger_reason=trigger_reason,
    )
    return analysis