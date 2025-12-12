import json
import os
import tempfile

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from ..forms import UploadForm
from ..md import MARKDOWN_RENDERER
from ..models import Collaborator, Evaluation, Submission, Version


@login_required
def upload(request: HttpRequest, id: int) -> HttpResponse:
    is_collaborator = _validate_collaborator(request, id)
    if not is_collaborator:
        raise Http404("Uploads are only available to submission collaborators.")
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
            return redirect("versions-view", v.id)
    else:
        form = UploadForm(id=id)
    html_content = MARKDOWN_RENDERER.render(
        settings.SITE_SUBMISSION_INSTRUCTIONS_MARKDOWN
    )
    return render(
        request, "upload.html", {"form": form, "id": id, "html_content": html_content}
    )


@login_required
def download_results(request: HttpRequest, id: int) -> HttpResponse:
    version = Version.objects.get(id=id)
    is_collaborator = _validate_collaborator(request, id)
    if not is_collaborator:
        raise Http404(
            "Full results files are only available to submission collaborators."
        )
    evaluation = version.latest_evaluation
    if not evaluation.result:
        raise Http404("No results available for this version.")

    # Create a JSON response from the evaluation results
    response = HttpResponse(
        content_type="application/json",
    )
    response["Content-Disposition"] = f'attachment; filename="results_{id}.json"'

    response.write(json.dumps(evaluation.result, indent=4))
    return response


def view(request: HttpRequest, id: int) -> HttpResponse:
    version = Version.objects.get(id=id)
    evaluation = version.latest_evaluation
    is_collaborator = _validate_collaborator(request, id)

    results_display = []
    if evaluation.result:
        for dc in settings.EVALUATION_DISPLAY_CONFIG:
            results_display.append(
                {
                    "display_name": dc["display_name"],
                    "value": evaluation.result.get(dc["result_key"]),
                }
            )

    return render(
        request,
        "version.html",
        {
            "version": version,
            "evaluation": evaluation,
            "results_display": results_display,
            "is_collaborator": is_collaborator,
        },
    )


def _validate_collaborator(request: HttpRequest, id: int):
    """
    Validate that the user is a collaborator of the submission.
    """
    try:
        Collaborator.objects.get(submission_id=id, user=request.user)
        is_collaborator = True
    except Collaborator.DoesNotExist:
        is_collaborator = False
    return is_collaborator
