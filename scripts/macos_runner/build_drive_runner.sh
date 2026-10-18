#!/usr/bin/env bash
# cmb-drive-runner를 빌드해 ~/Library/Application Support/CMBIOPHARM/bin/에 둔다.
# 다시 빌드하면 바이너리가 바뀌어 macOS 권한이 풀릴 수 있다. 이미 있으면 --force 없이는 건드리지 않는다.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bin_dir="${HOME}/Library/Application Support/CMBIOPHARM/bin"
target="${bin_dir}/cmb-drive-runner"

if [[ -x "${target}" && "${1:-}" != "--force" ]]; then
  echo "이미 있음: ${target} (다시 빌드하려면 --force, 이후 전체 디스크 접근 권한 재부여 필요)"
  exit 0
fi

mkdir -p "${bin_dir}"
xcrun clang -O2 -Wall -o "${target}.tmp" "${script_dir}/cmb_drive_runner.c"
codesign --force --sign - --identifier com.cmbiopharm.drive-runner "${target}.tmp"
mv "${target}.tmp" "${target}"
echo "빌드 완료: ${target}"
echo "시스템 설정 > 개인정보 보호 및 보안 > 전체 디스크 접근 권한에서 + 로 이 파일을 추가하세요."
