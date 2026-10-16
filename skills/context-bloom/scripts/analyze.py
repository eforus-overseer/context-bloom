"""Local English lexical analysis and reviewable compaction advice."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from statusline import pressure

ROOT = Path(__file__).resolve().parents[1]
NEGATIONS = {'no', 'not', 'nor', 'never', 'without', "n't"}


class NLP:
    def __init__(self, encoding='cl100k_base'):
        import nltk
        import tiktoken
        from nltk.corpus import stopwords
        from nltk.stem import PorterStemmer, WordNetLemmatizer
        from nltk.tokenize import TreebankWordTokenizer
        # A read-only cache loader prevents implicit tokenizer downloads at runtime.
        import tiktoken.load
        cache = ROOT / '.token_cache'
        def cached_only(path):
            cached = cache / hashlib.sha1(path.encode()).hexdigest()
            if not cached.is_file():
                raise ValueError('Tokenizer cache missing. Run scripts/setup.py first (explicit download).')
            return cached.read_bytes()
        original = tiktoken.load.read_file
        tiktoken.load.read_file = cached_only
        try:
            os.environ['TIKTOKEN_CACHE_DIR'] = str(cache)
            self.encoder = tiktoken.get_encoding(encoding)
        finally:
            tiktoken.load.read_file = original
        nltk.data.path.insert(0, str(ROOT / '.nltk_data'))
        self.stop = set(stopwords.words('english')) - NEGATIONS
        self.lemma = WordNetLemmatizer()
        self.stem = PorterStemmer()
        self.tokenizer = TreebankWordTokenizer()
        self.tag = nltk.pos_tag
        self.encoding = encoding
        self.normalize('Children are running; do not stop.')

    def count(self, text):
        return len(self.encoder.encode(text, disallowed_special=()))

    def normalize(self, text):
        words = [re.sub(r'^\W+|\W+$', '', w) for w in self.tokenizer.tokenize(text.casefold())]
        words = [w for w in words if any(c.isalpha() for c in w)]
        tags = self.tag(words) if words else []
        lemmas = [self.lemma.lemmatize(w, {'J': 'a', 'V': 'v', 'N': 'n', 'R': 'r'}.get(tag[0], 'n'))
                  for w, tag in tags]
        kept = [w for w in lemmas if w not in self.stop]
        stems = [self.stem.stem(w) for w in kept]
        return {'words': words, 'lemmas': lemmas, 'kept': kept, 'stems': stems}


def sections(text):
    """Split on blank lines outside fenced code, retaining exact line coordinates."""
    output, start, buffer, fence = [], 1, [], None
    for line_no, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        marker = re.match(r'(`{3,}|~{3,})', stripped)
        if marker:
            value = marker.group(1)
            if fence is None:
                fence = value
            elif value[0] == fence[0] and len(value) >= len(fence):
                fence = None
        if not line.strip() and fence is None:
            if buffer:
                output.append({'text': '\n'.join(buffer), 'location': f'lines {start}–{line_no - 1}', 'role': 'text'})
                buffer = []
            start = line_no + 1
        else:
            if not buffer:
                start = line_no
            buffer.append(line)
    if buffer:
        output.append({'text': '\n'.join(buffer), 'location': f'lines {start}–{len(text.splitlines())}', 'role': 'text'})
    return output


def load_input(path, format):
    raw = path.read_bytes()
    if len(raw) > 2_000_000:
        raise ValueError('Input exceeds the 2 MB limit; export a smaller relevant context slice.')
    text = raw.decode('utf-8')
    if format == 'text':
        blocks = sections(text)
        token_text = text
    else:
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError('messages input must be a JSON array of {role, content} objects')
        blocks = []
        for i, message in enumerate(data, 1):
            if not isinstance(message, dict) or message.get('role') not in ('system', 'developer', 'user', 'assistant', 'tool') or not isinstance(message.get('content'), str):
                raise ValueError(f'message {i}: expected supported role and string content')
            blocks.append({'text': message['content'], 'role': message['role'], 'location': f'message {i}'})
        token_text = '\n\n'.join(b['text'] for b in blocks)
    if not blocks or not token_text.strip():
        raise ValueError('input must contain text')
    if len(blocks) > 2000:
        raise ValueError('Input exceeds 2,000 blocks; export a smaller context slice.')
    return raw, token_text, blocks


def analyze(text, blocks, nlp, context_used=None, context_limit=None, keep_recent=2, prepare=65, compact=80):
    if (context_used is None) != (context_limit is None):
        raise ValueError('provide both --context-used and --context-limit, or neither')
    if context_used is not None and (context_used < 0 or context_limit <= 0):
        raise ValueError('context used must be nonnegative and limit must be positive')
    if keep_recent < 1:
        raise ValueError('keep-recent must be at least 1')
    percentage = 100 * context_used / context_limit if context_limit else None
    state = pressure(percentage, prepare, compact)
    normalized = nlp.normalize(text)
    total_tokens = nlp.count(text)
    rows = []
    previous = set()
    for i, block in enumerate(blocks):
        terms = nlp.normalize(block['text'])['stems']
        unique = set(terms)
        overlap = len(unique & previous) / len(unique) if unique else 0
        previous.update(unique)
        tokens = nlp.count(block['text'])
        protected = []
        if i >= len(blocks) - keep_recent:
            protected.append('recent context')
        if block['role'] in ('user', 'system', 'developer'):
            protected.append('instructions or user request')
        if '<!-- bloom:keep -->' in block['text']:
            protected.append('explicit keep marker')
        if re.search(r'^\s*(?:```|~~~)', block['text'], re.M):
            protected.append('fenced code; preserve exact syntax')
        if re.search(r'\b(?:must|never|do not|todo|pending|unresolved)\b', block['text'], re.I):
            protected.append('possible constraint or unfinished work')
        candidate = not protected and tokens >= 40
        reasons = []
        if candidate:
            reasons.append('older block outside protected recent context')
            if overlap >= .6:
                reasons.append('high lexical overlap with earlier blocks')
            if block['role'] == 'tool':
                reasons.append('tool output: preserve result and artifact path instead of full log')
        # Ranking is an inspection aid, never a semantic equivalence claim.
        score = round(tokens * (.25 + .75 * overlap), 2) if candidate else 0
        rows.append({'id': i + 1, 'location': block['location'], 'role': block['role'],
                     'text_tokens': tokens, 'normalized_terms': len(terms),
                     'lexical_overlap': round(overlap, 3), 'protected': protected,
                     'candidate': candidate, 'score': score, 'reasons': reasons})
    candidates = sorted((r for r in rows if r['candidate']), key=lambda r: (-r['score'], r['id']))[:8]
    advice = {'unknown': 'Timing unknown: supply current host context usage. Review the ranked blocks when useful.',
              'room': 'Room to work. Save a handoff at the next task boundary if the session will continue.',
              'prepare': 'Prepare a handoff now; compact after the current coherent task completes.',
              'compact': 'Compact at the next safe boundary after saving goals, constraints, decisions, and unfinished work.'}[state]
    return {'schema_version': '1.0', 'name': 'Context Bloom',
            'tokenizer': {'encoding': nlp.encoding, 'scope': 'supplied text only; excludes host framing, hidden instructions, images and tools'},
            'counts': {'raw_text_tokens': total_tokens,
                       'normalized_text_tokens': nlp.count(' '.join(normalized['stems'])),
                       'lexical_words': len(normalized['words']), 'lemmatized_terms': len(normalized['lemmas']),
                       'content_terms': len(normalized['kept']), 'unique_stems': len(set(normalized['stems']))},
            'top_stems': [{'term': t, 'count': c} for t, c in Counter(normalized['stems']).most_common(12)],
            'context': {'used': context_used, 'limit': context_limit, 'percentage': percentage,
                        'source': 'user-supplied host usage' if context_used is not None else 'unavailable', 'state': state},
            'policy': {'prepare_at_percent': prepare, 'compact_at_percent': compact, 'keep_recent': keep_recent},
            'advice': advice, 'blocks': rows, 'candidates': candidates,
            'limitations': ['English lexical analysis; normalization is lossy and is never a replacement prompt.',
                            'Normalized token counts do not measure live context or guaranteed token savings.',
                            'Lexical overlap does not prove duplicate meaning; review each candidate before condensing.',
                            'Compaction timing thresholds are configurable heuristics, not provider limits.',
                            'No automatic compaction, transcript scanning, or remote API calls.']}


def handoff(report):
    lines = ['# Context Bloom · compaction plan', '', report['advice'], '',
             '## Review these blocks', '']
    for block in report['candidates']:
        lines.append(f"- {block['location']} ({block['text_tokens']} source-text tokens): {'; '.join(block['reasons'])}.")
    if not report['candidates']:
        lines.append('No unprotected blocks met the review threshold. Do not force a compaction.')
    lines += ['', '## Fill in before compacting', '',
              '- Current goal and acceptance criteria:', '- User constraints and exact identifiers:',
              '- Decisions made and why:', '- Completed changes, files, and verified results:',
              '- Remaining work, failures, and next action:',
              '- Links or paths to full logs and artifacts:', '',
              'Review against the original context, then use the host’s compaction command.',
              'This is a worksheet, not an automatically generated factual summary.', '']
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--format', choices=['text', 'messages'], default='text')
    parser.add_argument('--encoding', choices=['cl100k_base', 'o200k_base'], default='cl100k_base')
    parser.add_argument('--context-used', type=int)
    parser.add_argument('--context-limit', type=int)
    parser.add_argument('--keep-recent', type=int, default=2)
    parser.add_argument('--prepare', type=float, default=65)
    parser.add_argument('--compact', type=float, default=80)
    parser.add_argument('--out', type=Path, default=Path('reports/bloom.json'))
    args = parser.parse_args(argv)
    try:
        if args.out.suffix != '.json':
            raise ValueError('--out must end in .json')
        outputs = [args.out, args.out.with_suffix('.html'), args.out.with_suffix('.handoff.md')]
        if args.input.resolve() in {p.resolve() for p in outputs}:
            raise ValueError('output would overwrite the input')
        raw, text, blocks = load_input(args.input, args.format)
        report = analyze(text, blocks, NLP(args.encoding), args.context_used, args.context_limit,
                         args.keep_recent, args.prepare, args.compact)
        report['input_sha256'] = hashlib.sha256(raw).hexdigest()
        from visual import html_report
        outputs[0].parent.mkdir(parents=True, exist_ok=True)
        outputs[0].write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n', encoding='utf-8')
        outputs[1].write_text(html_report(report), encoding='utf-8')
        outputs[2].write_text(handoff(report), encoding='utf-8')
    except (OSError, ValueError, ImportError, LookupError) as exc:
        parser.error(f'{exc}\nIf dependencies or resources are missing, follow references/setup.md.')
    print(f"Context Bloom · {report['counts']['raw_text_tokens']:,} source-text tokens · {report['counts']['normalized_text_tokens']:,} normalized-text tokens")
    print(report['advice'])
    print(f'Saved {outputs[0]}, {outputs[1]}, and {outputs[2]}')


if __name__ == '__main__':
    main()
