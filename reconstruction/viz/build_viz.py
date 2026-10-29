"""Build the Charter viz from the cross-link (data/crosslink) and the raw samples (data/raw).

Everything the page needs is inlined, so it is one self-contained HTML file:
  - the ordered document (data/crosslink/document.json), each target with its links sorted
    unprompted -> near -> echo, then by coverage
  - the full prompt, CoT and answer of every linked sample, gzip+base64 (decompressed in the browser), so a
    click on any source opens the whole transcript with the matched spans highlighted
Writes charter_viz.html (Google Fonts link) and charter_viz_standalone.html (fonts embedded, no network).
Usage: python3 reconstruction/viz/build_viz.py   (after reconstruction/crosslink.py)
"""
import base64, gzip, json, re, urllib.request
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
XL, RAW = REPO / "data/crosslink", REPO / "data/raw"
CLS = {"unprompted": 0, "near": 1, "echo": 2}

doc = json.load(open(XL / "document.json"))
links = json.load(open(XL / "links.json"))
samples = {s["sid"]: s for s in json.load(open(XL / "samples.json"))}
manifest = {m["run"]: m for m in json.load(open(RAW / "runs.json"))}

by_target = defaultdict(list)
for l in links:
    by_target[l["target"]].append(l)
used = sorted({l["sid"] for l in links}, key=lambda s: (samples[s]["run"], s))
idx = {sid: i for i, sid in enumerate(used)}


def pack(target):
    rows = sorted(by_target.get(target, []), key=lambda l: (CLS[l["cls"]], -l["coverage"], l["sid"]))
    return [[idx[l["sid"]], CLS[l["cls"]], l["coverage"], l["spans"]] for l in rows]


items = []
for it in doc["items"]:
    x = {k: v for k, v in it.items() if k not in ("id",)}
    if it["t"] in ("P", "V", "H"):
        x["id"] = it["id"]
        x["links"] = pack(it["id"])
    items.append(x)
excluded = [{**e, "links": pack(e["pid"])} for e in doc["excluded"]]

texts = {}
for f in sorted((RAW / "runs").glob("*.jsonl")):
    for line in open(f):
        r = json.loads(line)
        if r["sid"] in idx:
            texts[r["sid"]] = [
                "\n".join(m["content"] for m in r["messages"] if isinstance(m.get("content"), str)),
                r["reasoning"], r["content"]]
blob = base64.b64encode(gzip.compress(json.dumps([texts[s] for s in used], ensure_ascii=False).encode(), 9)).decode()

runs = sorted({samples[s]["run"] for s in used})
data = {
    "meta": {"n_samples": len(samples), "n_linked": len(used), "params": doc["params"]},
    "runs": [{"run": r, "n": sum(1 for s in samples.values() if s["run"] == r)} for r in runs],
    "samples": [[samples[s]["run"], samples[s]["prompt_id"], samples[s]["rep"], samples[s]["effort"], samples[s]["provider"]] for s in used],
    "items": items, "excluded": excluded,
}
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
template = (HERE / "charter_viz.template.html").read_text()
assert "/*__DATA__*/" in template and "/*__TEXTS__*/" in template
page = template.replace("/*__DATA__*/", payload).replace("/*__TEXTS__*/", blob)
out = HERE / "charter_viz.html"
out.write_text(page)
n_p = sum(it["t"] in ("P", "V") for it in items)
print(f"{out}  {out.stat().st_size / 1e6:.2f} MB  passages={n_p} linked samples={len(used)} links={len(links)}")

# ---- standalone copy: fonts embedded as data URIs, no network at all ----
FONTS_URL = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', template).group(1)
font_css = HERE / "fonts_inline.css"  # cached, so later builds work offline
if not font_css.exists():
    ua = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
    css = urllib.request.urlopen(urllib.request.Request(FONTS_URL, headers=ua)).read().decode()
    keep = []
    for subset, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
        if subset in ("latin", "latin-ext"):
            url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
            keep.append(block.replace(url, "data:font/woff2;base64," + base64.b64encode(urllib.request.urlopen(url).read()).decode()))
    font_css.write_text("\n".join(keep))
body = re.sub(r'<link rel="(?:preconnect|stylesheet)"[^>]*>\n?', "", page)
title = re.search(r"<title>.*?</title>", body).group(0)
body = body.replace(title + "\n", "", 1)
standalone = HERE / "charter_viz_standalone.html"  # also the page served by GitHub Pages
DESC = ("Muse Spark Open's Charter reconstructed from its chain of thought: every passage links to the samples "
        "that wrote it, unprompted ones first, with full transcripts one click away.")
standalone.write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    f'<meta name="description" content="{DESC}">\n<meta property="og:title" content="Muse\'s Charter, Reconstructed">\n'
    f'<meta property="og:description" content="{DESC}">\n<meta property="og:type" content="article">\n'
    f"{title}\n<style>\n{font_css.read_text()}\n[hidden]{{display:none!important}}\nbody{{margin:0}}\n</style>\n"
    f"</head>\n<body>\n{body}\n</body>\n</html>\n")
print(f"{standalone}  {standalone.stat().st_size / 1e6:.2f} MB  (no external requests)")
