import asyncio
import json
import logging
import os
import tempfile
from urllib.parse import urlparse

import aiodocker
import aiodocker.containers
import fsspec
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q

from ...models import Evaluation, Version

logger = logging.getLogger()


class DockerEvaluator:
    def __init__(self):
        docker_host = os.getenv("DOCKER_HOST", "")
        self.docker = aiodocker.Docker(url=docker_host)
        self.image = settings.EVALUATOR_DOCKER_IMAGE

    async def pull_image(self):
        try:
            image_info = await self.docker.images.get(self.image)
        except aiodocker.DockerError as e:
            if e.status == 404:
                image_info = None
            else:
                raise
        if not image_info:
            await self.docker.images.pull(
                self.image, auth=settings.EVALUATOR_DOCKER_AUTH
            )
            logger.info(f"Successfully pulled Docker image: {self.image}")
        else:
            logger.info(f"Not pulling {self.image}, it already exists")

    async def start_evaluation(self, input_uri):
        await self.pull_image()

        os.makedirs(settings.SUBMISSIONS_RESULTS_DIR, exist_ok=True)
        results_dir = tempfile.mkdtemp(prefix=settings.SUBMISSIONS_RESULTS_DIR)
        results_file = os.path.join(results_dir, "output.json")
        results_uri = f"file://{results_file}"

        url_parts = urlparse(input_uri)
        assert url_parts.scheme == "file"
        input_container_path = "/input"
        output_container_path = "/output"
        # Reference to possible config we can pass in
        # https://docs.docker.com/reference/api/engine/version/v1.43/#tag/Container/operation/ContainerCreate
        host_config = {
            "Binds": settings.EVALUATOR_DOCKER_EXTRA_BINDS
            + [
                # FIXME: This is security critical code, pay attention and
                # carefully reason about this before deploying to 'production'
                f"{url_parts.path}:{input_container_path}:ro",
                f"{results_dir}:{output_container_path}:rw",
            ],
        }
        if settings.EVALUATOR_DOCKER_CONTAINER_CPU_LIMIT:
            # Replicate the 'cpus' flag to 'docker run' by using
            # the CpuPeriod of 100000 and multiplying the CPU limit by that number, as documented
            # in https://docs.docker.com/engine/containers/resource_constraints/#configure-the-default-cfs-scheduler
            host_config["CpuPeriod"] = 100000
            host_config["CpuQuota"] = int(
                settings.EVALUATOR_DOCKER_CONTAINER_CPU_LIMIT * host_config["CpuPeriod"]
            )
        if settings.EVALUATOR_DOCKER_CONTAINER_MEMORY_LIMIT:
            host_config["Memory"] = settings.EVALUATOR_DOCKER_CONTAINER_MEMORY_LIMIT
        if settings.EVALUATOR_DOCKER_DISABLE_NETWORK:
            host_config["NetworkMode"] = "none"
        container = await self.docker.containers.create(
            config={
                "Image": self.image,
                "Cmd": settings.EVALUATOR_DOCKER_CMD
                + [
                    f"{input_container_path}",
                    f"{output_container_path}/output.json",
                ],
                "HostConfig": host_config,
            }
        )

        logger.debug(f"Container created with ID: {container.id}")
        try:
            await container.start()
            logs = await container.log(stdout=True, stderr=True)
            logger.debug(f"Container logs: {logs}")
        except Exception as e:
            logger.error(f"Failed to start container: {e}")

        return {
            "container_id": container.id,
            "results_uri": results_uri,
        }

    async def is_still_running(self, state: dict) -> bool:
        container = await self.docker.containers.get(container_id=state["container_id"])
        return container["State"].get("Status") == "running"

    async def get_result(self, state: dict) -> dict:
        container = await self.docker.containers.get(container_id=state["container_id"])
        logger.debug(f"Container state: {container['State']}")

        success = (
            container["State"]["Status"] == "exited"
            and container["State"]["ExitCode"] == 0
        )
        if not success:
            return None
        with fsspec.open(state["results_uri"]) as f:
            result = json.load(f)
        # FIXME: Remove the results file here somehow
        # os.remove(results_file)
        return result


class Command(BaseCommand):
    async def start_evaluation(
        self, evaluator: DockerEvaluator, evaluation: Evaluation
    ):
        logger.info(f"starting evaluation of {evaluation.version.data_uri}")
        new_state = await evaluator.start_evaluation(evaluation.version.data_uri)
        evaluation.evaluator_state = new_state
        evaluation.status = Evaluation.Status.EVALUATING
        await evaluation.asave()

    async def process_running_evaluation(
        self, evaluator: DockerEvaluator, evaluation: Evaluation
    ):
        state = evaluation.evaluator_state
        is_still_running = await evaluator.is_still_running(state)
        if not is_still_running:
            logger.info(f"{evaluation} is completed")
            result = await evaluator.get_result(state)
            logger.debug(f"Result: {result}")
            if result is None:
                evaluation.status = Evaluation.Status.FAILED
            else:
                evaluation.status = Evaluation.Status.EVALUATED
                evaluation.result = result
            await evaluation.asave()
        else:
            logger.info(f"{evaluation} is still running")

    async def ahandle(self):
        evaluator = DockerEvaluator()
        while True:
            # Create evaluation objects when they do not exist
            versions_without_evaluations = Version.objects.filter(
                Q(status=Version.Status.UPLOADED),
                ~Exists(Evaluation.objects.filter(version=OuterRef("pk"))),
            )
            async for v in versions_without_evaluations:
                e = Evaluation(version=v)
                await e.asave()

            # Start Evaluations when they have not been started yet
            unstarted_evaluations = Evaluation.objects.select_related("version").filter(
                status=Evaluation.Status.NOT_STARTED
            )

            async for e in unstarted_evaluations:
                await self.start_evaluation(evaluator, e)

            # Check running evaluations
            running_evaluations = Evaluation.objects.select_related("version").filter(
                status=Evaluation.Status.EVALUATING
            )

            async for e in running_evaluations:
                await self.process_running_evaluation(evaluator, e)

            await asyncio.sleep(10)

    def handle(self, *args, **kwargs):
        asyncio.run(self.ahandle())
