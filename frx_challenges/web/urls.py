from django.urls import path

from .views import collaborators, default, pages, submissions, versions  # teams

urlpatterns = [
    path("upload/<int:id>", versions.upload, name="upload"),
    path("page/<slug:slug>", pages.view, name="page-view"),
    path("file/<slug:slug>", pages.content_file, name="content-file"),
    path("leaderboard", default.leaderboard, name="leaderboard"),
    path("submissions/", submissions.list, name="submissions-list"),
    path("submissions/create", submissions.create, name="submissions-create"),
    path("submissions/<int:id>", submissions.detail, name="submissions-detail"),
    path("submissions/<int:id>/edit", submissions.edit, name="submissions-edit"),
    path(
        "submissions/<int:id>/collaborators",
        collaborators.list,
        name="collaborators-list",
    ),
    path("versions/<int:id>", versions.view, name="versions-view"),
    path(
        "evaluation/<int:id>", submissions.detail_evaluation, name="evaluation-detail"
    ),
    path("", pages.home, name="home"),
]
