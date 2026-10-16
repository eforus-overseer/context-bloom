# Contributing

Start with a small, observable improvement and its limits. The current pipeline is English-only and lexical; don't claim semantic equivalence or guaranteed token savings.

Use synthetic fixtures. Test that goals, negations, corrections, exact identifiers, and pending work survive your recommendations. New host integrations need current official documentation and a reproducible example payload. Never commit personal transcripts or generated reports from real sessions.

Prepare the environment using the README, then run `skills/context-bloom/.venv/bin/python -m unittest discover -s tests -v`. Discuss larger language models or native UI integrations in an issue first.
