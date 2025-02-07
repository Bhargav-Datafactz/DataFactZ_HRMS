from django.urls import include, path

urlpatterns = [
    path("auth/", include("datafactz_api.api_urls.auth.urls")),
    path("asset/", include("datafactz_api.api_urls.asset.urls")),
    path("base/", include("datafactz_api.api_urls.base.urls")),
    path("employee/", include("datafactz_api.api_urls.employee.urls")),
    path("notifications/", include("datafactz_api.api_urls.notifications.urls")),
    path("payroll/", include("datafactz_api.api_urls.payroll.urls")),
    path("attendance/", include("datafactz_api.api_urls.attendance.urls")),
    path("leave/", include("datafactz_api.api_urls.leave.urls")),
]
