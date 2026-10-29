# Muse Spark Open: Charter reconstruction

**Interactive viz: https://vigji.github.io/muse-spark-open-charter/**

A reconstruction of the "Charter" that Muse Spark Open (`meta/muse-spark-open`, via OpenRouter) reasons from,
assembled only from its chain of thought, with every passage linked to the samples that produced it.

- `data/raw/`: the raw transcripts of all probe runs, cleaned (29 runs, 1,404 samples, $10.19 of API cost),
  and nothing else. It includes the earlier eval-awareness runs on other models (`study: "eval-awareness"`).
- `data/crosslink/`: data only. The reconstructed document (162 passages: 135 solid, 27 weak), plus 9,251
  passage-to-sample links classed by what each sample's own prompt contained: 7,833 unprompted, 151 near,
  1,267 echo. Only unprompted links count as support. Schemas are in `data/README.md`.
- `reconstruction/`: the pipeline. `charter_spec.json` is the hand-edited order, text and verdicts.
  `viz/charter_viz.html` is the viz: every passage lists its sources unprompted first, and any source opens
  the full prompt, CoT and answer. `charter_viz_standalone.html` works offline and is the page
  that `.github/workflows/pages.yml` deploys to GitHub Pages on every push that changes it.
- `notes/charter_reconstruction.md`: running findings, probe by probe, including the adversarial audit. Where
  its quoted text differs from `data/crosslink/document.json`, the document is current.
- `run.py`: the OpenRouter sampler that generated the runs. It reads `OPENROUTER_API_KEY` from a local
  `.env`, which is not committed.

Rebuild from the committed data:

```
python3 reconstruction/crosslink.py && python3 reconstruction/viz/build_viz.py
python3 reconstruction/grow.py      # report: text the samples agree on that the document still lacks
```

`reconstruction/clean_raw.py` regenerates `data/raw/` from the original `out/` run folders. Those folders
are not in this repo.
