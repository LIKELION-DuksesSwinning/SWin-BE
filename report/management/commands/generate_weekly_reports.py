"""
사용법:
    python manage.py generate_weekly_reports [--week-start YYYY-MM-DD]

week_start를 지정하지 않으면 오늘이 속한 주의 월요일을 기준으로 계산한다.
보통 Celery beat나 crontab 등 외부 스케줄러가 매주 월요일 새벽에 이 커맨드를 호출하는 방식으로 사용한다.
그 주에 AI 피부 분석(Analysis) 기록이 있는 사용자만 대상으로 리포트/루틴을 생성한다.
"""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from AIanalysis.models import Analysis
from report.services import generate_routine_recommendation, generate_weekly_report


class Command(BaseCommand):
    help = "지난 한 주(월요일 시작)에 대해 사용자별 주간 리포트와 루틴 추천을 생성한다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--week-start",
            type=str,
            default=None,
            help="YYYY-MM-DD 형식. 미지정 시 이번 주 월요일을 기준으로 계산.",
        )

    def handle(self, *args, **options):
        if options["week_start"]:
            week_start = date.fromisoformat(options["week_start"])
        else:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        User = get_user_model()
        user_ids = (
            Analysis.objects.filter(created_at__date__gte=week_start, created_at__date__lte=week_end)
            .values_list("user_id", flat=True)
            .distinct()
        )

        count = 0
        for user in User.objects.filter(id__in=user_ids):
            weekly_report = generate_weekly_report(user, week_start, week_end)
            generate_routine_recommendation(weekly_report, user)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"{week_start} ~ {week_end}: {count}명 사용자 주간 리포트 생성 완료")
        )
