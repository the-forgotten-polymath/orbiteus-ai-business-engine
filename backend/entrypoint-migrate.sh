#!/bin/sh
# One-shot migration entrypoint for the `migrate` compose service.
#
# Runs `alembic upgrade head` and exits. The backend service depends on the
# successful completion of this container.
#
# Inside Alembic itself, every upgrade should wrap its changes with the
# advisory lock helper from `orbiteus_core.alembic_lock` to be safe against
# concurrent runs in multi-replica deployments.
set -e

echo "[migrate] alembic upgrade head"
alembic upgrade head
echo "[migrate] done."
