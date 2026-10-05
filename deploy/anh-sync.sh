#!/usr/bin/env bash
# Runs sync.py (Notion <-> lab.horyz.io) and publishes docs/data.json. Triggered by anh-sync.timer every 5 min.
set -euo pipefail
cd /opt/anh-notion
exec 9>/var/lock/anh-sync.lock
flock -n 9 || exit 0                                   # never overlap
export GIT_SSH_COMMAND="ssh -i /etc/anh-sync/deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
git pull -q --rebase -X theirs
set -a; . /etc/anh-sync.env; set +a                    # NOTION, LAB_SYNC_KEY  (600, root)
python3 sync.py
if ! git diff --quiet -- docs/data.json; then
  git add docs/data.json
  git -c user.name=anh-sync -c user.email=anh-sync@users.noreply.github.com commit -qm "sync data.json"
  git push -q
fi
