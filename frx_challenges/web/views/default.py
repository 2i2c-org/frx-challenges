import os
import tempfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.front_matter import front_matter_plugin

from ..forms import UploadForm
from ..models import Evaluation, Submission, Version


@login_required
def upload(request: HttpRequest, id: int) -> HttpResponse:
    if request.method == "POST":
        form = UploadForm(data=request.POST, files=request.FILES, id=id)
        if form.is_valid():
            # FIXME: We are creating the uploads directory on first use if
            # necessary. This may be a security risk, let's verify.
            os.makedirs(settings.SUBMISSIONS_UPLOADS_DIR, exist_ok=True)
            _, filepath = tempfile.mkstemp(prefix=settings.SUBMISSIONS_UPLOADS_DIR)
            with open(filepath, "wb") as f:
                f.write(request.FILES["file"].read())
            with transaction.atomic():
                v = Version(
                    submission=Submission.objects.get(id=id),
                    user=request.user,
                    status=Version.Status.UPLOADED,
                    filename=request.FILES["file"].name,
                    data_uri=f"file:///{filepath}",
                )
                v.save()

                # Make sure every version has at least one evaluation
                # by default, even if it has not been started
                e = Evaluation(version=v)
                e.save()
            return redirect("submissions-detail", id)
    else:
        form = UploadForm(id=id)
    md = (
        MarkdownIt("commonmark", {"breaks": True, "html": True})
        .use(front_matter_plugin)
        .use(footnote_plugin)
        .enable("table")
    )
    html_content = md.render(settings.SITE_SUBMISSION_INSTRUCTIONS_MARKDOWN)
    return render(
        request, "upload.html", {"form": form, "id": id, "html_content": html_content}
    )


def results(request: HttpRequest) -> HttpResponse:
    evaluations = Evaluation.objects.all()

    evaluations_resp = {
        "display_config": settings.EVALUATION_DISPLAY_CONFIG,
        "results": [],
    }

    for ev in evaluations:
        evaluations_resp["results"].append(
            {
                "evaluation_id": ev.id,
                "username": ev.version.user.username,
                "status": ev.status,
                "last_updated": ev.last_updated.isoformat(),
                "result": ev.result,
            }
        )

    return JsonResponse(evaluations_resp)


def leaderboard(request: HttpRequest) -> HttpResponse:
    if settings.CHALLENGE_STATE != "RUNNING":
        return HttpResponse(
            "Challenge hasn't started, so leaderboard is not available", status=400
        )

    return render(request, "results.html")
