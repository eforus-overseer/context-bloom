# Design and roadmap

## Delivered

1. Preserve the original counter and repository history; rename to Context Bloom.
2. Build a self-contained skill with deterministic, local English NLP analysis and explicit tokenizer selection.
3. Separate source-text, normalized-text, and host context measurements.
4. Rank review locations while protecting instructions, recent work, fenced code, explicit keep markers, and likely unresolved tasks.
5. Provide a Claude terminal indicator and a portable graphical report without claiming unsupported Codex UI access.
6. Package direct installation and Claude plugin metadata; test behavior and publish a synthetic demo.

## Measurement details

Treebank tokenization → English POS tagging → WordNet lemmatization → English stop-word removal (negations retained) → Porter stemming. Both raw supplied text and joined normalized stems are counted with the selected tiktoken encoding. For message arrays, raw supplied text means message contents joined by two newlines; it deliberately excludes role framing. Per-block counts may not sum exactly to full-text counts because tokenization at boundaries differs.

Only unprotected blocks with at least 40 source-text tokens become review candidates. Score = source-text tokens × (0.25 + 0.75 × lexical overlap). Overlap is the fraction of distinct stems already seen in previous blocks. Return the top eight by score. This is transparent lexical triage, not a semantic compaction model or expected-savings estimate.

Text/Markdown inputs split at blank lines outside fenced code. Message arrays preserve message boundaries. Role protection applies to structured message input; unstructured prose has only lexical/recency/code/explicit-marker protections. A keep marker protects its own block, not the entire document. Read the original text before acting.

The handoff is an unfilled worksheet; the invoking agent supplies verified facts. No automatic summarizer or conversation mutation is implemented. With no actual host measurement, timing remains unknown.

## Next milestones

- **Export adapters:** support one documented host transcript format, explicitly selected by the user, with tool-call/result grouping and tests for compaction boundaries.
- **Better grouping:** preserve Markdown sections and constraints across related blocks, including headings and tables.
- **Semantic evaluation:** use a licensed synthetic dataset of repetitions, contradictions, corrections, and exact identifiers; measure harmful removal recommendations before adding embeddings.
- **Multilingual:** language selection, appropriate lemmatizers and stop lists, and language-specific benchmark cases.
- **Live visual UI:** integrate only through supported host interfaces; isolate sessions and mark stale telemetry. The current HTML is a snapshot, not a live dashboard.

## References

- [NLTK WordNet lemmatizer](https://www.nltk.org/api/nltk.stem.wordnet.html)
- [tiktoken](https://github.com/openai/tiktoken)
- [Host integration references](../skills/context-bloom/references/integrations.md)
