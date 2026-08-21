"""Shared fixtures for the test suite.

The suite runs in two modes:

**Mocked** (default) -- every HTTP call is served by :mod:`responses` from the JSON
files in ``tests/fixtures/``. No network, no credentials, deterministic.

**Sandbox** -- tests marked ``@pytest.mark.sandbox`` talk to the real Unzer sandbox.
They are skipped unless ``UNZER_PRIVATE_KEY`` is set, because Unzer's actual
behaviour repeatedly differs from its documentation: fields documented as required
turn out optional, and vice versa. Mocks can only ever assert what we believed at
the time we wrote them.

Run against the sandbox with::

    UNZER_PRIVATE_KEY=s-priv-... pytest -m sandbox

Or force it -- fails instead of skipping when no key is present, so a CI job cannot
silently pass without ever calling the API::

    UNZER_PRIVATE_KEY=s-priv-... pytest --sandbox
"""

import json
import os
import pathlib
import typing as t

import pytest
import responses

from unzer import UnzerClient

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"

DUMMY_PRIVATE_KEY = "s-priv-000000000000000000000000000000"
DUMMY_PUBLIC_KEY = "s-pub-0000000000000000000000000000000"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--sandbox",
        action="store_true",
        default=False,
        help="require the sandbox tests to run: fail instead of skip when "
             "UNZER_PRIVATE_KEY is unset",
    )


def _load_dotenv() -> None:
    """Read ``KEY=value`` pairs from a ``.env`` in the repository root.

    Keeps the sandbox credentials out of the shell history and out of the
    repository -- ``.env`` is git-ignored. Existing environment variables win, so
    an explicit ``UNZER_PRIVATE_KEY=... pytest`` still overrides the file.
    """
    env_file = pathlib.Path(__file__).parent.parent / ".env"
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _sandbox_key() -> str | None:
    """Return the sandbox private key from the environment, if it is usable.

    :raises pytest.UsageError: If the key is not a sandbox key. Production keys
        start with ``p-``; running the test suite against a production account
        would create real payments.
    """
    _load_dotenv()
    key = os.environ.get("UNZER_PRIVATE_KEY")
    if not key:
        return None
    if not key.startswith("s-priv-"):
        raise pytest.UsageError(
            "UNZER_PRIVATE_KEY is not a sandbox key: sandbox keys start with "
            "'s-priv-'. Refusing to run the test suite against a non-sandbox "
            "account -- this would create real transactions."
        )
    return key


def pytest_collection_modifyitems(
        config: pytest.Config,
        items: list[pytest.Item],
) -> None:
    """Skip sandbox tests unless a sandbox key is available."""
    key = _sandbox_key()
    if key:
        return
    if config.getoption("--sandbox"):
        raise pytest.UsageError(
            "--sandbox was given but UNZER_PRIVATE_KEY is not set."
        )
    skip = pytest.mark.skip(reason="no UNZER_PRIVATE_KEY set (sandbox test)")
    for item in items:
        if "sandbox" in item.keywords:
            item.add_marker(skip)


@pytest.fixture
def fixture_json() -> t.Callable[[str], t.Any]:
    """Load a captured API response from ``tests/fixtures``.

    :return: A callable taking the file name without the ``.json`` suffix.
    """

    def load(name: str) -> t.Any:
        path = FIXTURE_DIR / f"{name}.json"
        if not path.is_file():
            raise AssertionError(
                f"fixture {name!r} does not exist; available: "
                f"{sorted(p.stem for p in FIXTURE_DIR.glob('*.json'))}"
            )
        return json.loads(path.read_text(encoding="utf-8"))

    return load


@pytest.fixture
def client() -> UnzerClient:
    """A client with dummy credentials and retries disabled.

    ``retryDelays`` is emptied so a test that provokes a failure does not spend
    fifteen seconds in :func:`time.sleep`. Use :func:`retrying_client` to test the
    retry behaviour itself.
    """
    client = UnzerClient(DUMMY_PRIVATE_KEY, DUMMY_PUBLIC_KEY, sandbox=True)
    client.retryDelays = ()
    return client


@pytest.fixture
def retrying_client() -> UnzerClient:
    """A client that retries, but without waiting between the attempts."""
    client = UnzerClient(DUMMY_PRIVATE_KEY, DUMMY_PUBLIC_KEY, sandbox=True)
    client.retryDelays = (0, 0, 0, 0)
    return client


@pytest.fixture
def mocked_api() -> t.Iterator[responses.RequestsMock]:
    """Intercept every outgoing request.

    ``assert_all_requests_are_fired`` stays on: a registered response that is never
    called usually means the test does not exercise what it claims to.
    """
    with responses.RequestsMock(assert_all_requests_are_fired=True) as rsps:
        yield rsps


@pytest.fixture(scope="module")
def sandbox_client() -> UnzerClient:
    """A client bound to the real Unzer sandbox.

    Only usable in tests marked ``@pytest.mark.sandbox``; without a key the
    marker skips the test before this fixture is reached.
    """
    key = _sandbox_key()
    if not key:  # pragma: no cover - guarded by the marker
        pytest.skip("no UNZER_PRIVATE_KEY set")
    return UnzerClient(key, os.environ.get("UNZER_PUBLIC_KEY", ""), sandbox=True)
