#!/usr/bin/env bash
# Agent 03 — v0 폴더의 대표 메모(첫 줄 "v1발행")를 찾아 주간 정리 v1 이상을 공유 드라이브에 발행한다.
# launchd가 10분마다 실행한다. 원본 일지·rnd 리포는 읽기만 한다.
set -uo pipefail

export PATH="${HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export TZ="Asia/Seoul"

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd -- "${script_dir}/../.." && pwd)"
conf="${repo_dir}/config/daily_worklog.conf"
drive_root="${HOME}/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com"
log_dir="${HOME}/Library/Logs/CMBIOPHARM"
state_dir="${HOME}/Library/Application Support/CMBIOPHARM/weekly-review"
lock_dir="${TMPDIR:-/tmp}/cmbiopharm-release-watch.lock"

mkdir -p "${log_dir}" "${state_dir}"
exec >>"${log_dir}/weekly-release.log" 2>&1

mkdir "${lock_dir}" 2>/dev/null || exit 0
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT

# shellcheck source=/dev/null
source "${conf}"
[[ -d "${drive_root}/${DRAFT_DIR}" ]] || { echo "[$(date '+%F %T')] FAIL v0 폴더 없음(마운트 확인)"; exit 1; }

exec /usr/bin/python3 -I "${script_dir}/release_watch.py" \
  --drive-root "${drive_root}" \
  --draft-dir "${drive_root}/${DRAFT_DIR}" \
  --share-root "${drive_root}/${SHARE_DIR}/주간_업무중점" \
  --people "${repo_dir}/config/daily_worklog_people.tsv" \
  --rnd-dir "${RND_DIR:-${CMBIOPHARM_RND_DIR:-$(cd -- "${repo_dir}/.." && pwd)/rnd}}" \
  --state-dir "${state_dir}" \
  --model "${WEEKLY_MODEL:-claude-opus-5-5}" \
  --kakao-dir "${KAKAO_DIR:+${drive_root}/${KAKAO_DIR}}"
