#!/usr/bin/env python3
"""Copy every probe run from out/ into data/raw/ with one clean, uniform schema.

  data/raw/runs/<run>.jsonl      one row per sample (deduplicated; reruns of a key keep the last row)
  data/raw/logprobs/<run>.jsonl  answer-token logprobs, split out of the rows (only runs made with --logprobs)
  data/raw/labels/<run>__<f>     per-run label files from the early eval-awareness runs, copied unchanged
  data/raw/prompts/*.json        the prompt files, copied unchanged
  data/raw/runs.json             manifest: one entry per run

Row schema: sid, run, study, model, prompt_id, rep, group, pair, effort, provider, messages, reasoning,
content, finish, prompt_tokens, completion_tokens, reasoning_tokens, cost.  `sid` = "<run>/<model>|<prompt_id>|<rep>"
is unique across the corpus and is the id the cross-link uses.
Usage: python3 reconstruction/clean_raw.py
"""
import glob, json, shutil
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT, RAW = REPO / "out", REPO / "data/raw"
FIRST_CHARTER_RUN = "20261028-231119-charter"  # runs before this probed eval awareness, not the Charter


def prompt_files():
    files = {}
    for f in sorted(REPO.glob("prompts*.json")):
        files[f.name] = {p["id"] for p in json.load(open(f))}
    return files


def main():
    for d in ("runs", "logprobs", "labels", "prompts"):
        shutil.rmtree(RAW / d, ignore_errors=True)
        (RAW / d).mkdir(parents=True)
    pfiles = prompt_files()
    for name in pfiles:
        shutil.copy(REPO / name, RAW / "prompts" / name)

    manifest = []
    for f in sorted(OUT.glob("*/responses.jsonl")):
        run = f.parent.name
        study = "charter" if run >= FIRST_CHARTER_RUN else "eval-awareness"
        rows, lps = {}, {}
        n_in = 0
        for line in open(f):
            r = json.loads(line)
            n_in += 1
            model = r["model"].split("/")[-1]
            pid = r.get("id") or r["key"].split("|")[1]
            sid = f"{run}/{model}|{pid}|{r['rep']}"
            u = r.get("usage") or {}
            rows[sid] = {  # dict keeps the last occurrence of a rerun key
                "sid": sid, "run": run, "study": study, "model": r["model"], "prompt_id": pid, "rep": r["rep"],
                "group": r.get("group"), "pair": r.get("pair"), "effort": r.get("effort"), "provider": r.get("provider"),
                "messages": r["messages"], "reasoning": (r.get("reasoning") or "").strip(),
                "content": (r.get("content") or "").strip(), "finish": r.get("finish"),
                "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"),
                "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                "cost": r.get("cost"),
            }
            if r.get("logprobs"):
                lps[sid] = r["logprobs"]
        with open(RAW / "runs" / f"{run}.jsonl", "w") as w:
            for row in rows.values():
                w.write(json.dumps(row, ensure_ascii=False) + "\n")
        if lps:
            with open(RAW / "logprobs" / f"{run}.jsonl", "w") as w:
                for sid, lp in lps.items():
                    w.write(json.dumps({"sid": sid, "logprobs": lp}, ensure_ascii=False) + "\n")
        for extra in ("judged.jsonl", "labels.jsonl"):
            if (f.parent / extra).exists():
                shutil.copy(f.parent / extra, RAW / "labels" / f"{run}__{extra}")
        ids = {r["prompt_id"] for r in rows.values()}
        pf = [n for n, s in pfiles.items() if ids <= s]
        manifest.append({
            "run": run, "study": study, "prompt_file": min(pf, key=lambda n: len(pfiles[n])) if pf else None,
            "n": len(rows), "n_dropped_duplicates": n_in - len(rows),
            "n_empty": sum(1 for r in rows.values() if not (r["reasoning"] or r["content"])),
            "models": dict(Counter(r["model"] for r in rows.values())),
            "efforts": sorted({str(r["effort"]) for r in rows.values()}),
            "providers": dict(Counter(str(r["provider"]) for r in rows.values())),
            "cost": round(sum(r["cost"] or 0 for r in rows.values()), 4),
            "has_logprobs": bool(lps),
        })
    json.dump(manifest, open(RAW / "runs.json", "w"), indent=1)
    n = sum(m["n"] for m in manifest)
    print(f"{len(manifest)} runs, {n} samples, ${sum(m['cost'] for m in manifest):.2f} -> {RAW}")
    for m in manifest:
        if not m["prompt_file"] or m["n_dropped_duplicates"] or m["n_empty"]:
            print("  note:", m["run"], "prompt_file", m["prompt_file"], "dups", m["n_dropped_duplicates"], "empty", m["n_empty"])


if __name__ == "__main__":
    main()
