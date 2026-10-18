/*
 * cmb-drive-runner: launchd 작업이 Google Drive(~/Library/CloudStorage)를 읽고 쓸 수 있게 하는 실행기.
 * macOS는 launchd가 띄운 프로세스(책임 프로세스)의 권한으로 자식 프로세스의 파일 접근을 판단한다.
 * 이 실행기에만 "전체 디스크 접근 권한"을 주고, 인자로 받은 명령을 자식으로 실행한 뒤 종료 코드를 그대로 돌려준다.
 * exec로 자신을 바꾸면 권한 판단 대상이 bash로 바뀌므로 반드시 spawn 후 기다린다.
 * 사용: cmb-drive-runner /bin/bash /path/to/script.sh [args...]
 */
#include <spawn.h>
#include <stdio.h>
#include <sys/wait.h>

extern char **environ;

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s <program> [args...]\n", argv[0]);
        return 64;
    }
    pid_t pid;
    int rc = posix_spawn(&pid, argv[1], NULL, NULL, &argv[1], environ);
    if (rc != 0) {
        perror("posix_spawn");
        return 127;
    }
    int status = 0;
    while (waitpid(pid, &status, 0) < 0) {
    }
    if (WIFEXITED(status)) return WEXITSTATUS(status);
    return 128 + (WIFSIGNALED(status) ? WTERMSIG(status) : 0);
}
