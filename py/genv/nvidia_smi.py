import asyncio
from typing import Dict, Iterable


async def run(*args: str) -> str:
    """
    Runs nvidia-smi with the given arguments as a subprocess, waits for it and returns its output.
    Raises 'RuntimeError' if subprocess exited with failure.
    """
    args = ["nvidia-smi", *args]

    process = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        command = " ".join(args)
        raise RuntimeError(
            f"Failed running '{command}' ({stderr.decode('utf-8').strip()})"
        )

    return stdout.decode("utf-8").strip()


async def device_uuids() -> Dict[str, int]:
    """
    Queries device UUIDs.

    :return: A mapping from device UUID to its index
    """
    output = await run("--query-gpu=uuid,index", "--format=csv,noheader")

    mapping = dict()

    for line in output.splitlines():
        uuid, index = line.split(", ")
        mapping[uuid] = int(index)

    return mapping


async def compute_apps() -> Iterable[Dict]:
    """
    Queries the running compute apps.
    """
    output = await run(
        "--query-compute-apps=gpu_uuid,pid,used_gpu_memory",
        "--format=csv,noheader,nounits",
    )

    apps = []

    for line in output.splitlines():
        gpu_uuid, pid, used_gpu_memory = line.split(", ")

        apps.append(
            dict(
                gpu_uuid=gpu_uuid, pid=int(pid), used_gpu_memory=f"{used_gpu_memory}mi"
            )
        )

    return apps


class Process:
    def __init__(self, gpu_index: int, pid: int, used_gpu_memory: str) -> None:
        self.gpu_index = gpu_index
        self.pid = pid
        self.used_gpu_memory = used_gpu_memory

    def __repr__(self) -> str:
        return f"nvidia_smi.Process(gpu={self.gpu_index}, pid={self.pid}, used_gpu_memory='{self.used_gpu_memory}')"


async def compute_processes() -> Iterable[Process]:
    """
    Returns information about all running compute processes.
    """
    uuids, apps = await asyncio.gather(device_uuids(), compute_apps())

    return [
        Process(
            gpu_index=uuids[app["gpu_uuid"]],
            pid=app["pid"],
            used_gpu_memory=app["used_gpu_memory"],
        )
        for app in apps
    ]
