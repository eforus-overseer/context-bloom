# Setup

Python 3.10+ is required. From this skill directory:

```sh
python3 -m venv .venv
.venv/bin/python -m pip --isolated install --index-url https://pypi.org/simple -r requirements.txt
.venv/bin/python scripts/setup.py
```

Windows: use `.venv\Scripts\python.exe` instead. Setup explicitly downloads NLTK WordNet, English stop words, English POS tagger, and `cl100k_base` / `o200k_base` tokenizer tables. It may take a minute. Keep `.nltk_data/`, `.token_cache/`, and `.venv/` local. Later analyses make no network requests; absent resources produce an error instead of silent approximate normalization.

Use `python3 scripts/run.py input.md --out reports/bloom.json`. Use an absolute script path outside this directory. The output includes JSON, offline HTML, and a handoff worksheet. The entire self-contained skill folder can be copied to another machine; recreate its environment there rather than copying a virtual environment.

English prose is the supported linguistic scope. Other scripts, source code and language mixtures are not meaningfully normalized by the English model. BPE text counts still operate on Unicode, but are not full session counts. Negations are retained, while stemming can collapse distinctions; never feed the normalized words back as a replacement conversation.
