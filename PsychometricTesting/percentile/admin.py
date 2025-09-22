# percentile/admin.py

from django.contrib import admin
from .models import VariableDistribution

@admin.register(VariableDistribution)
class VariableDistributionAdmin(admin.ModelAdmin):
    list_display = ('name',)
