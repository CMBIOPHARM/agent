#!/usr/bin/env bash
# 항상 켜진 Mac에서 등록된 저장소와 공용 실행 환경을 안전하게 점검한다.
# 깨끗한 main이 원격보다 뒤에 있을 때만 fast-forward한다.
set -uo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export GIT_TERMINAL_PROMPT=0

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
control_repo="$(cd -- "${script_dir}/.." && pwd)"
orca_root="${CMBIOPHARM_ORCA_ROOT:-$(cd -- "${control_repo}/.." && pwd)}"
registry="${CMBIOPHARM_REPO_REGISTRY:-${control_repo}/config/repositories.tsv}"
user_home="${HOME}"
log_dir="${user_home}/Library/Logs/CMBIOPHARM"
log_file="${log_dir}/agent-hub.log"
lock_dir="${TMPDIR:-/tmp}/cmbiopharm-agent-hub.lock"
drive_root="${user_home}/Library/CloudStorage/GoogleDrive-jpark@cmbiopharm.com"

mkdir -p "${log_dir}"
if [[ -f "${log_file}" ]] && [[ "$(stat -f%z "${log_file}" 2>/dev/null || echo 0)" -gt 1048576 ]]; then
  tail -n 1000 "${log_file}" > "${log_file}.tmp" && mv "${log_file}.tmp" "${log_file}"
fi
exec >>"${log_file}" 2>&1

stamp() { date '+%Y-%m-%d %H:%M:%S %Z'; }
log() { printf '[%s] %s\n' "$(stamp)" "$*"; }

if ! mkdir "${lock_dir}" 2>/dev/null; then
  log "SKIP 이전 통합 점검이 아직 실행 중"
  exit 0
fi
trap 'rmdir "${lock_dir}" 2>/dev/null || true' EXIT

if [[ ! -f "${registry}" ]]; then
  log "FAIL 저장소 등록부를 찾지 못함: ${registry}"
  exit 1
fi

repo_total=0
fail_total=0
warn_total=0

while IFS=$'\t' read -r repo_name relative_path auto_fast_forward extra; do
  [[ -z "${repo_name}" || "${repo_name}" == \#* ]] && continue
  repo_total=$((repo_total + 1))

  if [[ -z "${relative_path}" || -n "${extra:-}" || "${relative_path}" == /* || "${relative_path}" == *'..'* ]]; then
    log "FAIL [${repo_name}] 등록 경로가 안전하지 않음: ${relative_path:-비어 있음}"
    fail_total=$((fail_total + 1))
    continue
  fi

  repo_dir="${orca_root}/${relative_path}"
  if ! git -C "${repo_dir}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    log "FAIL [${repo_name}] Git 저장소를 찾지 못함: ${repo_dir}"
    fail_total=$((fail_total + 1))
    continue
  fi

  if ! git -C "${repo_dir}" fetch --prune --quiet origin; then
    log "FAIL [${repo_name}] GitHub fetch 실패"
    fail_total=$((fail_total + 1))
    continue
  fi

  if ! git -C "${repo_dir}" rev-parse --verify --quiet origin/main >/dev/null; then
    log "FAIL [${repo_name}] origin/main을 찾지 못함"
    fail_total=$((fail_total + 1))
    continue
  fi

  branch="$(git -C "${repo_dir}" symbolic-ref --quiet --short HEAD 2>/dev/null || true)"
  dirty="$(git -C "${repo_dir}" status --porcelain 2>/dev/null || true)"

  if [[ "${branch}" != "main" ]]; then
    log "WARN [${repo_name}] 기본 저장소 브랜치가 main이 아님: ${branch:-detached}"
    warn_total=$((warn_total + 1))
  elif [[ -n "${dirty}" ]]; then
    log "WARN [${repo_name}] main에 미커밋 변경이 있어 자동 갱신하지 않음"
    warn_total=$((warn_total + 1))
  else
    read -r ahead behind < <(git -C "${repo_dir}" rev-list --left-right --count 'HEAD...origin/main' | tr '\t' ' ')
    if [[ "${ahead}" -eq 0 && "${behind}" -gt 0 ]]; then
      if [[ "${auto_fast_forward}" == "yes" ]]; then
        before="$(git -C "${repo_dir}" rev-parse --short HEAD)"
        if git -C "${repo_dir}" merge --ff-only --quiet origin/main; then
          log "PULL [${repo_name}] ${before} -> $(git -C "${repo_dir}" rev-parse --short HEAD) (${behind}개 커밋)"
        else
          log "FAIL [${repo_name}] origin/main fast-forward 실패"
          fail_total=$((fail_total + 1))
        fi
      else
        log "INFO [${repo_name}] origin/main보다 ${behind}개 뒤처짐 (자동 갱신 꺼짐)"
      fi
    elif [[ "${ahead}" -gt 0 && "${behind}" -gt 0 ]]; then
      log "WARN [${repo_name}] main 분기됨: 로컬 +${ahead}, 원격 +${behind}"
      warn_total=$((warn_total + 1))
    elif [[ "${ahead}" -gt 0 ]]; then
      log "WARN [${repo_name}] main에 미푸시 커밋 ${ahead}개"
      warn_total=$((warn_total + 1))
    else
      log "OK [${repo_name}] GitHub main 최신: $(git -C "${repo_dir}" rev-parse --short HEAD)"
    fi
  fi

  unmerged=""
  while IFS= read -r remote_branch; do
    case "${remote_branch}" in
      origin/HEAD|origin/main) continue ;;
    esac
    if git -C "${repo_dir}" cherry origin/main "${remote_branch}" 2>/dev/null | grep -q '^+'; then
      unmerged+="${remote_branch}"$'\n'
    fi
  done < <(git -C "${repo_dir}" for-each-ref --format='%(refname:short)' refs/remotes/origin)
  unmerged="${unmerged%$'\n'}"
  if [[ -n "${unmerged}" ]]; then
    count="$(printf '%s\n' "${unmerged}" | wc -l | tr -d ' ')"
    names="$(printf '%s\n' "${unmerged}" | paste -sd ',' - | sed 's/,/, /g')"
    log "INFO [${repo_name}] main 미병합 원격 브랜치 ${count}개: ${names}"
  fi
done < "${registry}"

if [[ "${repo_total}" -eq 0 ]]; then
  log "FAIL 저장소 등록부가 비어 있음"
  fail_total=$((fail_total + 1))
fi

if [[ -d "${drive_root}/공유 드라이브/CMBIOPHARM" ]]; then
  log "OK Google Drive 마운트"
else
  log "WARN Google Drive CMBIOPHARM 공유 드라이브를 찾지 못함"
  warn_total=$((warn_total + 1))
fi

if [[ -x "${orca_root}/rnd/scripts/.venv/bin/python" ]]; then
  log "OK Mac 시뮬레이터 환경"
else
  log "WARN Mac 시뮬레이터 환경 없음"
  warn_total=$((warn_total + 1))
fi

log "SUMMARY 저장소 ${repo_total}개, 경고 ${warn_total}건, 실패 ${fail_total}건"
[[ "${fail_total}" -eq 0 ]]
