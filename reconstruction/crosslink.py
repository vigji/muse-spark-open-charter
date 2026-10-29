#!/usr/bin/env python3
"""Cross-link the editorial spec (reconstruction/charter_spec.json) to the raw samples (data/raw/runs).

A sample supports a passage when >= MIN_COV of the passage's word 6-grams occur in its reasoning or answer.
Words are compared after folding first-person and "it" onto Muse (the CoT flips between "I must", "it must" and
"Muse must") and dropping the hedges the samples add or omit at will (materially, reasonably, generally).
Each link is then classed by how much of the passage that sample's OWN prompt already contained:
  unprompted  the prompt shares no 6-gram with the passage and < NEAR3 of its 3-grams (the model produced it)
  near        the prompt shares some 6-grams, or >= NEAR3 of the 3-grams (partial or paraphrased cue)
  echo        the prompt contains >= MIN_COV of the passage's 6-grams (verification/MCQ prompts; not evidence)
Only `unprompted` links count as support. Headings are linked the same way, on their title.

Writes data/crosslink/:
  samples.json   metadata of every linked-corpus sample (text stays in data/raw/runs/<run>.jsonl, row `sid`)
  document.json  the ordered reconstruction: headings, notes, gaps, passages (+ verdicts, tests, support stats)
  links.json     one row per (target, sample): cls, coverage, prompt overlap, char spans in reasoning/content
                 (and, for near/echo links, in the prompt = the user messages joined by newlines)
Usage: python3 reconstruction/crosslink.py
"""
import json, re
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW, OUT = REPO / "data/raw", REPO / "data/crosslink"
SPEC = REPO / "reconstruction/charter_spec.json"
MODEL = "meta/muse-spark-open"
N, MIN_COV, NEAR3 = 6, 0.5, 0.35
TOK = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")
FOLD = {"i": "muse", "me": "muse", "it": "muse", "my": "its", "myself": "itself", "am": "is"}
HEDGES = {"materially", "reasonably", "generally"}


def tokens(text):
    """[(word, start, end)]: folded words without apostrophes or hedges, offsets into the original text"""
    low = text.lower().replace("’", "'")  # same length, offsets still valid
    out = []
    for m in TOK.finditer(low):
        w = m.group().replace("'", "")
        if w not in HEDGES:
            out.append((FOLD.get(w, w), m.start(), m.end()))
    return out


def grams(words, n):
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)}


def spans(toks, g, n):
    """char spans of the token runs whose n-grams are in g"""
    hit = [False] * len(toks)
    words = [t[0] for t in toks]
    for i in range(len(words) - n + 1):
        if tuple(words[i:i + n]) in g:
            for j in range(i, i + n): hit[j] = True
    out, i = [], 0
    while i < len(toks):
        if hit[i]:
            j = i
            while j + 1 < len(toks) and hit[j + 1]: j += 1
            out.append([toks[i][1], toks[j][2]]); i = j + 1
        else:
            i += 1
    return out


def load_samples():
    S = []
    for f in sorted((RAW / "runs").glob("*.jsonl")):
        for line in open(f):
            r = json.loads(line)
            if r["model"] != MODEL or r["study"] != "charter": continue
            prompt = "\n".join(m["content"] for m in r["messages"] if isinstance(m.get("content"), str))
            fields = {k: tokens(r[k]) for k in ("reasoning", "content")}
            ptoks = tokens(prompt)
            pw = [t[0] for t in ptoks]
            S.append({"row": r, "fields": fields, "g": {k: grams([t[0] for t in v], N) for k, v in fields.items()},
                      "ptoks": ptoks, "p6": grams(pw, N), "p3": grams(pw, 3)})
    return S


def link(target_id, text, S, short_exact=False):
    words = [t[0] for t in tokens(text)]
    n = min(N, len(words))
    g, g3 = grams(words, n), grams(words, 3)
    rows = []
    for s in S:
        found = set()
        for k in ("reasoning", "content"):
            found |= g & (s["g"][k] if n == N else grams([t[0] for t in s["fields"][k]], n))
        cov = len(found) / len(g)
        if cov < MIN_COV: continue
        p6 = len(g & s["p6"]) / len(g) if n == N else 0.0  # short targets: exact check in main()
        p3 = len(g3 & s["p3"]) / max(1, len(g3))
        cls = "echo" if p6 >= MIN_COV else "near" if p6 > 0 or p3 >= NEAR3 else "unprompted"
        sp = {k: spans(s["fields"][k], g, n) for k in ("reasoning", "content")}
        if cls != "unprompted":  # show what the prompt already contained
            sp["prompt"] = spans(s["ptoks"], g, n) if p6 > 0 else spans(s["ptoks"], g3, 3)
        rows.append({"target": target_id, "sid": s["row"]["sid"], "cls": cls, "coverage": round(cov, 3),
                     "prompt6": round(p6, 3), "prompt3": round(p3, 3),
                     "spans": {k: v for k, v in sp.items() if v}})
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = load_samples()
    # short targets (< 6 words) are matched on their full word sequence; prompt check needs the prompt words
    prompt_words = {s["row"]["sid"]: " ".join(t[0] for t in tokens(
        "\n".join(m["content"] for m in s["row"]["messages"] if isinstance(m.get("content"), str)))) for s in S}
    spec = json.load(open(SPEC))
    links, doc = [], []
    for i, it in enumerate(spec["items"]):
        it = dict(it)
        if it["t"] in ("P", "V") or it["t"] == "H":
            tid = it["pid"] if it["t"] != "H" else f"h{i}"
            text = it.get("text") or it["title"]
            text = re.sub(r"[*_`]|…", " ", text)
            rows = link(tid, text, S)
            short = " ".join(t[0] for t in tokens(text))
            for r in rows:  # exact prompt check for short targets
                if len(short.split()) < N and short in prompt_words[r["sid"]]:
                    r["cls"], r["prompt6"] = "echo", 1.0
            links += rows
            by = defaultdict(set)
            for r in rows: by[r["cls"]].add(r["sid"])
            runs_u = {sid.split("/")[0] for sid in by["unprompted"]}
            nu = len(by["unprompted"])
            it["id"] = tid
            it["support"] = {"unprompted": nu, "near": len(by["near"]), "echo": len(by["echo"]), "runs_unprompted": len(runs_u),
                             "tier": "solid" if nu >= 3 and len(runs_u) >= 2 else "weak" if nu else "none"}
        doc.append(it)
    for e in spec.get("excluded", []):
        rows = link(e["pid"], re.sub(r"[*_`]|…", " ", e["text"]), S)
        links += rows
    json.dump({"items": doc, "excluded": spec.get("excluded", []),
               "params": {"model": MODEL, "ngram": N, "min_coverage": MIN_COV, "near_3gram": NEAR3}},
              open(OUT / "document.json", "w"), indent=1, ensure_ascii=False)
    json.dump(links, open(OUT / "links.json", "w"), ensure_ascii=False)
    meta = [{k: s["row"][k] for k in ("sid", "run", "prompt_id", "rep", "group", "effort", "provider")} for s in S]
    json.dump(meta, open(OUT / "samples.json", "w"), indent=1)
    P = [x for x in doc if x["t"] in ("P", "V")]
    tiers = defaultdict(int)
    for x in P: tiers[x["support"]["tier"]] += 1
    cls = defaultdict(int)
    for r in links: cls[r["cls"]] += 1
    print(f"{len(S)} samples, {len(P)} passages {dict(tiers)}, {len(links)} links {dict(cls)} -> {OUT}")


if __name__ == "__main__":
    main()
