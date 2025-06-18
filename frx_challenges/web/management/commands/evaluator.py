import asyncio
import collections.abc
import json
import logging
import os
import tempfile
from typing import Optional
from urllib.parse import urlparse

import aiodocker
import aiodocker.containers
import fsspec
from django.conf import settings
from django.core.management.base import BaseCommand
from web.utils import recursive_update

from ...models import Evaluation

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
            logger.info(f"Starting to pull Docker image: {self.image}")
            await self.docker.images.pull(
                self.image, auth=settings.EVALUATOR_DOCKER_AUTH
            )
            logger.info(f"Successfully pulled Docker image: {self.image}")
        else:
            logger.info(f"Not pulling {self.image}, it already exists")

    async def start_evaluation(self, input_uri):

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
        cmd = [
            c.format(
                submission_path=input_container_path,
                result_path=f"{output_container_path}/output.json",
            )
            for c in settings.EVALUATOR_DOCKER_CMD
        ]

        if settings.EVALUATOR_DOCKER_EXTRA_HOST_CONFIG:
            recursive_update(host_config, settings.EVALUATOR_DOCKER_EXTRA_HOST_CONFIG)

        config = {
            "Image": self.image,
            "Cmd": cmd,
            "HostConfig": host_config,
        }

        if settings.EVALUATOR_DOCKER_CONTAINER_ENV:
            if isinstance(
                settings.EVALUATOR_DOCKER_CONTAINER_ENV, collections.abc.Mapping
            ):
                config["Env"] = [
                    f"{k}={v}"
                    for k, v in settings.EVALUATOR_DOCKER_CONTAINER_ENV.items()
                ]
            elif isinstance(settings.EVALUATOR_DOCKER_CONTAINER_ENV, list):
                config["Env"] = settings.EVALUATOR_DOCKER_CONTAINER_ENV
            else:
                raise RuntimeError(
                    f"settings.EVALUATOR_DOCKER_CONTAINER_ENV should be a dict or list, found {type( settings.EVALUATOR_DOCKER_CONTAINER_ENV)}"
                )

        container = await self.docker.containers.create(config)

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
            "command": cmd,
            "image": self.image,
        }

    async def is_still_running(self, state: dict) -> bool:
        try:
            container = await self.docker.containers.get(
                container_id=state["container_id"]
            )
        except aiodocker.DockerError as e:
            if e.status == 404:
                return False
            raise

        return container["State"].get("Status") == "running"

    async def get_logs(self, state: dict) -> Optional[str]:
        try:
            container = await self.docker.containers.get(
                container_id=state["container_id"]
            )
        except aiodocker.DockerError as e:
            if e.status == 404:
                return None
            raise
        return "".join(await container.log(stdout=True, stderr=True, follow=False))

    async def get_result(self, state: dict) -> Optional[dict]:
        try:
            container = await self.docker.containers.get(
                container_id=state["container_id"]
            )
        except aiodocker.DockerError as e:
            if e.status == 404:
                return None
            raise

        logger.debug(f"Container state: {container['State']}")

        try:
            with fsspec.open(state["results_uri"]) as f:
                result = json.load(f)
            return result
        except FileNotFoundError:
            if container["State"]["Status"] != "exited":
                logger.warning(
                    f"Container {state['container_id']} is still running, results file not available yet."
                )
            elif container["State"]["Status"] == "exited":
                if container["State"]["ExitCode"] != 0:
                    logger.error(
                        f"Container {state['container_id']} exited with non-zero exit code: {container['State']['ExitCode']}"
                    )
                logger.error(f"Results file not found: {state['results_uri']}")
            return None


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
        result = await evaluator.get_result(state)
        if not is_still_running:
            logger.info(f"{evaluation} is completed")
            logger.debug(f"Result: {result}")
            evaluation.evaluator_logs = await evaluator.get_logs(state)
            if result is None:
                evaluation.status = Evaluation.Status.FAILED
            else:
                evaluation.status = Evaluation.Status.EVALUATED
                evaluation.result = result
            await evaluation.asave()
        else:
            if result is not None:
                evaluation.result = result
                await evaluation.asave()
            logger.info(f"{evaluation} is still running")

    async def ahandle(self):
        evaluator = DockerEvaluator()
        # Pull image if needed when the evaluator starts
        await evaluator.pull_image()
        while True:
            # Get the Evaluations that have not been started yet
            unstarted_evaluations = Evaluation.objects.select_related("version").filter(
                status=Evaluation.Status.NOT_STARTED
            )

            # Get the running Evaluation objects
            running_evaluations = Evaluation.objects.select_related("version").filter(
                status=Evaluation.Status.EVALUATING
            )

            # Get the number of running evaluations
            # This is a synchronous operation so it's wrapped in sync_to_async
            num = await running_evaluations.acount()
            async for e in unstarted_evaluations:
                # Only start a new evaluation if the number of running evaluations is less than the maximum
                if num < settings.MAX_RUNNING_EVALUATIONS:
                    await self.start_evaluation(evaluator, e)
                    # Instead of checking the database again, we can just increment the counter
                    # And the database will be checked in the next iteration
                    num += 1
                else:
                    logger.warning(
                        "Maximum number of running evaluations reached, waiting for some to finish"
                    )

            async for e in running_evaluations:
                await self.process_running_evaluation(evaluator, e)

            await asyncio.sleep(10)

    def handle(self, *args, **kwargs):
        asyncio.run(self.ahandle())
