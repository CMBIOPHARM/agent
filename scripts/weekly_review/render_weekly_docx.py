#!/usr/bin/env python3
"""주간 정리 JSON을 Word(docx)로 만든다. 앞쪽: 지난주 중점 대비 수행, 뒤쪽(쪽 나눔): 차주 권장 업무.

표준 라이브러리만으로 WordprocessingML을 직접 쓴다(표·쪽 나눔·테두리 유지).
"""
import argparse
import datetime as dt
import json
import re
import sys
import zipfile
from xml.sax.saxutils import escape

FONT = "맑은 고딕"
WEEKDAYS = "월화수목금토일"
STATUS_FILL = {"완료": "E2F0D9", "일부": "FFF2CC", "미완료": "F8CBAD", "미확인": "E7E6E6"}


def kdate(d):
    return "%s(%s)" % (d.strftime("%m-%d"), WEEKDAYS[d.weekday()])


def run(text, size=11, bold=False, color=None):
    props = '<w:rFonts w:ascii="%s" w:hAnsi="%s" w:eastAsia="%s"/>' % (FONT, FONT, FONT)
    if bold:
        props += "<w:b/>"
    if color:
        props += '<w:color w:val="%s"/>' % color
    props += '<w:sz w:val="%d"/><w:szCs w:val="%d"/>' % (size * 2, size * 2)
    return '<w:r><w:rPr>%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (props, escape(str(text)))


def para(runs, align=None, space_after=80, border=None, shade=None, keep=False):
    ppr = ""
    if keep:
        ppr += "<w:keepNext/>"
    if border:
        ppr += ('<w:pBdr>' + "".join(
            '<w:%s w:val="%s" w:sz="12" w:space="4" w:color="%s"/>' % (side, border[0], border[1])
            for side in ("top", "left", "bottom", "right")) + "</w:pBdr>")
    if shade:
        ppr += '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % shade
    ppr += '<w:spacing w:after="%d"/>' % space_after
    if align:
        ppr += '<w:jc w:val="%s"/>' % align
    return "<w:p><w:pPr>%s</w:pPr>%s</w:p>" % (ppr, runs)


def heading(text):
    return para(run(text, 14, True, "1F3864"), space_after=100, keep=True)


def bullets(items, size=10):
    if not items:
        return para(run("· 없음", size, color="595959"))
    return "".join(para(run("· " + str(x), size), space_after=40) for x in items)


def cell(content_runs, width, fill=None, align=None):
    tcpr = '<w:tcW w:w="%d" w:type="dxa"/>' % width
    if fill:
        tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="%s"/>' % fill
    tcpr += '<w:vAlign w:val="center"/>'
    paras = content_runs if isinstance(content_runs, list) else [content_runs]
    body = "".join(para(r, align=align, space_after=0) for r in paras)
    return "<w:tc><w:tcPr>%s</w:tcPr>%s</w:tc>" % (tcpr, body)


def table(widths, header, rows):
    grid = "".join('<w:gridCol w:w="%d"/>' % w for w in widths)
    borders = "".join('<w:%s w:val="single" w:sz="4" w:space="0" w:color="8EA9C1"/>' % s
                      for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
    tblpr = ('<w:tblPr><w:tblW w:w="%d" w:type="dxa"/><w:tblBorders>%s</w:tblBorders>'
             '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:top w:w="50" w:type="dxa"/>'
             '<w:left w:w="80" w:type="dxa"/><w:bottom w:w="50" w:type="dxa"/>'
             '<w:right w:w="80" w:type="dxa"/></w:tblCellMar></w:tblPr>') % (sum(widths), borders)
    head = '<w:tr><w:trPr><w:tblHeader/></w:trPr>%s</w:tr>' % "".join(
        cell(run(h, 10, True, "FFFFFF"), w, "1F3864", "center") for h, w in zip(header, widths))
    body = ""
    for r in rows:
        body += '<w:tr><w:trPr><w:cantSplit/></w:trPr>%s</w:tr>' % "".join(
            cell(c[0], w, c[1] if len(c) > 1 else None, c[2] if len(c) > 2 else None) for c, w in zip(r, widths))
    return "<w:tbl>%s<w:tblGrid>%s</w:tblGrid>%s%s</w:tbl>" % (tblpr, grid, head, body) + para("", space_after=60)


DRAFT_LABEL = "초안 v0 · 대표 검토 전 · 배포 금지"


def build(data, name, title, prev_monday, next_monday, generated, label=DRAFT_LABEL):
    prev_fri = prev_monday + dt.timedelta(days=4)
    next_fri = next_monday + dt.timedelta(days=4)
    x = []
    color = "C00000" if label == DRAFT_LABEL else "1F3864"
    x.append(para(run(label, 11, True, color), align="center", border=("single", color), space_after=160))
    x.append(para(run("주간 정리 — %s %s" % (name, title), 20, True), space_after=40))
    x.append(para(run("지난주 %s~%s · 차주 %s~%s · 생성 %s" % (
        kdate(prev_monday), kdate(prev_fri), kdate(next_monday), kdate(next_fri), generated), 10, color="595959"),
        space_after=160))

    # 앞쪽
    x.append(heading("1. 지난주 중점 대비 수행 (업무일지)"))
    x.append(para(run("중점: ", 11, True) + run(data.get("focus_line") or "미확인", 11), shade="DEEAF6",
                  space_after=60))
    x.append(para(run("기준: %s" % (data.get("focus_source") or "없음"), 9, color="595959"), space_after=80))
    rows = []
    for i, r in enumerate(data.get("front_rows") or [], 1):
        st = (r.get("status") or "미확인").strip()
        rows.append([(run(i, 10, True), None, "center"), (run(r.get("item", ""), 10, True),),
                     (run(r.get("done", ""), 10),), (run(st, 10, True), STATUS_FILL.get(st), "center")])
    x.append(table([500, 3000, 4900, 1100], ["#", "중점 항목", "수행 내용 (업무일지)", "상태"], rows))
    x.append(para(run("중점 외 수행", 11, True), space_after=40, keep=True))
    x.append(bullets(data.get("extra_done")))
    x.append(para(run("기록 점검", 11, True), space_after=40, keep=True))
    x.append(bullets(data.get("record_checks")))

    # 뒤쪽
    x.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')
    x.append(heading("2. 차주 권장 업무 방향 (대표 지시·rnd 리포 기준)"))
    x.append(para(run("방향: ", 11, True) + run(data.get("direction_line") or "미확인", 11), shade="FBE5D6",
                  space_after=100))
    rows = []
    for i, r in enumerate(data.get("back_rows") or [], 1):
        rows.append([(run(i, 10, True), None, "center"),
                     ([run(r.get("task", ""), 10, True), run(r.get("detail", ""), 9, color="404040")],),
                     (run(r.get("basis", ""), 9, color="404040"),), (run(r.get("criteria", ""), 10),)])
    x.append(table([500, 3700, 2500, 2800], ["#", "권장 업무", "근거 (지시·리포)", "완료 기준"], rows))
    x.append(para(run("대표 결정 대기", 11, True), space_after=40, keep=True))
    x.append(bullets(data.get("decisions")))
    x.append(para(run("미룬 것", 11, True), space_after=40, keep=True))
    x.append(bullets(data.get("deferred")))
    notes = list(data.get("notes") or [])
    srcs = data.get("sources") or []
    if srcs:
        notes.append("읽은 리포 문서: " + ", ".join(srcs))
    if notes:
        x.append(para(run("참고", 9, True, "595959"), space_after=20))
        x.extend(para(run(n, 8, color="595959"), space_after=20) for n in notes)

    sect = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
            '<w:pgMar w:top="1000" w:right="1000" w:bottom="1000" w:left="1000" w:header="500" w:footer="500" w:gutter="0"/>'
            '</w:sectPr>')
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            + "".join(x) + sect + "</w:body></w:document>")


CONTENT_TYPES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                 '<Default Extension="xml" ContentType="application/xml"/>'
                 '<Override PartName="/word/document.xml" '
                 'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                 '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/></Relationships>')


def load_json(path):
    text = open(path, encoding="utf-8").read().strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("JSON 객체를 찾지 못함")
    return json.loads(text[start:end + 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--next-monday", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--label", default=DRAFT_LABEL, help="맨 위 테두리 문구. v1 이상은 예: 'v1 · 대표 검토 반영본'")
    args = ap.parse_args()

    data = load_json(args.json)
    if not data.get("front_rows") and not data.get("back_rows"):
        print("주간 정리 JSON에 표 내용이 없음", file=sys.stderr)
        return 3
    next_monday = dt.date.fromisoformat(args.next_monday)
    generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    xml = build(data, args.name, args.title, next_monday - dt.timedelta(days=7), next_monday, generated, args.label)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", RELS)
        zf.writestr("word/document.xml", xml)
    print(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
