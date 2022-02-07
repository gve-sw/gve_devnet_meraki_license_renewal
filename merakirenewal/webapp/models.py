from django.db import models


class Log(models.Model):
    name = models.CharField(max_length=500)
    country = models.CharField(max_length=500)
    email = models.CharField(max_length=500)
    requestdate = models.CharField(max_length=500)
    requestdeadline = models.IntegerField()
    apikeys = models.CharField(max_length=5000)
    apikeysstring = models.CharField(max_length=5000)
    expiring = models.IntegerField()
    expired = models.IntegerField()
