from django.apps import AppConfig


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leave"

    def ready(self):
        from django.urls import include, path

        from datafactz.urls import urlpatterns
        from leave import scheduler

        urlpatterns.append(
            path("leave/", include("leave.urls")),
        )
        super().ready()
