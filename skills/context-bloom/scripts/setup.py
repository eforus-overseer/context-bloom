"""Explicit, one-time NLP resource download; never called by the analyzer."""
import os
from pathlib import Path
import ssl
import urllib.request
import certifi
import nltk
import tiktoken

# Verified CA bundle also works with Python.org installations on macOS.
context = ssl.create_default_context(cafile=certifi.where())
urllib.request.install_opener(urllib.request.build_opener(urllib.request.HTTPSHandler(context=context)))

root = Path(__file__).resolve().parents[1]
data = root / '.nltk_data'
data.mkdir(exist_ok=True)
for resource in ('wordnet', 'stopwords', 'averaged_perceptron_tagger_eng'):
    if not nltk.download(resource, download_dir=str(data), quiet=True, raise_on_error=True):
        raise SystemExit(f'Could not download {resource}')
os.environ['TIKTOKEN_CACHE_DIR'] = str(root / '.token_cache')
for encoding in ('cl100k_base', 'o200k_base'):
    tiktoken.get_encoding(encoding)
print('NLP resources and both tokenizer tables are cached. Analysis now runs offline.')
