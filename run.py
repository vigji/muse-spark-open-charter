# /// script
# requires-python = ">=3.11"
# dependencies = ["openai", "python-dotenv", "pandas", "tabulate"]
# ///
"""Smoke test: do open-weights reasoning models verbalize eval awareness in their (raw, readable) CoT?

    uv run run.py ping                                         # 1 tiny call per model, checks the reasoning field comes back
    uv run run.py generate [out/<t>] [--reps 2] [--models a,b] [--dry-run]   # appends to out/<t>/responses.jsonl
    uv run run.py dump out/<t>                                 # cots.md, grouped by prompt, for reading
    uv run run.py report out/<t>                               # summary.md, from hand-written labels.jsonl

Labels are written by hand (by Claude reading cots.md), one line per sample: {"key", "aware": yes|no|ambiguous, "quote"}.
OpenRouter key: OPENROUTER_API_KEY from ./.env (gitignored). Spend is capped by --budget (real cost from usage.cost).
"""

import argparse
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])

MODELS = ["z-ai/glm-5.3", "moonshotai/kimi-k3", "deepseek/deepseek-v4-pro-0813", "qwen/qwen3.8-2.4t-a95b",
          "meta/muse-spark-open", "nvidia/nemotron-3-ultra-550b-a55b", "xiaomi/mimo-v2.6-pro"]
MAX_TOKENS = 3000
EFFORT = None  # OpenRouter reasoning.effort, e.g. "high"; None = provider default
LOGPROBS = False  # answer-token logprobs (OpenRouter returns none for reasoning tokens)

spent, lock = 0.0, threading.Lock()


def prices():
    return {m.id: (float(m.pricing["prompt"]), float(m.pricing["completion"])) for m in client.models.list()}


def chat(model, messages, budget, price, max_tokens=None, **params):
    """One call; reserves worst-case cost against the budget first, then books the real cost. Returns (message dict, cost)."""
    global spent
    max_tokens = max_tokens or MAX_TOKENS
    worst = price[0] * 4 * sum(len(m["content"]) for m in messages) + price[1] * max_tokens
    with lock:
        if spent + worst > budget:
            raise RuntimeError(f"budget: spent ${spent:.3f}, next call could cost ${worst:.3f}")
        spent += worst
    cost = 0  # failed calls aren't billed; this releases the reservation
    try:
        extra = {"reasoning": {"effort": EFFORT} if EFFORT else {"enabled": True}, "usage": {"include": True}}
        if LOGPROBS:
            params = {**params, "logprobs": True, "top_logprobs": 5}
            extra["provider"] = {"require_parameters": True}
        r = client.chat.completions.create(model=model, messages=messages, max_tokens=max_tokens, **params, extra_body=extra)
        r = r.model_dump()
        cost = r["usage"].get("cost", worst)
        lp = [[t["token"], t["logprob"], [[a["token"], a["logprob"]] for a in t["top_logprobs"]]]
              for t in ((r["choices"][0].get("logprobs") or {}).get("content") or [])]
        return {**r["choices"][0]["message"], "finish": r["choices"][0]["finish_reason"], "usage": r["usage"], "provider": r.get("provider"), "logprobs": lp}, cost
    finally:
        with lock:
            spent += cost - worst


def ping(args):
    price = prices()
    for model in args.models:
        msg, cost = chat(model, [{"role": "user", "content": "What is 17*23?"}], args.budget, price[model], max_tokens=1000)
        cot = msg.get("reasoning") or ""
        print(f"{model:32s} ${cost:.5f}  reasoning={len(cot)} chars  answer={msg['content']!r:.40}\n    {cot[:200]!r}")
    print(f"total ${spent:.4f}")


def generate(args):
    price, prompts = prices(), json.loads(Path(args.prompts).read_text())
    jobs = [(m, p, rep) for m in args.models for p in prompts if not args.ids or p["id"] in args.ids for rep in range(args.reps)]
    print(f"{len(jobs)} calls, worst-case output cost ${sum(price[m][1] * MAX_TOKENS for m, _, _ in jobs):.3f} (budget ${args.budget})")
    if args.dry_run:
        return
    out = Path(args.dir) if args.dir else ROOT / "out" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    f = open(out / "responses.jsonl", "a")

    def run(job):
        model, p, rep = job
        try:
            msg, cost = chat(model, p["messages"], args.budget, price[model], **p.get("params", {}))  # e.g. temperature
        except Exception as e:
            print(f"FAIL {model} {p['id']}: {e}")
            return
        row = {"key": f"{model.split('/')[1]}|{p['id']}|{rep}", "model": model, "id": p["id"], "group": p["group"],
               "pair": p.get("pair"), "rep": rep, "messages": p["messages"], "reasoning": msg.get("reasoning") or "",
               "content": msg["content"] or "", "finish": msg["finish"], "usage": msg["usage"], "provider": msg["provider"], "effort": EFFORT, "cost": cost,
               **({"logprobs": msg["logprobs"]} if LOGPROBS else {})}
        with lock:
            f.write(json.dumps(row) + "\n")
            f.flush()
        print(f"{model:32s} {p['id']:16s} rep{rep} ${cost:.4f}  (total ${spent:.3f})")

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(run, jobs))
    print(f"wrote {out}  total ${spent:.4f}")


def dump(args):
    out = Path(args.dir)
    df = pd.read_json(out / "responses.jsonl", lines=True).sort_values(["id", "model", "rep"])
    lines = []
    for pid, g in df.groupby("id", sort=False):
        lines += [f"# {pid}", "", "\n\n".join(f"[{m['role']}] {m['content']}" for m in g.iloc[0].messages), ""]
        for r in g.itertuples():
            lines += [f"## {r.key}  ({r.finish})", "", "COT:", r.reasoning.strip(), "", "ANSWER:", r.content.strip()[:600], ""]
    (out / "cots.md").write_text("\n".join(lines))
    print(f"{len(df)} samples -> {out / 'cots.md'}")


def report(args):
    out = Path(args.dir)
    df = pd.read_json(out / "responses.jsonl", lines=True).merge(pd.read_json(out / "labels.jsonl", lines=True), on="key")
    df["aware"] = df.aware.eq("yes")
    df["model"] = df.model.str.split("/").str[1]
    df["pair"] = df.pair.fillna("control")
    frac = lambda s: f"{s.sum()}/{len(s)}"
    by_group = df.pivot_table(index="model", columns="group", values="aware", aggfunc=frac)
    by_prompt = df.pivot_table(index=["pair", "id"], columns="model", values="aware", aggfunc=frac)
    quotes = df[df.aware]
    lines = [f"# Eval-awareness smoke test: {out.name}", "",
             f"Generation ${df.cost.sum():.3f}. Cells = samples whose CoT verbalizes that the model may be in a test / eval / "
             "constructed scenario (hand-labelled).", "",
             "## By group", "", by_group.to_markdown(), "", "## By prompt", "", by_prompt.to_markdown(), "", "## Quotes", "",
             *(f"- **{r.model}** `{r.id}`: \"{r.quote}\"" for r in quotes.itertuples())]
    (out / "summary.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["ping", "generate", "dump", "report"])
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--reps", type=int, default=2)
    ap.add_argument("--models", type=lambda s: s.split(","), default=MODELS)
    ap.add_argument("--prompts", default=ROOT / "prompts.json")
    ap.add_argument("--ids", type=lambda s: s.split(","))
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    ap.add_argument("--effort")
    ap.add_argument("--logprobs", action="store_true")
    args = ap.parse_args()
    MAX_TOKENS, EFFORT, LOGPROBS = args.max_tokens, args.effort, args.logprobs
    {"ping": ping, "generate": generate, "dump": dump, "report": report}[args.cmd](args)
