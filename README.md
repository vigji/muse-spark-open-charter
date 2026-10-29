# Muse Spark Open: Charter reconstruction

## **[→ Open the interactive viewer](https://vigji.github.io/muse-spark-open-charter/)**

Write-up: [Leaking Muse's Charter, Meta's model spec](https://vigji.github.io/blog/muse-spark-charter/)

A reconstruction of the "Charter" that Muse Spark Open (`meta/muse-spark-open`) reasons from, assembled only
from its chain of thought.

**Method.** 884 Muse Spark Open transcripts (260 prompts, via OpenRouter) were searched for each reconstructed
passage by word 6-gram overlap. A match counts as support only if that transcript's own prompt did not already
contain the passage. Passages reproduced unprompted by 3+ transcripts from 2+ runs are marked solid (135 of 162).

- `data/raw/`: raw transcripts (prompt, CoT, answer) of all runs
- `data/crosslink/`: the reconstructed document and the passage-to-transcript links (schemas in `data/README.md`)
- `reconstruction/`: the pipeline and the viewer (`python3 reconstruction/crosslink.py && python3 reconstruction/viz/build_viz.py`)
