from django.urls import path

from .views import collaborators, default, pages, submissions, versions  # teams

urlpatterns = [
    path("upload/<int:id>", versions.upload, name="upload"),
    path(
        "download-results/<int:id>", versions.download_results, name="download-results"
    ),
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
    path(
        "submissions/<int:id>/collaborators/add",
        collaborators.add,
        name="collaborators-add",
    ),
    path(
        "submissions/<int:id>/collaborators/delete/<int:collab_id>",
        collaborators.delete,
        name="collaborators-delete",
    ),
    path("versions/<int:id>", versions.view, name="versions-view"),
    path("", pages.home, name="home"),
]
