from django.urls import path
from . import views

app_name = "content"

urlpatterns = [
    path("", views.feed, name="feed"),
    path("upload/", views.upload_video, name="upload_video"),
    path("video/<slug:slug>/", views.video_detail, name="video_detail"),
    path("video/<slug:slug>/progress/", views.update_progress, name="update_progress"),
]
