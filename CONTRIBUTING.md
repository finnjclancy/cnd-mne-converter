# Contributing

Issues and small PRs are welcome. If you change how neural data is interpreted, say so in the PR. Do not silently resample, truncate, pad, scale, or guess units.

```bash
git clone https://github.com/finnjclancy/cnd-mne-converter.git
cd cnd-mne-converter
uv sync --extra dev
uv run pytest --cov=cnd_mne
uv run ruff check .
uv run ruff format --check .
uv run mypy src/cnd_mne
```

Tests should use small synthetic or openly redistributable fixtures. Do not commit participant data unless the licence actually allows it. New mappings need a round trip, a malformed-input case, and a note about anything MNE or CND cannot represent.

If you want to change the MNE-facing API in a big way, open an issue first.
