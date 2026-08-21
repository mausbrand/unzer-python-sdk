# Contributing

## Before you change behaviour: measure it

The single most important rule in this repository. Unzer's documentation is frequently wrong,
and so are their official SDKs. **The running API is the only source of truth.** Before
implementing a field, a required-ness, an endpoint version or an enum value, call the sandbox
and look at what actually comes back. Before "fixing" something because a docs page calls a
field mandatory, check whether the API enforces it.

[AGENTS.md](AGENTS.md) lists thirteen measured cases where the documentation was wrong, along
with the source ranking to use when looking things up.

## Issues

Please include the SDK version, the Python version, and — if there is one — the `errorId`
(`s-err-…`) from the `ErrorResponse`. Unzer support can resolve those. Never paste private
keys, and remember that `DEBUG` logs contain full payloads with IBANs and names.

## Pull requests

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/), and the
type determines the version bump:

| Type | Meaning | Bump |
|---|---|---|
| `fix:` | bug fix | patch |
| `feat:` | new feature | minor |
| `refactor:`, `chore:`, `docs:`, `test:`, `cicd:` | no behaviour change | none |

Add a `!` (`feat!:`) for a breaking change. Code identifiers in the subject may be written as
`` `code` ``.

Branch off before committing: `fix/*` for patch-level work, `feat/*` for minor-level work.
Fixes target `main`, features target `develop`. Commit only what belongs to the change — no
drive-by version bumps, no unrelated reformatting.

## Code style

- PEP 8, with the exceptions in `tox.ini` and one deliberate deviation: **method and attribute
  names mirror the Unzer JSON payload** (`getPayment`, `paymentId`), because tracing a field
  from the API reference into this code should not require a translation table. This is
  scheduled to change to snake_case in 2.0.
- Lines up to 120 characters, spaces, LF, trailing newline — see `.editorconfig`.
- Double quotes. Multi-line dicts and lists: one entry per line, trailing comma.
- Type hints everywhere. `import typing as t`, built-in generics (`list[str]`), `X | None`.
  Do not repeat types in the docstring — the annotation is the single source of truth. Older
  modules still carry `# type:` comments; those are legacy, do not add more.
- Docstrings in Sphinx/reST format (`:param x:`, `:return:`). No Google or NumPy style.
- An unknown enum value raises — it means the SDK is behind the API, and the fix is to add
  the missing member, not to swallow it. Note that `unknown` is a real value in this API
  (`salutation`), so a placeholder of that name would be ambiguous.

## Setup and tests

```bash
uv sync --extra testing          # or: pip install -e ".[testing]"
uv run pytest                    # unit tests, mocked, no network
uv run pycodestyle src/ tests/   # the CI checks the full tree, not just the diff
```

Unit tests mock HTTP with [responses](https://pypi.org/project/responses/) and read their
payloads from `tests/fixtures/`. **Build fixtures from real captured responses**, never by
hand: a hand-written one only confirms what you believed while writing it. One of ours had
`action: "charge"` where the API answers `"CHARGE"`.

Sandbox tests talk to the real API and are opt-in:

```bash
echo 'UNZER_PRIVATE_KEY=s-priv-...' > .env    # git-ignored, never commit this
uv run pytest -m sandbox
```

They create real resources on whatever account the key belongs to, so the suite refuses
anything that is not a `s-priv-` key. Sandbox accounts differ in which methods they have
enabled — tests skip what an account cannot do, so a skip is usually the account, not a bug.

Every bug fix gets a regression test that fails before the fix. Tests must not depend on state
an earlier run left behind in the sandbox; generate unique ids per run.

## Releasing

1. Bump `__version__` in `src/unzer/__init__.py`.
2. Commit as `chore: bump version to vX.Y.Z`.
3. Tag `vX.Y.Z` and push the tag.

The publish workflow builds and uploads to PyPI and drafts a GitHub release. A `v-test-*`
prefix targets TestPyPI instead and creates no public release. Pre-releases follow PEP 440
(`1.6.0.dev1`, `1.6.0rc1`); a tag containing `dev` is marked as a prerelease automatically.
