/*
 * cmb-materialize: Drive(File Provider)에서 아직 내려받지 않은 파일을 launchd 작업에서도 열 수 있게 한다.
 * launchd가 띄운 프로세스는 dataless 파일 내려받기가 꺼져 있어 open/read가 EDEADLK
 * (Resource deadlock avoided)로 실패한다. 내려받기 정책을 켠 뒤 나머지 인자를 exec한다.
 * 정책은 exec와 자식 프로세스에 이어진다. 사용: cmb-drive-runner cmb-materialize /bin/bash script.sh
 * 전체 디스크 접근 권한은 앞의 cmb-drive-runner가 갖고 있으므로 이 파일은 권한이 필요 없다.
 */
#include <stdio.h>
#include <sys/resource.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s program [args...]\n", argv[0]);
        return 64;
    }
    if (setiopolicy_np(IOPOL_TYPE_VFS_MATERIALIZE_DATALESS_FILES, IOPOL_SCOPE_PROCESS,
                       IOPOL_MATERIALIZE_DATALESS_FILES_ON) != 0)
        perror("setiopolicy_np");
    execv(argv[1], argv + 1);
    perror("execv");
    return 127;
}
