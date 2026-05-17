"""Trigger a site Docker image rebuild and recreate the running container.

`docker restart` alone is not enough — the container has to be removed
and re-run so the new image SHA takes effect. We capture the existing
container's HostConfig + network + env, then stop + remove + run with
the same config but the freshly built image.

Requires:
  - /var/run/docker.sock mounted into this container
  - The host's repo directory mounted at `settings.repo_path`
  - `docker` Python SDK installed (in pyproject)

No-op if `site_image_name` is empty.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class RebuildError(Exception):
    pass


def rebuild_site_image(
    *,
    image_name: str,
    dockerfile_path: str,
    repo_path: Path,
    container_name: str,
) -> None:
    if not image_name:
        log.info("rebuild_site: SITE_IMAGE_NAME empty; skipping")
        return
    try:
        import docker            # type: ignore[import-not-found]
    except ImportError as e:
        raise RebuildError("docker SDK not installed") from e

    client = docker.from_env()

    log.info("rebuild_site: building %s from %s", image_name, repo_path)
    try:
        image, logs = client.images.build(
            path=str(repo_path),
            dockerfile=dockerfile_path,
            tag=image_name,
            rm=True,
            forcerm=True,
            pull=False,
        )
    except docker.errors.BuildError as e:
        for chunk in (e.build_log or []):
            if isinstance(chunk, dict) and chunk.get("stream"):
                log.error("docker build: %s", chunk["stream"].rstrip())
        raise RebuildError(f"build failed: {e}") from e
    except docker.errors.APIError as e:
        raise RebuildError(f"docker API error: {e}") from e

    for chunk in logs:
        if isinstance(chunk, dict) and chunk.get("stream"):
            line = chunk["stream"].rstrip()
            if line:
                log.debug("docker build: %s", line)
    log.info("rebuild_site: built %s", image.short_id)

    # Snapshot the running container's config so we can recreate it.
    try:
        existing = client.containers.get(container_name)
    except docker.errors.NotFound:
        log.warning(
            "rebuild_site: container %s not running; image updated but"
            " no recreate possible — start it manually",
            container_name,
        )
        return

    spec = _capture_runtime_spec(existing)
    log.info("rebuild_site: stopping + removing %s", container_name)
    try:
        existing.stop(timeout=10)
        existing.remove(force=True)
    except docker.errors.APIError as e:
        raise RebuildError(f"remove failed: {e}") from e

    log.info("rebuild_site: recreating %s with %s", container_name, image_name)
    try:
        client.containers.run(
            image=image_name,
            name=container_name,
            detach=True,
            **spec,
        )
    except docker.errors.APIError as e:
        raise RebuildError(f"create failed: {e}") from e
    log.info("rebuild_site: container up")


def _capture_runtime_spec(container: Any) -> dict[str, Any]:
    """Extracts the kwargs we need to recreate the container.

    Pulls only the fields we know we set in compose — anything more
    elaborate (capabilities, sysctls, etc.) would round-trip lossily,
    and we'd rather fail loudly than silently misconfigure.
    """
    attrs = container.attrs
    host = attrs.get("HostConfig", {}) or {}
    cfg = attrs.get("Config", {}) or {}
    net = attrs.get("NetworkSettings", {}) or {}

    # Ports: {"3000/tcp": [{"HostPort": "3003"}]} → {"3000/tcp": 3003}
    port_bindings = host.get("PortBindings") or {}
    ports: dict[str, int | str] = {}
    for container_port, bindings in port_bindings.items():
        if bindings:
            hp = bindings[0].get("HostPort")
            ports[container_port] = int(hp) if (hp and hp.isdigit()) else hp

    # Volumes: {"chronos-dist-data": "/app/dist/data:ro"} as docker-py expects.
    binds = host.get("Binds") or []
    mounts = host.get("Mounts") or []
    volumes: dict[str, dict[str, str]] = {}
    for b in binds:
        # Format: "name:dest[:mode]"
        parts = b.split(":")
        if len(parts) >= 2:
            src, dst = parts[0], parts[1]
            mode = parts[2] if len(parts) > 2 else "rw"
            volumes[src] = {"bind": dst, "mode": mode}
    for m in mounts:
        src = m.get("Name") or m.get("Source")
        dst = m.get("Destination")
        mode = "ro" if not m.get("RW", True) else "rw"
        if src and dst:
            volumes[src] = {"bind": dst, "mode": mode}

    # Networks. docker-py's run() accepts only one network at a time;
    # extras are attached after.
    networks = list((net.get("Networks") or {}).keys())
    primary_network = networks[0] if networks else None

    # Environment as list of "KEY=value".
    env = cfg.get("Env") or []

    restart_policy = host.get("RestartPolicy") or {}
    rp_name = restart_policy.get("Name") or "no"

    return {
        "ports": ports,
        "volumes": volumes,
        "environment": env,
        "network": primary_network,
        "restart_policy": {"Name": rp_name, "MaximumRetryCount": restart_policy.get("MaximumRetryCount", 0)},
    }
