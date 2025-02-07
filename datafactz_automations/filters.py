"""
datafactz_automations/filters.py
"""

from datafactz.filters import DatafactzFilterSet, django_filters
from datafactz_automations.models import MailAutomation


class AutomationFilter(DatafactzFilterSet):
    """
    AutomationFilter
    """

    search = django_filters.CharFilter(field_name="title", lookup_expr="icontains")

    class Meta:
        model = MailAutomation
        fields = "__all__"
