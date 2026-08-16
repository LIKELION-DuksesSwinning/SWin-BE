"""
사용법:
    python manage.py seed_pools --file 서울시_수영장업_인허가_정보.csv --dry-run

실제 컬럼 기준(서울 열린데이터광장 "수영장업 인허가 정보"):
    사업장명, 도로명주소, 지번주소, 전화번호, 영업상태명, ...

동 추출 규칙:
    1순위) 도로명주소 끝 괄호 안 첫 항목  예: "...(자양동, 자양7차우성아파트)" → 자양동
    2순위) 도로명주소가 비어있거나 괄호가 없으면, 지번주소에서 "구" 다음 토큰을 동으로 사용
           예: "서울특별시 중구 정동 1-76" → 정동
"""

import csv
import re

from django.core.management.base import BaseCommand, CommandError

from pools.models import Pool, Region  # 실제 경로에 맞게 조정

DONG_IN_PARENS = re.compile(r"\(([^)]+)\)")
DISTRICT_PATTERN = re.compile(r"(\S+구)\s")
DONG_AFTER_DISTRICT = re.compile(r"\S+구\s+(\S+동)")


def extract_district(address: str):
    match = DISTRICT_PATTERN.search(address)
    return match.group(1) if match else None


def extract_dong(road_address: str, jibun_address: str):
    # 1순위: 도로명주소 괄호 안
    if road_address:
        matches = DONG_IN_PARENS.findall(road_address)
        if matches:
            candidate = matches[-1].split(",")[0].strip()
            if candidate:
                return candidate

    # 2순위: 지번주소에서 "구" 바로 다음 "동" 토큰
    if jibun_address:
        match = DONG_AFTER_DISTRICT.search(jibun_address)
        if match:
            return match.group(1)

    return None


class Command(BaseCommand):
    help = "서울시 수영장업 인허가 정보 CSV로 Pool 데이터를 일괄 등록합니다."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True)
        parser.add_argument("--encoding", type=str, default="cp949")
        parser.add_argument(
            "--status-value", type=str, default="영업/정상",
            help="이 값과 일치하는 행만 등록. 전체 등록하려면 --status-value all"
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        file_path = options["file"]
        encoding = options["encoding"]
        status_value = options["status_value"]
        dry_run = options["dry_run"]

        try:
            with open(file_path, encoding=encoding) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"파일을 찾을 수 없습니다: {file_path}")
        except UnicodeDecodeError:
            raise CommandError(f"'{encoding}' 인코딩으로 읽기 실패. --encoding utf-8 등으로 재시도해보세요.")

        if not rows:
            raise CommandError("CSV에 데이터가 없습니다.")

        if status_value != "all":
            rows = [r for r in rows if r.get("영업상태명", "").strip() == status_value]

        created, skipped, no_dong_match = 0, 0, []

        for row in rows:
            name = row.get("사업장명", "").strip()
            road_address = row.get("도로명주소", "").strip()
            jibun_address = row.get("지번주소", "").strip()
            address = road_address or jibun_address

            if not name or not address:
                continue

            dong_name = extract_dong(road_address, jibun_address)
            district_name = extract_district(address)

            dong = None
            if dong_name:
                qs = Region.objects.filter(name=dong_name, level=Region.Level.DONG)
                if district_name:
                    qs = qs.filter(parent__name=district_name)
                dong = qs.first()

            if not dong:
                no_dong_match.append(f"{name} (동: {dong_name}, 구: {district_name}, 주소: {address})")

            if dry_run:
                created += 1
                continue

            _, was_created = Pool.objects.get_or_create(
                name=name, address=address, defaults={"dong": dong}
            )
            if was_created:
                created += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(f"완료! 생성: {created}, 이미 존재: {skipped}"))
        if no_dong_match:
            self.stdout.write(self.style.WARNING(f"동 매칭 실패 ({len(no_dong_match)}건, dong=None으로 저장됨):"))
            for item in no_dong_match:
                self.stdout.write(f"  - {item}")