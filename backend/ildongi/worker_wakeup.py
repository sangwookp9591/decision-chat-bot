"""Process-local wake signal shared by request intake and job workers."""

import weakref

_workers: weakref.WeakSet = weakref.WeakSet()


def register_worker(worker) -> None:
    _workers.add(worker)


def notify_new_job() -> None:
    for worker in tuple(_workers):
        worker.wake()
