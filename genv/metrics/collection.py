from typing import Iterable, Optional

from genv.entities import Snapshot, System

from .metric import Metric
from .spec import Spec
from .type import Type


class Collection:
    """
    A metric collection.
    """

    def __init__(self, specs: Iterable[Spec]) -> None:
        self._metrics = [
            Metric(
                spec.name,
                spec.documentation,
                spec.labelnames,
                type=spec.type,
                convert=spec.convert,
                filter=spec.filter,
            )
            for spec in specs
        ]

    def __iter__(self):
        return self._metrics.__iter__()

    def __getitem__(self, name: str) -> Metric:
        return next(metric for metric in self if metric.name == name)

    def _find(self, type: Type) -> Iterable[Metric]:
        """
        Returns all metrics of the given type.
        """
        return [metric for metric in self if metric.type == type]

    def cleanup(
        self,
        system: Optional[System],
        snapshot: Optional[Snapshot],
        *,
        header: Optional[str] = None
    ) -> None:
        """
        Cleans up metric label values.

        :param header: First label value to filter; optional.
        """
        for metric in self:
            for labelvalues in metric.label_sets():
                if header and labelvalues[0] != header:
                    continue

                if snapshot and metric.filter:
                    if not metric.filter(
                        labelvalues[1:] if header else labelvalues, snapshot
                    ):
                        metric.remove(*labelvalues)

    def update(
        self, system: Optional[System], snapshot: Optional[Snapshot], labels: dict = {}
    ) -> None:
        """
        Updates metric values.
        """
        if system:
            self._general(system, labels)
            self._device(system, labels)

        if snapshot:
            self._system(snapshot, labels)
            self._env(snapshot, labels)
            self._process(snapshot, labels)
            self._user(snapshot, labels)

    def _general(self, system: System, labels: dict) -> None:
        """Updates general metrics."""

        self["genv_is_installed"].labels(**labels).set(system.genv.installed)

    def _device(self, system: System, labels: dict) -> None:
        """
        Updates per-device metrics.
        """
        for device in system.devices:
            for metric in self._find(Type.Device):
                if not metric.convert:
                    continue

                metric.labels(index=device.index, **labels).set(metric.convert(device))

    def _system(self, snapshot: Snapshot, labels: dict) -> None:
        """
        Updates system-wide metrics.
        """
        for metric in self._find(Type.System):
            if not metric.convert:
                continue

            metric.labels(**labels).set(metric.convert(snapshot))

    def _env(self, snapshot: Snapshot, labels: dict) -> None:
        """
        Updates per-environment metrics.
        """
        for env in snapshot.envs:
            env_snapshot = snapshot.filter(eid=env.eid)

            for metric in self._find(Type.Environment):
                if not metric.convert:
                    continue

                metric.labels(eid=env.eid, **labels).set(metric.convert(env_snapshot))

    def _process(self, snapshot: Snapshot, labels: dict) -> None:
        """
        Updates per-process metrics.
        """
        for process in snapshot.processes:
            pid = process.pid
            eid = process.eid or ""

            self["genv_process_devices_total"].labels(pid=pid, eid=eid, **labels).set(
                len(process.indices)
            )

            for usage in process.used_gpu_memory:
                self["genv_process_used_gpu_memory_bytes"].labels(
                    pid=pid, eid=eid, device=usage.index, **labels
                ).set(usage.bytes)

    def _user(self, snapshot: Snapshot, labels: dict) -> None:
        """
        Updates per-user metrics.
        """
        for username in snapshot.envs.usernames:
            user_snapshot = snapshot.filter(username=username)

            for metric in self._find(Type.User):
                if not metric.convert:
                    continue

                metric.labels(username=username, **labels).set(
                    metric.convert(user_snapshot)
                )
