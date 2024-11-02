from django.urls import path

from .views import default, pages, submissions, teams

urlpatterns = [
    path("upload/<int:id>", default.upload, name="upload"),
    path("teams/list", teams.list, name="teams-list"),
    path("teams/create", teams.create, name="teams-create"),
    path("teams/<int:id>", teams.view, name="teams-view"),
    path("teams/<int:id>/add-member", teams.add_member, name="teams-add-member"),
    path(
        "teams/<int:team_id>/remove-member/<int:user_id>",
        teams.remove_member,
        name="teams-remove-member",
    ),
    path("page/<slug:slug>", pages.view, name="page-view"),
    path("file/<slug:slug>", pages.content_file, name="content-file"),
    path("leaderboard", default.leaderboard, name="leaderboard"),
    path("submissions/", submissions.list, name="submissions-list"),
    path("submissions/create", submissions.create, name="submissions-create"),
    path("submissions/<int:id>", submissions.detail, name="submissions-detail"),
    path(
        "evaluation/<int:id>", submissions.detail_evaluation, name="evaluation-detail"
    ),
    path("", pages.home, name="home"),
]
