import json

from django.contrib.auth.models import User
from django.db import models

from datafactz.datafactz_middlewares import _thread_locals
from datafactz.models import DatafactzModel

# Create your models here.


class ToggleColumn(DatafactzModel):
    """
    ToggleColumn
    """

    user_id = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_excluded_column",
        editable=False,
    )
    path = models.CharField(max_length=256)
    excluded_columns = models.JSONField(default=list)

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", {})
        user = request.user
        self.user_id = user
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.user_id.employee_get)


class ActiveTab(DatafactzModel):
    """
    ActiveTab
    """

    path = models.CharField(max_length=256)
    tab_target = models.CharField(max_length=256)


class ActiveGroup(DatafactzModel):
    """
    ActiveGroup
    """

    path = models.CharField(max_length=256)
    group_target = models.CharField(max_length=256)
    group_by_field = models.CharField(max_length=256)


class SavedFilter(DatafactzModel):
    """
    SavedFilter
    """

    title = models.CharField(max_length=20, null=True)
    color = models.CharField(max_length=10, default="")
    is_default = models.BooleanField(default=False)
    filter = models.TextField()
    urlencode = models.TextField(default="")
    path = models.CharField(max_length=256)
    referrer = models.CharField(max_length=256, default="")

    def save(self, *args, **kwargs):
        SavedFilter.objects.filter(
            is_default=True, path=self.path, created_by=self.created_by
        ).exclude(id=self.pk).update(is_default=False)
        return super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.title)


class ActiveView(DatafactzModel):
    """
    This model to store the active view type for HNV
    """

    path = models.CharField(max_length=256)
    type = models.CharField(max_length=50)

    def save(self, *args, **kwargs):
        return super().save(*args, **kwargs)
