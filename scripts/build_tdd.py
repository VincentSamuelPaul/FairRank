"""Render docs/TDD.md to a PDF (screenshots embedded) with headless Chromium. Run via scripts/build-submission.sh."""
import pathlib
import re
import sys

import markdown
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(".").resolve()
SRC = ROOT / "docs" / "TDD.md"
OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "submission/FairRank-TDD.pdf")

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm 15mm; }
body { font: 10.2pt/1.5 'Inter', 'Helvetica Neue', Arial, sans-serif; color: #1b2236; }
h1 { font-size: 22pt; margin: 0 0 6pt; letter-spacing: -0.02em; }
h2 { font-size: 14.5pt; margin: 20pt 0 6pt; padding-top: 6pt; border-top: 1px solid #d8d3c8; letter-spacing: -0.01em; page-break-after: avoid; }
p { margin: 5pt 0; } em { color: #4a5266; }
a { color: #1f4fa3; text-decoration: none; }
code { font: 9pt 'SFMono-Regular', Consolas, monospace; background: #f1ede4; padding: 0 3px; border-radius: 3px; }
pre { background: #f1ede4; padding: 8pt 10pt; border-radius: 6px; font-size: 8.4pt; line-height: 1.35; page-break-inside: avoid; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 6pt 0 10pt; font-size: 8.8pt; page-break-inside: auto; }
tr { page-break-inside: avoid; }
th, td { border: 1px solid #d8d3c8; padding: 4pt 6pt; vertical-align: top; text-align: left; }
th { background: #f1ede4; }
ul, ol { margin: 4pt 0 4pt 16pt; padding: 0; } li { margin: 2pt 0; }
.shot { max-height: 430px; overflow: hidden; border: 1px solid #d8d3c8; border-radius: 8px; background: #0a0f1e; margin: 8pt 0 2pt; page-break-inside: avoid; }
.shot img { display: block; width: 100%; }
.shot.phone { width: 36%; margin: 8pt auto 2pt; max-height: 600px; }
p.cap { margin-top: 0; font-size: 8.8pt; page-break-inside: avoid; }
"""

html = markdown.markdown(SRC.read_text(), extensions=["tables", "fenced_code"])
html = re.sub(r"<p><img alt=\"([^\"]*)\" src=\"([^\"]+)\" ?/?>\s*(?:</p>\s*<p>)?<em>", r'<div class="shot"><img alt="\1" src="\2"></div><p class="cap"><em>', html)
html = re.sub(r'<div class="shot"><img alt="([^"]*)" src="([^"]*phone[^"]*)">', r'<div class="shot phone"><img alt="\1" src="\2">', html)
html = f"<!doctype html><html><head><meta charset='utf-8'><title>FairRank: Technical Design Document</title><base href='file://{ROOT}/docs/'><style>{CSS}</style></head><body>{html}</body></html>"
tmp = ROOT / ".review" / "tdd.html"
tmp.parent.mkdir(exist_ok=True)
tmp.write_text(html)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--allow-file-access-from-files"])
    pg = b.new_page()
    pg.goto(f"file://{tmp}")
    pg.wait_for_load_state("load")
    pg.evaluate("Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => { i.onload = i.onerror = r })))")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    pg.pdf(path=str(OUT), format="A4", print_background=True, margin={"top": "16mm", "bottom": "18mm", "left": "15mm", "right": "15mm"},
           display_header_footer=True, header_template="<span></span>",
           footer_template="<div style='font-size:8px;color:#6b7280;width:100%;text-align:center'>FairRank · Technical Design Document · <span class='pageNumber'></span> / <span class='totalPages'></span></div>")
    b.close()
print("wrote", OUT)
