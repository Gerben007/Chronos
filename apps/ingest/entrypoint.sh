#!/bin/sh
# Container entrypoint.
#
# Docker volumes are owned by root when first created. Start as root, fix
# ownership on the data volumes, optionally grant the docker socket group
# to the chronos user, then drop privileges to UID 1000.

set -e

if [ "$(id -u)" = "0" ]; then
    for d in /data/db /data/dist; do
        [ -d "$d" ] && chown -R 1000:1000 "$d"
    done

    # If /var/run/docker.sock is mounted from the host, make sure UID 1000
    # can talk to it. The host's docker group GID varies; we read it from
    # the socket and add a matching group inside the container.
    DOCKER_GROUPS=""
    if [ -S /var/run/docker.sock ]; then
        DOCKER_GID=$(stat -c '%g' /var/run/docker.sock)
        if ! getent group "$DOCKER_GID" >/dev/null 2>&1; then
            groupadd -g "$DOCKER_GID" docker-host 2>/dev/null || true
        fi
        DOCKER_GROUPS="$DOCKER_GID"
    fi

    if [ -n "$DOCKER_GROUPS" ]; then
        exec setpriv --reuid=1000 --regid=1000 --groups="$DOCKER_GROUPS" -- "$@"
    fi
    exec setpriv --reuid=1000 --regid=1000 --clear-groups -- "$@"
fi

exec "$@"
