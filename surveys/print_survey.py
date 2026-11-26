#!/usr/bin/env python3
"""print_survey.py: a printable PDF view of a Qualtrics survey file (.qsf), like Qualtrics' own print view.

The PDF lists the survey flow (blocks, branches, randomizers, the embedded data each element sets, web
services, ends of survey) and then every block in flow order with every question: its export tag, its type,
its text as the participant reads it, its answer options, whether it has display logic, and whether a page
script draws part of it. Choice pages whose options are drawn by a page script from embedded data show the
question text and say so; the values the script draws from are the embedded data listed in the flow. Pictures
are named, not loaded, and the browser that prints the PDF is kept off the network.

Used for the four calibration studies: python surveys/print_survey.py writes
calibration/<study>/survey/<survey>.pdf next to each fielded survey file; one file can be printed with
python surveys/print_survey.py <file.qsf> [<out.pdf>]. Needs playwright with Chromium. The PDF's creation
and modification dates are set to the date the study was fielded, so a rerun writes the same bytes.
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STUDIES = [("wave1", "calibration_wave1.qsf"), ("wave2", "calibration_wave2.qsf"),
           ("wave3", "calibration_wave3.qsf"), ("realism_study", "realism_study.qsf")]
FIELDED = "D:20260702000000+00'00'"          # July 2, 2026: the day all four studies ran

CSS = """
body{font-family:Arial,Helvetica,sans-serif;font-size:10.5pt;color:#1d1d1d;margin:0}
h1{font-size:15pt;margin:0 0 4pt}h2{font-size:12.5pt;margin:18pt 0 6pt;border-bottom:1px solid #999}
h3{font-size:11pt;margin:14pt 0 4pt;background:#eef1f4;padding:3pt 5pt}
.meta{color:#555;font-size:9pt;margin-bottom:10pt}
ul.flow{margin:2pt 0 2pt 12pt;padding-left:10pt}ul.flow li{margin:1.5pt 0}
.kind{font-weight:bold}.ed{color:#444;font-size:9pt;word-break:break-word}
.q{border:1px solid #cfd4da;border-radius:4px;padding:6pt 8pt;margin:6pt 0;page-break-inside:avoid}
.qhead{font-size:9pt;color:#555;margin-bottom:4pt}.qtext{margin:2pt 0 4pt}
.qtext img{display:none}.pic{display:inline-block;border:1px dashed #999;padding:2pt 5pt;font-size:9pt;color:#555}
ol.choices{margin:2pt 0 2pt 18pt;padding:0}.note{font-size:9pt;color:#6b4e00;margin-top:3pt}
.pb{font-size:8.5pt;color:#888;text-align:center;margin:4pt 0}
"""


def load(path):
    q = json.load(open(path, encoding="utf-8"))
    els = q["SurveyElements"]
    blocks = next(e for e in els if e["Element"] == "BL")["Payload"]
    blocks = list(blocks.values()) if isinstance(blocks, dict) else list(blocks)
    flow = next(e for e in els if e["Element"] == "FL")["Payload"]
    questions = {e["Payload"]["QuestionID"]: e["Payload"] for e in els if e["Element"] == "SQ"}
    return q.get("SurveyEntry", {}), {b["ID"]: b for b in blocks if "ID" in b}, flow, questions


def clean_html(text):
    text = re.sub(r"<script.*?</script>", "", text or "", flags=re.S | re.I)
    text = re.sub(r"\son\w+\s*=\s*(\"[^\"]*\"|'[^']*')", "", text, flags=re.I)
    text = re.sub(r"<img[^>]*src=[\"']([^\"']*)[\"'][^>]*>",
                  lambda m: f'<span class="pic">picture: {html.escape(os.path.basename(m.group(1)))}</span>',
                  text, flags=re.I)
    return text


def short(value, n=200):
    value = str(value)
    return value if len(value) <= n else value[:n] + " ..."


def flow_html(items, blocks, order):
    out = ['<ul class="flow">']
    for it in items:
        t = it.get("Type")
        if t in ("Standard", "Block"):
            b = blocks.get(it.get("ID"), {})
            order.append(it.get("ID"))
            out.append(f'<li><span class="kind">Block:</span> {html.escape(b.get("Description", it.get("ID", "")))}</li>')
        elif t == "Branch":
            out.append(f'<li><span class="kind">Branch:</span> {html.escape(it.get("Description", "") or "a condition")}')
            out.append(flow_html(it.get("Flow", []), blocks, order) + "</li>")
        elif t == "BlockRandomizer":
            n = len(it.get("Flow", []))
            k = it.get("SubSet", n)
            even = " evenly" if it.get("EvenPresentation") else ""
            out.append(f'<li><span class="kind">Randomizer:</span> presents {k} of the {n} elements below{even}')
            out.append(flow_html(it.get("Flow", []), blocks, order) + "</li>")
        elif t == "Group":
            out.append(f'<li><span class="kind">Group:</span> {html.escape(it.get("Description", ""))}')
            out.append(flow_html(it.get("Flow", []), blocks, order) + "</li>")
        elif t == "EmbeddedData":
            fields = it.get("EmbeddedData", [])
            parts = [f'{html.escape(f.get("Field", ""))} = {html.escape(short(f.get("Value", "")))}' if f.get("Value")
                     else html.escape(f.get("Field", "")) for f in fields]
            out.append(f'<li><span class="kind">Embedded data</span> <span class="ed">({len(fields)} fields): '
                       + "; ".join(parts) + "</span></li>")
        elif t == "WebService":
            out.append(f'<li><span class="kind">Web service:</span> {html.escape(it.get("URL", ""))}</li>')
        elif t == "EndSurvey":
            out.append('<li><span class="kind">End of survey</span></li>')
        else:
            out.append(f'<li><span class="kind">{html.escape(str(t))}</span></li>')
    out.append("</ul>")
    return "".join(out)


def question_html(q):
    tag = q.get("DataExportTag", q.get("QuestionID"))
    kind = "/".join(x for x in (q.get("QuestionType"), q.get("Selector"), q.get("SubSelector")) if x)
    parts = [f'<div class="q"><div class="qhead">{html.escape(str(tag))} &middot; {html.escape(kind)}</div>']
    if q.get("QuestionType") == "Timing":
        parts.append('<div class="qtext">(records the time spent on this page; not shown)</div>')
    elif q.get("QuestionType") == "Meta":
        parts.append('<div class="qtext">(records the browser, operating system and screen size; not shown)</div>')
    else:
        parts.append(f'<div class="qtext">{clean_html(q.get("QuestionText", ""))}</div>')
    choices = q.get("Choices") or {}
    if choices and q.get("QuestionType") not in ("Timing", "Meta"):
        order = [str(c) for c in (q.get("ChoiceOrder") or list(choices))]
        parts.append('<ol class="choices">' + "".join(
            f"<li>{clean_html(choices.get(c, {}).get('Display', ''))}</li>" for c in order if c in choices) + "</ol>")
    notes = []
    if q.get("DisplayLogic"):
        notes.append("shown only when its display condition holds")
    if q.get("QuestionJS"):
        notes.append("a page script runs on this page (for example, it draws the options from embedded data, "
                     "or holds the Next button until an option is chosen)")
    if notes:
        parts.append('<div class="note">Note: ' + "; ".join(notes) + ".</div>")
    parts.append("</div>")
    return "".join(parts)


def survey_html(path):
    entry, blocks, flow, questions = load(path)
    order = []
    flow_part = flow_html(flow.get("Flow", []), blocks, order)
    seen, sections = set(), []
    for bid in order + [b for b in blocks if b not in order]:
        if bid in seen or bid not in blocks:
            continue
        seen.add(bid)
        b = blocks[bid]
        if b.get("Type") == "Trash" or not b.get("BlockElements"):
            continue
        body = [f'<h3>Block: {html.escape(b.get("Description", bid))}</h3>']
        for el in b.get("BlockElements", []):
            if el.get("Type") == "Question" and el.get("QuestionID") in questions:
                body.append(question_html(questions[el["QuestionID"]]))
            elif el.get("Type") == "Page Break":
                body.append('<div class="pb">page break</div>')
        sections.append("".join(body))
    name = entry.get("SurveyName", os.path.basename(path))
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{html.escape(name)}</title>"
            f"<style>{CSS}</style></head><body><h1>{html.escape(name)}</h1>"
            f"<div class='meta'>A printable view of {html.escape(os.path.basename(path))}: the survey flow, then every "
            f"block and question in flow order. {len(questions)} questions in {len(seen)} blocks.</div>"
            f"<h2>Survey flow</h2>{flow_part}<h2>Blocks and questions</h2>{''.join(sections)}</body></html>")


def fix_dates(pdf_bytes):
    """Set the PDF's creation and modification dates to the fielding date (same length, so offsets hold)."""
    def rep(m):
        new = FIELDED.encode("latin-1")
        old = m.group(2)
        return m.group(1) + (new + b" " * (len(old) - len(new)) if len(new) <= len(old) else new[:len(old)])
    return re.sub(rb"(/(?:CreationDate|ModDate) \()(D:[^)]*)", rep, pdf_bytes)


def print_pdf(qsf, out, page):
    page.set_content(survey_html(qsf))
    page.pdf(path=out, format="Letter", print_background=True,
             margin={"top": "0.6in", "bottom": "0.6in", "left": "0.6in", "right": "0.6in"})
    data = open(out, "rb").read()
    with open(out, "wb") as fh:
        fh.write(fix_dates(data))


def main(argv):
    from playwright.sync_api import sync_playwright
    if argv:
        jobs = [(argv[0], argv[1] if len(argv) > 1 else os.path.splitext(argv[0])[0] + ".pdf")]
    else:
        jobs = [(os.path.join(ROOT, "calibration", s, "survey", f), os.path.join(ROOT, "calibration", s, "survey",
                 os.path.splitext(f)[0] + ".pdf")) for s, f in STUDIES]
    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        ctx = br.new_context()
        ctx.route("**/*", lambda route: route.abort() if not route.request.url.startswith(("data:", "about:"))
                  else route.continue_())
        page = ctx.new_page()
        for qsf, out in jobs:
            print_pdf(qsf, out, page)
            print(f"wrote {os.path.relpath(out, ROOT)} ({os.path.getsize(out) // 1024} KB)")
        br.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
