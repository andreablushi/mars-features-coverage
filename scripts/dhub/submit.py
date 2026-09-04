"""Registering a version of the pipeline on DigitalHub, and starting it."""

from __future__ import annotations

import tomllib

import digitalhub as dh

import analysis.utils.settings as settings
import utils.disk.paths as paths
from dhub import configs

COMPLETED = "COMPLETED"


def submitted(half: str, handler: str, ref: str, **parameters) -> int:
    """Register a version of one half from a pushed commit, and run it.

    Args:
        half: Which half to submit, naming the function it is registered as.
        handler: The dotted path the platform imports and calls.
        ref: The branch, tag, or commit the platform clones.
        **parameters: What the handler is called with on the platform.

    Returns:
        A process exit code, non zero when the image did not build.
    """
    platform = configs.load()
    # The image is built from the repo's own dependencies, so it cannot drift
    manifest = (paths.REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    needs = tomllib.loads(manifest)["project"]["dependencies"] + platform.image_extras
    project = dh.get_or_create_project(platform.project)
    function = project.new_function(
        name=platform.functions[half],
        kind="python",
        python_version=platform.python_version,
        code_src=f"git+{platform.repository}#{ref}",
        handler=handler,
        requirements=needs,
    )

    # Build the image first, since the job cannot install anything itself.
    built = function.run(action="build", wait=True)
    if built.status.state != COMPLETED:
        print(f"the image did not build: {built.status.state}")
        return 1
    function.refresh()

    # Start the job on the built image, telling it where the clone lands. The
    # cores it is given are the jobs it runs at once, however the config reads
    cores = int(platform.cpu or settings.load().workers)
    root = platform.source_root
    run = function.run(
        action="job",
        resources={"cpu": str(cores), "mem": platform.memory, "disk": platform.disk},
        envs=[{"name": "PYTHONPATH", "value": f"{root}:{root}/src:{root}/scripts"}],
        parameters=parameters | {"workers": cores},
        wait=False,
    )
    print(run.key)
    return 0
