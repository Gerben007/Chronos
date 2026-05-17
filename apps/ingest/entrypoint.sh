#!/bin/sh
# Container entrypoint.
#
# Docker volumes are owned by root when first created. Rather than make the
# operator run a chown sidecar, the container starts as root, fixes
# ownership on the data volumes, then drops privileges to UID 1000 before
# exec'ing the real command.

set -e

if [ "$(id -u)" = "0" ]; then
    for d in /data/db /data/dist; do
        [ -d "$d" ] && chown -R 1000:1000 "$d"
    done
    exec setpriv --reuid=1000 --regid=1000 --clear-groups -- "$@"
fi

exec "$@"
