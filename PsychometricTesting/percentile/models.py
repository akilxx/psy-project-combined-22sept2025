# percentile/models.py

from django.db import models

class VariableDistribution(models.Model):
    name = models.CharField(max_length=100, unique=True)
    distribution = models.JSONField(help_text='List of dicts with keys "score" and "frequency".')

    def __str__(self):
        return self.name
