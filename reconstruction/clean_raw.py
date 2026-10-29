#!/usr/bin/env python3
"""Copy every probe run from out/ into data/raw/ with one clean, uniform schema.

  data/raw/runs/<run>.jsonl      one row per sample (deduplicated; reruns of a key keep the last row)

Only the transcripts are kept: logprobs, judge labels, prompt files and per-run metadata are left out.

Row schema: sid, run, study, model, prompt_id, rep, group, pair, effort, provider, messages, reasoning,
content, finish, prompt_tokens, completion_tokens, reasoning_tokens, cost.  `sid` = "<run>/<model>|<prompt_id>|<rep>"
is unique across the corpus and is the id the cross-link uses.
Usage: python3 reconstruction/clean_raw.py
"""
import json, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT, RAW = REPO / "out", REPO / "data/raw"
FIRST_CHARTER_RUN = "20261028-231119-charter"  # runs before this probed eval awareness, not the Charter


def main():
    shutil.rmtree(RAW, ignore_errors=True)
    (RAW / "runs").mkdir(parents=True)
    n_runs = n_rows = 0
    for f in sorted(OUT.glob("*/responses.jsonl")):
        run = f.parent.name
        study = "charter" if run >= FIRST_CHARTER_RUN else "eval-awareness"
        rows = {}
        for line in open(f):
            r = json.loads(line)
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
        with open(RAW / "runs" / f"{run}.jsonl", "w") as w:
            for row in rows.values():
                w.write(json.dumps(row, ensure_ascii=False) + "\n")
        n_runs, n_rows = n_runs + 1, n_rows + len(rows)
    print(f"{n_runs} runs, {n_rows} samples -> {RAW}")


if __name__ == "__main__":
    main()
