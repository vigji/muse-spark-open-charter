#!/usr/bin/env python3
"""Report where a passage's unprompted samples keep agreeing past its edges (run after crosslink.py).

For every passage, take the unprompted samples whose best match covers most of it and walk outward word by word
(folded as in crosslink.py) while >= AGREE of them still agree. An extension whose words are not already in the
document is text the spec is missing: the report shows it in the wording of an agreeing sample, to be added to
charter_spec.json by hand. Read-only; nothing is written.
Usage: python3 reconstruction/grow.py [min_words]
"""
import json, sys
from collections import Counter
from crosslink import OUT, RAW, SPEC, tokens

AGREE, MIN_SAMPLES, MAX_WORDS, FULL = 0.6, 3, 200, 0.8
min_words = int(sys.argv[1]) if len(sys.argv) > 1 else 4

spec = json.load(open(SPEC))["items"]
doc_words = [t[0] for it in spec if it["t"] in ("P", "V") for t in tokens(it["text"])]
doc4 = {tuple(doc_words[i:i + 4]) for i in range(len(doc_words) - 3)}
links = json.load(open(OUT / "links.json"))
rows = {}
for f in (RAW / "runs").glob("*.jsonl"):
    for line in open(f):
        r = json.loads(line); rows[r["sid"]] = r


def context(link, n_words):
    """(left words reversed, right words, left toks reversed, right toks, text) around the longest matched span"""
    r = rows[link["sid"]]
    best = max(((k, a, b) for k, sp in link["spans"].items() if k != "prompt" for a, b in sp), key=lambda x: x[2] - x[1])
    k, a, b = best
    toks = tokens(r[k])
    inside = sum(1 for t in toks if a <= t[1] < b)
    if inside < FULL * n_words: return None
    left = [t for t in toks if t[2] <= a][::-1][:MAX_WORDS]
    right = [t for t in toks if t[1] >= b][:MAX_WORDS]
    return left, right, r[k]


def agree(sides):
    """longest prefix on which >= AGREE of the samples agree; returns (n, a sample that agrees on all of it)"""
    alive, n = sides, 0
    while True:
        c = Counter(s[n][0] for s in alive if len(s) > n)
        if not c: break
        w, m = c.most_common(1)[0]
        if m < AGREE * len(sides): break
        alive, n = [s for s in alive if len(s) > n and s[n][0] == w], n + 1
    return n, alive[0] if alive else None


def missing(words):
    return sum(tuple(words[i:i + 4]) not in doc4 for i in range(len(words) - 3))


for it in spec:
    if it["t"] != "P": continue
    n_words = len(tokens(it["text"]))
    ctx = [c for l in links if l["target"] == it["pid"] and l["cls"] == "unprompted" for c in [context(l, n_words)] if c]
    if len(ctx) < MIN_SAMPLES: continue
    for side in ("left", "right"):
        n, s = agree([c[0] if side == "left" else c[1] for c in ctx])
        if n < min_words: continue
        toks = s[:n][::-1] if side == "left" else s[:n]
        if missing([t[0] for t in toks]) < 2: continue  # the extension is a neighbouring passage already in the doc
        text = next(c[2] for c in ctx if (c[0] if side == "left" else c[1]) is s)
        surface = " ".join(text[toks[0][1]:toks[-1][2]].split())
        print(f"{it['pid']} {side:5s} n={len(ctx)}  {it['text'][:60]!r}\n    + {surface}\n")
