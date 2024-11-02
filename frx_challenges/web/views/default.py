import os
import tempfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse
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


def leaderboard(request: HttpRequest) -> HttpResponse:
    if settings.CHALLENGE_STATE != "RUNNING":
        return HttpResponse(
            "Challenge hasn't started, so leaderboard is not available", status=400
        )

    sorted_display_config = sorted(
        settings.EVALUATION_DISPLAY_CONFIG, key=lambda dc: -dc["ordering_priority"]
    )
    results = []
    all_submissions = Submission.objects.all()
    for sub in all_submissions:
        bv = sub.best_version
        if not bv:
            # Only display submissions with at least one 'best version'
            continue
        results.append({"submission": sub, "best_version": bv})

    def sort_key_func(r):
        bv: Version = r["best_version"]
        sort_key = []
        for dc in sorted_display_config:
            if dc["ordering"] == "smaller_is_better":
                sort_key.append(-bv.latest_evaluation.result[dc["result_key"]])
            elif dc["ordering"] == "bigger_is_better":
                sort_key.append(bv.latest_evaluation.result[dc["result_key"]])
            else:
                raise ValueError(
                    f"Invalid ordering {dc['ordering']} found for result_key {dc['result_key']}"
                )

        return sort_key

    results = sorted(results, key=sort_key_func)
    return render(request, "results.html", {"results": results})
