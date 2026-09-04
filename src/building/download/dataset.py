"""The download stage: bring down every product the written selection kept."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Executor, ThreadPoolExecutor, as_completed
from pathlib import Path

from analysis import dataset_list
from analysis.selector.models.selection import Selection
from building.download.common import client as transport
from building.download.crism import download as crism
from building.download.ctx import download as ctx
from building.download.models.job import Job, Outcome
from building.download.mola import download as mola
from building.download.sharad import download as sharad

# How many downloads to run at once. They wait on the network rather than the
# processor, so threads are what they are run on.
WORKERS = 16

# What reads an observation out of a product id the selection kept, for the
# instruments the selection names.
OBSERVED: dict[str, Callable[[str], str | None]] = {
    "CRISM": crism.observation_id,
    "CTX": ctx.observation_id,
    "SHARAD": sharad.observation_id,
}

# The instrument the selection can never name, whose tiles are found by the box
# of the feature that wants them.
GRIDDED = "MOLA"

# What brings one product of each instrument down, and where it landed.
FETCH: dict[str, Callable[[str, transport.Client], tuple[Path, ...]]] = {
    "CRISM": lambda held, ode: tuple(crism.fetch(held, ode).values()),
    "CTX": lambda held, ode: (ctx.fetch(held, ode),),
    "SHARAD": lambda held, ode: (sharad.fetch(held, ode),),
    GRIDDED: lambda held, ode: (mola.fetch(held, ode),),
}


def download_dataset(
    workers: int = WORKERS,
    log: Callable[[int, int, Outcome], None] | None = None,
) -> list[Outcome]:
    """Bring down every product the selection kept, once each.

    The selection holds a row per feature and observation, and the same product
    is often kept for several features, so the download runs over the distinct
    products those rows name rather than over the rows.

    Args:
        workers: How many downloads to run at once.
        log: What to call as each download finishes, given how many have
            finished, how many there are, and the outcome, or None to say
            nothing.

    Returns:
        One outcome per product, in completion order.

    Raises:
        FileNotFoundError: When no selection has been written, or no feature
            catalogue is cached to read a gridded instrument's ground from.
    """
    picked = dataset_list.read_dataset_list()
    with transport.Client() as ode, ThreadPoolExecutor(max_workers=workers) as pool:
        jobs = _plan(picked, ode, pool)
        outcomes: list[Outcome] = []
        for done, outcome in enumerate(_run(jobs, ode, pool), start=1):
            outcomes.append(outcome)
            if log:
                log(done, len(jobs), outcome)
    return outcomes


def _plan(
    picked: Sequence[Selection], ode: transport.Client, pool: Executor
) -> list[Job]:
    """Work out every distinct product the selection asks to be downloaded.

    Args:
        picked: What the search left of each feature, as the selection was read.
        ode: The client the gridded tiles are looked up through.
        pool: The pool those lookups are run on.

    Returns:
        One job per distinct product, the instruments in a settled order.

    Raises:
        FileNotFoundError: When no feature catalogue is cached.
    """
    wanted: dict[str, set[str]] = {name: set() for name in FETCH}
    for one in picked:
        for kept in one.observations:
            read = OBSERVED.get(kept.iid)
            # Skip a product no instrument here downloads, and one whose id
            # names no observation its instrument can be asked for.
            if read and (held := read(kept.pdsid)):
                wanted[kept.iid].add(held)
    features = dataset_list.read_kept_features(picked)
    for found in pool.map(lambda feature: mola.tiles(feature, client=ode), features):
        wanted[GRIDDED].update(found)
    return [
        Job(instrument=name, identifier=held)
        for name in FETCH
        for held in sorted(wanted[name])
    ]


def _run(
    jobs: Sequence[Job], ode: transport.Client, pool: Executor
) -> Iterator[Outcome]:
    """Bring every planned product down, yielding each as it finishes.

    Args:
        jobs: The products to fetch.
        ode: The client every download is asked through.
        pool: The pool they are run on.

    Yields:
        One outcome per job, in completion order.
    """

    def fetched(job: Job) -> Outcome:
        """Bring one product down, keeping the failure rather than raising it."""
        try:
            return Outcome(job, landed=FETCH[job.instrument](job.identifier, ode))
        except Exception as error:  # noqa: BLE001
            return Outcome(job, error=error)

    futures = [pool.submit(fetched, job) for job in jobs]
    for future in as_completed(futures):
        yield future.result()
