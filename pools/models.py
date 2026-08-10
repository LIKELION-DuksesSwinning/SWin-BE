from django.db import models


class Pool(models.Model):
    name = models.CharField(max_length=100)
    district = models.CharField(max_length=50)
    address = models.CharField(max_length=255)

    def __str__(self):
        return self.name