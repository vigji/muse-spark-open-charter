# Charter reconstruction pipeline

Rebuilds the reconstructed Muse Charter, its cross-link to the CoTs, and the viz. Run from the repo root:

```
python3 reconstruction/clean_raw.py        # out/*/responses.jsonl  -> data/raw/
python3 reconstruction/crosslink.py        # charter_spec.json + data/raw -> data/crosslink/
python3 reconstruction/viz/build_viz.py    # data/crosslink + data/raw -> viz/charter_viz.html (+ _standalone)
```

- **`charter_spec.json`** is the one hand-edited input: the reading order (headings, notes, gaps, passages,
  variants), each passage's text, and the verdicts and test results from the adversarial probes. Edit it to
  place, demote or add a passage. Support counts are never written here; `crosslink.py` computes them.
- **`crosslink.py`** links every heading and passage to the samples that reproduce it and classes each link
  as unprompted, near or echo by what that sample's own prompt contained. See `../data/README.md`.
- **`grow.py`** (read-only report) walks outward from every passage while 60%+ of its unprompted samples keep
  agreeing and prints extensions that are not yet in the document, in a sample's own wording. Add the real ones
  to `charter_spec.json`; `_superseded/apply_grow.py` is the one-off that applied the first round.
- **`viz/build_viz.py`** inlines the document, the sorted links (unprompted first) and the full prompt, CoT
  and answer of every linked sample (gzip+base64). In the page, “open full transcript” shows a sample with
  the matched spans highlighted. `charter_viz_standalone.html` embeds the fonts too and needs no network.
  Published at https://claude.ai/artifact/Ssj74bi2fzXCLBBjyi6vNQ.
- **`_superseded/`** keeps the two one-offs that edited the spec, for the record: `migrate_spec.py` (the old
  pipeline's frozen order to `charter_spec.json`, audit applied) and `apply_grow.py` (first round of consensus
  extensions). The old pipeline files they read are not in this repo.

New probe runs: put them in `out/` (not in this repo; see `run.py`) and rerun the three scripts. New text that should appear in the document
has to be added to `charter_spec.json`; until then it is only in `data/raw`.
