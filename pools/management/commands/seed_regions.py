"""
사용법:
    python manage.py seed_regions --file 법정동코드_전체자료.txt

원본 데이터: 행정표준코드관리시스템 "법정동코드 전체자료"
파일 형식 (탭 구분, CP949 인코딩):
    법정동코드	법정동명	폐지여부
    1100000000	서울특별시	존재
    1111000000	서울특별시 종로구	존재
    1111010100	서울특별시 종로구 청운동	존재

- 폐지여부가 "존재"인 행만 사용합니다.
- 법정동명은 공백으로 시/도·시/군구·동이 합쳐져 있어서, 토큰 개수로 레벨을 판단합니다.
    1개 토큰 → 시/도 (예: "서울특별시")
    2개 토큰 → 시/군구 (예: "서울특별시 종로구")
    3개 토큰 → 읍/면/동 (예: "서울특별시 종로구 청운동")
    4개 이상 → 시/군구가 여러 단어인 경우 (예: "경기도 고양시 덕양구 화정동")
              첫 토큰=시/도, 마지막 토큰=동, 중간 전부=시/군구로 합쳐서 처리
- 기본적으로 서울특별시만 등록합니다. 다른 지역도 필요하면 --sido 옵션에 쉼표로 추가하세요.
"""

import csv

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from pools.models import Region


class Command(BaseCommand):
    help = "법정동코드 전체자료(txt)로 시/도-시/군구-읍/면/동 Region 데이터를 일괄 등록합니다."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True, help="법정동코드 전체자료 txt 파일 경로")
        parser.add_argument(
            "--sido",
            type=str,
            default="서울특별시",
            help="등록할 시/도 이름 (쉼표로 여러 개 가능, 기본값: 서울특별시). 전체 등록하려면 --sido all",
        )
        parser.add_argument(
            "--encoding", type=str, default="cp949", help="파일 인코딩 (기본값 cp949)"
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="실제로 저장하지 않고 몇 건 생성될지만 미리 확인"
        )

    def handle(self, *args, **options):
        file_path = options["file"]
        encoding = options["encoding"]
        dry_run = options["dry_run"]
        sido_filter = None if options["sido"] == "all" else set(options["sido"].split(","))

        try:
            with open(file_path, encoding=encoding) as f:
                reader = csv.DictReader(f, delimiter="\t")
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {file_path}")
        except UnicodeDecodeError:
            raise CommandError(
                f"'{encoding}' 인코딩으로 읽는 데 실패했습니다. --encoding utf-8 등으로 다시 시도해보세요."
            )

        required_cols = {"법정동코드", "법정동명", "폐지여부"}
        if not rows or required_cols - set(rows[0].keys()):
            raise CommandError(f"필요한 컬럼이 없습니다. 실제 컬럼: {list(rows[0].keys()) if rows else '없음'}")

        # 존재하는 행만, 필요하면 시/도로 필터링
        active_rows = [r for r in rows if r["폐지여부"].strip() == "존재"]
        if sido_filter:
            active_rows = [
                r for r in active_rows if r["법정동명"].split()[0] in sido_filter
            ]

        # 토큰 개수(레벨) 오름차순으로 처리해야 부모가 먼저 생성됨 (시/도 → 시/군구 → 동)
        active_rows.sort(key=lambda r: len(r["법정동명"].split()))

        created_counts = {"sido": 0, "sigungu": 0, "dong": 0}
        skipped_counts = {"sido": 0, "sigungu": 0, "dong": 0}
        sido_cache = {}
        sigungu_cache = {}

        with transaction.atomic():
            for row in active_rows:
                tokens = row["법정동명"].split()

                if len(tokens) == 1:
                    sido_name = tokens[0]
                    obj, created = Region.objects.get_or_create(
                        name=sido_name, level=Region.Level.SIDO, parent=None
                    )
                    sido_cache[sido_name] = obj
                    created_counts["sido"] += int(created)
                    skipped_counts["sido"] += int(not created)

                elif len(tokens) == 2:
                    sido_name, sigungu_name = tokens
                    sido_obj = sido_cache.get(sido_name)
                    if sido_obj is None:
                        # 시/도 단독 행이 파일에 없었을 경우를 대비한 안전장치
                        sido_obj, _ = Region.objects.get_or_create(
                            name=sido_name, level=Region.Level.SIDO, parent=None
                        )
                        sido_cache[sido_name] = sido_obj

                    obj, created = Region.objects.get_or_create(
                        name=sigungu_name, level=Region.Level.SIGUNGU, parent=sido_obj
                    )
                    sigungu_cache[(sido_name, sigungu_name)] = obj
                    created_counts["sigungu"] += int(created)
                    skipped_counts["sigungu"] += int(not created)

                elif len(tokens) >= 3:
                    sido_name = tokens[0]
                    dong_name = tokens[-1]
                    sigungu_name = " ".join(tokens[1:-1])  # 3토큰이면 가운데 1개, 4토큰 이상이면 여러 개 합침

                    sigungu_key = (sido_name, sigungu_name)
                    sigungu_obj = sigungu_cache.get(sigungu_key)
                    if sigungu_obj is None:
                        sido_obj = sido_cache.get(sido_name)
                        if sido_obj is None:
                            sido_obj, _ = Region.objects.get_or_create(
                                name=sido_name, level=Region.Level.SIDO, parent=None
                            )
                            sido_cache[sido_name] = sido_obj
                        sigungu_obj, _ = Region.objects.get_or_create(
                            name=sigungu_name, level=Region.Level.SIGUNGU, parent=sido_obj
                        )
                        sigungu_cache[sigungu_key] = sigungu_obj

                    _, created = Region.objects.get_or_create(
                        name=dong_name, level=Region.Level.DONG, parent=sigungu_obj
                    )
                    created_counts["dong"] += int(created)
                    skipped_counts["dong"] += int(not created)

            if dry_run:
                self.stdout.write(self.style.WARNING("--dry-run 모드: 실제 저장하지 않고 롤백합니다."))
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"완료! (대상: {options['sido']})"))
        self.stdout.write(f"시/도   - 생성: {created_counts['sido']}, 이미 존재: {skipped_counts['sido']}")
        self.stdout.write(f"시/군구 - 생성: {created_counts['sigungu']}, 이미 존재: {skipped_counts['sigungu']}")
        self.stdout.write(f"읍/면/동 - 생성: {created_counts['dong']}, 이미 존재: {skipped_counts['dong']}")