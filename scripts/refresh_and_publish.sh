#!/usr/bin/env bash

set -euo pipefail

python3 scripts/refresh_data.py

if [[ -z "$(git status --porcelain -- data/raw data/aggregated)" ]]; then
  echo "No data changes"
  exit 0
fi

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -- data/raw data/aggregated
git commit -m "chore: refresh gpu rental prices"

for attempt in 1 2 3; do
  if git push origin HEAD:main; then
    exit 0
  fi

  if (( attempt == 3 )); then
    break
  fi

  echo "Push attempt ${attempt} failed; synchronizing main before retrying."
  if git fetch origin main; then
    if ! git rebase origin/main; then
      git rebase --abort || true
      echo "Could not safely rebase the generated update onto origin/main."
      exit 1
    fi
  fi
  sleep $((attempt * 5))
done

echo "Unable to publish refreshed data after 3 attempts."
exit 1
