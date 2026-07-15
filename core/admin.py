from django.contrib import admin
from .models import IslamicMilestone

@admin.register(IslamicMilestone)
class IslamicMilestoneAdmin(admin.ModelAdmin):
    list_display = ('event_key', 'year', 'expected_gregorian_date', 'is_visible_in_delhi', 'visibility_grade')
    list_filter = ('event_key', 'year', 'is_visible_in_delhi')
    search_fields = ('event_key',)
    ordering = ('-year',)
