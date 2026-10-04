# -*- coding: utf-8 -*-
"""
内燃机学（中国大学MOOC ZJU-1460864162）小测题库复习资料生成器
输入: data/quiz_<测验ID>.json  —— 从浏览器收割导出的原始题目数据
输出: 复习资料/第XX章_测验.md + 复习资料/内燃机学_小测题库汇编.docx（零依赖 OOXML）
仅用 Python 标准库。
"""
import json
import os
import re
import sys
import zipfile
import urllib.request

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
OUT = os.path.join(BASE, "复习资料")
IMGDIR = os.path.join(OUT, "images")

TYPE_NAMES = {1: "单选题", 2: "多选题", 3: "填空题", 4: "判断题"}
# 题型排序: 选择题(单选/多选) → 判断题 → 填空题
TYPE_SEQ = [1, 2, 4, 3]
LETTERS = "ABCDEFGHIJ"

ZW = re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u202a-\u202e]")
TAG = re.compile(r"<[^>]+>")
IMG = re.compile(r'<img[^>]*src="([^"]+)"[^>]*>', re.I)


def clean_text(s):
    if not s:
        return ""
    s = ZW.sub("", s)
    s = TAG.sub("", s)
    # 数字/十六进制 HTML 实体（零宽字符常以实体形式残留在题干里）
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#39;", "'").replace("&rlm;", "").replace("&lrm;", "")
    s = ZW.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def get_images(html):
    if not html:
        return []
    return IMG.findall(html)


def download_image(url, cache={}):
    """下载图片到本地, 返回本地文件名"""
    if url in cache:
        return cache[url]
    os.makedirs(IMGDIR, exist_ok=True)
    fname = "img_" + re.sub(r"[^A-Za-z0-9]", "", url)[-40:] + ".png"
    if not fname.strip("img_.") or len(fname) < 8:
        fname = "img_%d.png" % abs(hash(url))
    path = os.path.join(IMGDIR, fname)
    if not os.path.exists(path):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r, open(path, "wb") as f:
                f.write(r.read())
        except Exception as e:
            print("  [warn] 图片下载失败 %s: %s" % (url[:80], e))
            return None
    cache[url] = fname
    return fname


def answer_of(q):
    """返回 (答案文本, 答案字母列表或None)"""
    t = q.get("type")
    if t in (1, 2, 4):
        opts = q.get("options") or []
        idx = [i for i, o in enumerate(opts) if o.get("answer")]
        letters = [LETTERS[i] for i in idx]
        texts = [clean_text(opts[i].get("content") or opts[i].get("contentHtml") or "") for i in idx]
        if t == 4:
            return ("正确" if texts and texts[0] == "正确" else "错误") if texts else "/".join(letters), letters
        label = "、".join(letters) + ("  " + "；".join(texts) if texts else "")
        return label, letters
    if t == 3:
        ans = q.get("stdAnswer")
        if isinstance(ans, list):
            ans = "；".join(str(a) for a in ans)
        ans = clean_text(str(ans)) if ans else "(未获取)"
        # 平台多答案分隔符: 做功##%_YZPRLFH_%##作功
        alts = [a.strip() for a in ans.split("##%_YZPRLFH_%##") if a.strip()]
        if len(alts) > 1:
            ans = alts[0] + "（或：" + "、".join(alts[1:]) + "）"
        return ans, None
    return "(未知题型)", None


CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn_to_int(s):
    if s == "十":
        return 10
    if len(s) == 1:
        return CN_NUM.get(s, 999)
    if s[0] == "十":
        return 10 + CN_NUM.get(s[1], 0)
    if s[-1] == "十":
        return CN_NUM.get(s[0], 0) * 10
    return CN_NUM.get(s[0], 0) * 10 + CN_NUM.get(s[-1], 0)


def load_quizzes():
    quizzes = []
    for fn in sorted(os.listdir(DATA)):
        m = re.match(r"quiz_(\d+)\.json$", fn)
        if not m:
            continue
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            d = json.load(f)
        quizzes.append(d)
    # 按章名中的中文数字排序（第一章 → 1）
    def chapno(d):
        m = re.search(r"第([一二三四五六七八九十]+)章", d.get("name", ""))
        return cn_to_int(m.group(1)) if m else 999
    quizzes.sort(key=chapno)
    return quizzes


def group_questions(qs):
    groups = {}
    for q in qs:
        groups.setdefault(q.get("type"), []).append(q)
    for t in groups:
        groups[t].sort(key=lambda q: (
            q.get("position") if isinstance(q.get("position"), (int, float)) else 10 ** 9,
            q.get("id") or 0,
        ))
    return groups


def render_md_quiz(d, img_map):
    name = d["name"]
    lines = ["# %s" % name, ""]
    qs = list(d["questions"].values())
    total = sum(q.get("score") or 0 for q in qs)
    lines.append("> 共 %d 题，合计 %.0f 分。答案已标注。" % (len(qs), total))
    lines.append("")
    groups = group_questions(qs)
    no = 0
    for t in TYPE_SEQ:
        if t not in groups:
            continue
        lines.append("## %s" % TYPE_NAMES.get(t, "其他(%s)" % t))
        lines.append("")
        for q in groups[t]:
            no += 1
            title = clean_text(q.get("title") or q.get("titleText") or "")
            lines.append("**%d.** %s（%s，%g分）" % (no, title, TYPE_NAMES.get(t, ""), q.get("score") or 0))
            # 题干图片
            for url in get_images(q.get("titleHtml")):
                local = img_map.get(url)
                if local:
                    lines.append("")
                    lines.append("![题图](images/%s)" % local)
            ans, letters = answer_of(q)
            opts = q.get("options") or []
            if opts:
                lines.append("")
                for i, o in enumerate(opts):
                    content = clean_text(o.get("content") or o.get("contentHtml") or "")
                    mark = " ✅" if o.get("answer") else ""
                    lines.append("- %s. %s%s" % (LETTERS[i], content, mark))
                    for url in get_images(o.get("contentHtml")):
                        local = img_map.get(url)
                        if local:
                            lines.append("  ![选项图](images/%s)" % local)
            lines.append("")
            lines.append("> **答案：%s**" % ans)
            analyse = q.get("analyse") or (q.get("options") and [o.get("analyse") for o in opts if o.get("analyse")])
            if analyse:
                if isinstance(analyse, list):
                    analyse = "；".join(clean_text(a) for a in analyse if a)
                else:
                    analyse = clean_text(str(analyse))
                if analyse:
                    lines.append(">")
                    lines.append("> 解析：%s" % analyse)
            lines.append("")
    return "\n".join(lines)


# ---------------- DOCX (raw OOXML) ----------------

def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def p_par(runs, style=None, indent=0):
    ppr = []
    if style:
        ppr.append('<w:pStyle w:val="%s"/>' % style)
    if indent:
        ppr.append('<w:ind w:left="%d"/>' % indent)
    x = "<w:p>" + ("<w:pPr>%s</w:pPr>" % "".join(ppr) if ppr else "")
    for run in runs:
        if not isinstance(run, tuple):
            run = (run, False, None)
        text, bold, color = run
        rpr = ""
        if bold or color:
            rpr = "<w:rPr>" + ("<w:b/>" if bold else "") + \
                  ("<w:color w:val=\"%s\"/>" % color if color else "") + "</w:rPr>"
        x += '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (rpr, esc(text))
    return x + "</w:p>"


def p_image(fname, rid_n=[0]):
    """内嵌图片段落 (EMU: 1px≈9525, 宽度上限 450px)"""
    from struct import unpack
    path = os.path.join(IMGDIR, fname)
    rid_n[0] += 1
    rid = "rimg%d" % rid_n[0]
    # 读取 PNG 尺寸 (IHDR)
    w = h = 300
    try:
        with open(path, "rb") as f:
            data = f.read(33)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = unpack(">II", data[16:24])
    except Exception:
        pass
    scale = min(1.0, 450.0 / w)
    cx, cy = int(w * 9525 * scale), int(h * 9525 * scale)
    return ('<w:p><w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
            '<wp:extent cx="%d" cy="%d"/><wp:docPr id="%d" name="%s"/>'
            '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
            '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            '</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>'
            % (cx, cy, rid_n[0], rid, rid_n[0], rid, rid, cx, cy)), rid, path


def build_docx(quizzes, img_map, out_path):
    rid_n = [0]
    rels = []          # (rid, target)
    media = []         # (path, name)
    body = []
    no = 0
    for d in quizzes:
        body.append(p_par([d["name"]], style="Heading1"))
        qs = list(d["questions"].values())
        groups = group_questions(qs)
        for t in TYPE_SEQ:
            if t not in groups:
                continue
            body.append(p_par([TYPE_NAMES.get(t, "其他")], style="Heading2"))
            for q in groups[t]:
                no += 1
                title = clean_text(q.get("title") or q.get("titleText") or "")
                body.append(p_par([("%d. %s（%s，%g分）" % (no, title, TYPE_NAMES.get(t, ""), q.get("score") or 0), True, None)]))
                for url in get_images(q.get("titleHtml")):
                    local = img_map.get(url)
                    if local:
                        xml, rid, path = p_image(local, rid_n)
                        body.append(xml)
                        rels.append((rid, "media/" + local))
                        media.append((path, local))
                ans, letters = answer_of(q)
                opts = q.get("options") or []
                for i, o in enumerate(opts):
                    content = clean_text(o.get("content") or o.get("contentHtml") or "")
                    mark = " ✔" if o.get("answer") else ""
                    color = "008000" if o.get("answer") else None
                    body.append(p_par([("%s. %s%s" % (LETTERS[i], content, mark), o.get("answer", False), color)], indent=360))
                    for url in get_images(o.get("contentHtml")):
                        local = img_map.get(url)
                        if local:
                            xml, rid, path = p_image(local, rid_n)
                            body.append(xml)
                            rels.append((rid, "media/" + local))
                            media.append((path, local))
                body.append(p_par([("答案：%s" % ans, True, "C00000")], indent=360))
                body.append(p_par([("", False, None)]))

    CT = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Default Extension="png" ContentType="image/png"/>
<Default Extension="jpeg" ContentType="image/jpeg"/>
<Default Extension="jpg" ContentType="image/jpeg"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>'''
    RELS = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''
    doc_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>']
    for rid, target in rels:
        doc_rels.append('<Relationship Id="%s" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="%s"/>' % (rid, target))
    doc_rels.append('</Relationships>')
    STYLES = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:style w:type="paragraph" w:styleId="Normal" w:default="1"><w:name w:val="Normal"/><w:rPr><w:rFonts w:ascii="Calibri" w:eastAsia="微软雅黑"/><w:sz w:val="22"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="0"/><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="34"/><w:color w:val="1F4E79"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/><w:pPr><w:outlineLvl w:val="1"/><w:spacing w:before="180" w:after="90"/></w:pPr><w:rPr><w:b/><w:sz w:val="28"/><w:color w:val="2E74B5"/></w:rPr></w:style>
</w:styles>'''
    NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
          'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
          'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
    DOCUMENT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document %s><w:body>%s'
                '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                '<w:pgMar w:top="1440" w:right="1200" w:bottom="1440" w:left="1200"/></w:sectPr>'
                '</w:body></w:document>' % (NS, "".join(body)))

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOCUMENT)
        z.writestr("word/styles.xml", STYLES)
        z.writestr("word/_rels/document.xml.rels", "".join(doc_rels))
        for path, name in media:
            z.write(path, "word/media/" + name)


def main():
    os.makedirs(OUT, exist_ok=True)
    quizzes = load_quizzes()
    if not quizzes:
        print("data/ 下没有 quiz_*.json，请先导出数据")
        sys.exit(1)

    # 收集并下载所有图片
    img_map = {}
    n_img = 0
    for d in quizzes:
        for q in d["questions"].values():
            for url in get_images(q.get("titleHtml")):
                if url not in img_map:
                    local = download_image(url)
                    if local:
                        img_map[url] = local
                        n_img += 1
            for o in q.get("options") or []:
                for url in get_images(o.get("contentHtml")):
                    if url not in img_map:
                        local = download_image(url)
                        if local:
                            img_map[url] = local
                            n_img += 1
    print("图片: %d 张" % n_img)

    # Markdown
    for d in quizzes:
        md = render_md_quiz(d, img_map)
        out = os.path.join(OUT, "%s.md" % d["name"])
        with open(out, "w", encoding="utf-8") as f:
            f.write(md)
        print("写入 %s（%d 题）" % (out, len(d["questions"])))

    # 合并 Markdown
    parts = ["# 《内燃机学》章节小测题库汇编", "",
             "> 浙江大学《内燃机学》中国大学MOOC（ZJU-1460864162，第6次开课）", ""]
    for d in quizzes:
        parts.append(render_md_quiz(d, img_map))
        parts.append("\n---\n")
    with open(os.path.join(OUT, "题库汇编.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts))
    print("写入 题库汇编.md")

    # DOCX
    docx_path = os.path.join(OUT, "内燃机学_小测题库汇编.docx")
    build_docx(quizzes, img_map, docx_path)
    print("写入 %s" % docx_path)


if __name__ == "__main__":
    main()
