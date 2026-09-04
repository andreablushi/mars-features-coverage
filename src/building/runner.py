"""Running a build's work: the downloads it waits on, and the crops it computes."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from rich.console import Console

import utils.disk.paths as paths
from building import build, planner
from building import console as printing
from building.download.common import client as transport
from building.download.dataset import FETCH
from building.metadata import read as metadata_read
from building.metadata import write as metadata
from building.models.job import Job, Outcome, Plan
from building.models.settings import Settings


def run_build(
    settings: Settings,
    console: Console,
    root: Path = paths.DATASET_ROOT,
    *,
    force: bool = False,
) -> list[Outcome]:
    """Fetch every product a build needs and cut each to the features that kept it.

    A download waits on the network and a crop waits on the processor, so the
    two run on pools of their own and a product is built the moment it lands.

    Args:
        settings: The settled choices for the build.
        console: The console to render on.
        root: The dataset's own root directory.
        force: Whether to rebuild crops that are already written.

    Returns:
        Every finished outcome, in completion order.

    Raises:
        FileNotFoundError: When no selection has been written to build from.
    """
    with transport.Client() as ode:
        plan = planner.build_plan(settings, ode, root, force=force)
        printing.describe(plan, settings, console)
        if not plan.jobs:
            _indexed(plan, [], root)
            return []
        with (
            ProcessPoolExecutor(max_workers=settings.workers) as building,
            ThreadPoolExecutor(max_workers=settings.workers) as fetching,
        ):
            waiting = threading.Semaphore(settings.ready)
            held = _built(plan.jobs, ode, fetching, building, root, waiting)
            with closing(held) as outcomes:
                collected = printing.render(
                    outcomes, len(plan.jobs), "building", console
                )
    _indexed(plan, collected, root)
    return collected


def _built(
    jobs: tuple[Job, ...],
    ode: transport.Client,
    fetching: ThreadPoolExecutor,
    building: ProcessPoolExecutor,
    root: Path,
    waiting: threading.Semaphore,
) -> Iterator[Outcome]:
    """Fetch every product and build it the moment it lands, in whatever order.

    A download waits on the network and a build waits on the processor, so a
    product goes to the build pool as soon as it is on disk, however many of the
    downloads planned ahead of it are still running. The jobs are still handed to
    the pool heaviest first, so what changes is which of them is waited on and
    never which of them is started.

    Downloading is the faster of the two, so it is held to the room it was given:
    a product takes a place before it comes down and gives it back once it has
    been built, which is what stops the whole archive landing on disk before the
    first crop is written.

    Args:
        jobs: The products to fetch and build, heaviest first.
        ode: The client every download is asked through.
        fetching: The threads the downloads run on.
        building: The processes the builds run on.
        root: The dataset's own root directory.
        waiting: The places a downloaded product may wait in to be built.

    Yields:
        One outcome per job, in the order they finish.
    """
    finished: queue.Queue[Outcome] = queue.Queue()

    def collect(job: Job) -> Callable[[Future[Outcome]], None]:
        """Return what to do with one job's build once the pool is done with it."""

        def collected(done: Future[Outcome]) -> None:
            """Put what the build left on the queue, and give its place back."""
            try:
                finished.put(done.result())
            except Exception as error:  # noqa: BLE001
                finished.put(Outcome(job, error=error))
            finally:
                waiting.release()

        return collected

    def land(job: Job) -> Callable[[Future[Outcome]], None]:
        """Return what to do with one job's product once it has come down."""

        def landed(done: Future[Outcome]) -> None:
            """Send a product that came down whole on to be built."""
            # Every path here leaves exactly one outcome on the queue and gives
            # back the one place it took, since a job that left neither would be
            # waited on for ever.
            try:
                outcome = done.result()
                if not outcome.failed:
                    built = building.submit(build.build, job, root)
                    built.add_done_callback(collect(job))
                    return
            except Exception as error:  # noqa: BLE001
                outcome = Outcome(job, error=error)
            finished.put(outcome)
            waiting.release()

        return landed

    for job in jobs:
        fetching.submit(_fetch, job, ode, waiting).add_done_callback(land(job))
    for _ in jobs:
        yield finished.get()


def _fetch(job: Job, ode: transport.Client, waiting: threading.Semaphore) -> Outcome:
    """Take a place on disk for one product and bring it down into it.

    The place is taken before the download rather than after, so the room a
    product is about to need is never given away to another one.

    Args:
        job: The product to fetch.
        ode: The client it is asked through.
        waiting: The places a downloaded product may wait in to be built, one of
            which is taken here and given back once the product has been built.

    Returns:
        The outcome, holding where the product landed or what stopped it.
    """
    waiting.acquire()
    try:
        return Outcome(job, landed=FETCH[job.instrument](job.identifier, ode))
    except Exception as error:  # noqa: BLE001
        return Outcome(job, error=error)


def _indexed(plan: Plan, collected: Sequence[Outcome], root: Path) -> None:
    """Write the index over every crop the dataset holds, not this run's alone.

    A build that skips what is already written would otherwise index only what
    it rewrote, so what an earlier run left is read back and carried forward.

    Args:
        plan: What the build set out to do, whose frames every feature is in.
        collected: What every job of this run left.
        root: The dataset's own root directory.

    Returns:
        None.
    """
    written = [held for one in collected for held in one.records]
    rewritten = {
        (held.feature_class, held.feature_name, held.instrument, held.identifier)
        for held in written
    }
    try:
        standing = metadata_read.read_observation_records(root)
    except FileNotFoundError:
        standing = []
    kept = [
        held
        for held in standing
        if (held.feature_class, held.feature_name, held.instrument, held.identifier)
        not in rewritten
        and (root / held.path).exists()
    ]
    metadata.write_metadata(plan.frames, kept + written, root)
