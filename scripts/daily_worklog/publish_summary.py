#!/usr/bin/env python3
"""요약 Markdown을 docx로 바꿔 저장 위치에 덮어쓰지 않고 저장한 뒤 존재를 확인한다.

같은 이름(확장자 무관, 예: 기존 .gdoc)이 있으면 _v2, _v3 …을 붙인다.
마지막 줄에 저장한 최종 경로를 출력한다.
"""
import argparse
import filecmp
import html
import os
import re
import shutil
import subprocess
import sys

CSS = """
body { font-family: 'Apple SD Gothic Neo', 'Noto Sans KR', sans-serif; font-size: 11pt; line-height: 1.5; }
h1 { font-size: 18pt; } h2 { font-size: 14pt; margin-top: 14pt; } h3 { font-size: 12pt; margin-top: 8pt; }
"""


def inline(text):
    text = html.escape(text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


def md_to_html(md):
    """요약에 쓰는 Markdown 일부(제목, 들여쓴 글머리, 굵게, 구분선)만 HTML로 바꾼다."""
    out, depth = [], 0
    for raw in md.splitlines():
        line = raw.rstrip()
        bullet = re.match(r"^(\s*)[-*]\s+(.*)$", line)
        if bullet:
            level = min(len(bullet.group(1).replace("\t", "  ")) // 2, 3) + 1
            while depth < level:
                out.append("<ul>")
                depth += 1
            while depth > level:
                out.append("</ul>")
                depth -= 1
            out.append("<li>%s</li>" % inline(bullet.group(2)))
            continue
        while depth:
            out.append("</ul>")
            depth -= 1
        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            level = len(heading.group(1))
            out.append("<h%d>%s</h%d>" % (level, inline(heading.group(2)), level))
        elif line.strip() == "---":
            out.append("<hr>")
        elif line.strip():
            out.append("<p>%s</p>" % inline(line))
    out.extend(["</ul>"] * depth)
    return "<!doctype html><html><head><meta charset='utf-8'><style>%s</style></head><body>%s</body></html>" % (
        CSS, "\n".join(out))


def free_name(dest_dir, stem, ext):
    taken = {os.path.splitext(f)[0] for f in os.listdir(dest_dir)}
    if stem not in taken:
        return stem + ext
    n = 2
    while "%s_v%d" % (stem, n) in taken:
        n += 1
    return "%s_v%d%s" % (stem, n, ext)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markdown", required=True)
    ap.add_argument("--dest-dir", required=True)
    ap.add_argument("--stem", required=True, help="예: 2026-10-16_일일요약")
    args = ap.parse_args()

    with open(args.markdown, encoding="utf-8") as fh:
        md = fh.read()
    if not md.lstrip().startswith("# "):
        print("요약 형식 오류: 첫 줄이 '# 날짜 일일요약'이 아님", file=sys.stderr)
        return 3

    work_dir = os.path.dirname(os.path.abspath(args.markdown))
    html_path = os.path.join(work_dir, "summary.html")
    docx_path = os.path.join(work_dir, "summary.docx")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(md_to_html(md))
    subprocess.run(["/usr/bin/textutil", "-convert", "docx", "-output", docx_path, html_path],
                   check=True, timeout=120)

    if not os.path.isdir(args.dest_dir):
        print("저장 위치를 찾지 못함: %s" % args.dest_dir, file=sys.stderr)
        return 4
    final = os.path.join(args.dest_dir, free_name(args.dest_dir, args.stem, ".docx"))
    shutil.copyfile(docx_path, final)
    if not (os.path.isfile(final) and filecmp.cmp(docx_path, final, shallow=False)):
        print("저장 확인 실패: %s" % final, file=sys.stderr)
        return 5
    print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
