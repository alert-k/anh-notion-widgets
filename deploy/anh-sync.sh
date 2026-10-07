#!/usr/bin/env bash
# Runs sync.py (Notion <-> lab.horyz.io). Triggered by anh-sync.path (progress file changed) and anh-sync.timer (every 5 min).
set -euo pipefail
cd /opt/anh-notion
exec 9>/var/lock/anh-sync.lock
flock -n 9 || exit 0                                   # never overlap; path trigger re-fires after we finish
export GIT_SSH_COMMAND="ssh -i /etc/anh-sync/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
git pull -q --ff-only || true                          # pick up code updates; keep running on the old code if offline
set -a; . /etc/anh-sync.env; set +a                    # NOTION, LAB_SYNC_KEY (600, root)
export ANH_DATA_DIR=/var/lib/anh-widgets               # data.json lives outside the repo
mkdir -p "$ANH_DATA_DIR"
exec python3 sync.py
