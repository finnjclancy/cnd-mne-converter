# Contributing

Issues and focused pull requests are welcome. Scientific mapping changes must
state their assumptions and must not silently resample, truncate, pad, scale,
or reinterpret data.

## Development setup

```bash
git clone https://github.com/finnjclancy/cnd-mne-converter.git
cd cnd-mne-converter
uv sync --extra dev
uv run pytest --cov=cnd_mne
uv run ruff check .
uv run ruff format --check .
uv build
```

Tests should use small synthetic or openly redistributable fixtures. Do not
commit participant data unless its licence and consent terms explicitly allow
redistribution. New format mappings should include round-trip tests, malformed
input tests, and documentation of any information that MNE or CND cannot
represent.

Before proposing a major MNE-facing API change, open a design issue so the CND
and MNE maintainers can agree on the representation.
