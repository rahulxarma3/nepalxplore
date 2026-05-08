from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("api/", views.api_docs, name="api_docs"),
    path("notifications/", views.notifications_list, name="notifications"),
    path("notifications/count/", views.notifications_count, name="notifications_count"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="notification_read"),
]
