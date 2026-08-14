from django.db import models


class Pool(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.name



class Region(models.Model):
    """행정구역 (시/도, 시/군구, 읍/면/동 계층) — 3.1 수영장 찾기 드롭다운용"""

    class Level(models.TextChoices):
        SIDO = "sido", "시/도"
        SIGUNGU = "sigungu", "시/군구"
        DONG = "dong", "읍/면/동"

    name = models.CharField(max_length=50)
    level = models.CharField(max_length=10, choices=Level.choices)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )

    class Meta:
        unique_together = ("name", "level", "parent")
        ordering = ["name"]

    def __str__(self):
        return self.name
