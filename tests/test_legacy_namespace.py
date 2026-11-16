"""Legacy imports must share types, globals and package objects."""

import importlib
import subprocess
import sys


def test_legacy_nested_modules_are_canonical(monkeypatch):
    for name in (
        "models",
        "runtime_identity",
        "policies",
        "policies.scoring",
        "media_import",
        "media_import.subtitles.jobs",
        "web.app",
    ):
        legacy = importlib.import_module("seed_agent." + name)
        canonical = importlib.import_module("media_agent." + name)
        assert legacy is canonical
        assert canonical.__name__ == "media_agent." + name
        assert canonical.__spec__.name == "media_agent." + name
    from seed_agent.models import TorrentCandidate
    from seed_agent.runtime_identity import RuntimeIdentityError

    from media_agent.models import TorrentCandidate as CurrentCandidate
    from media_agent.runtime_identity import RuntimeIdentityError as CurrentError

    assert TorrentCandidate is CurrentCandidate
    assert RuntimeIdentityError is CurrentError
    legacy = importlib.import_module("seed_agent.policies.scoring")
    canonical = importlib.import_module("media_agent.policies.scoring")
    monkeypatch.setattr(legacy, "legacy_probe", True, raising=False)
    assert canonical.legacy_probe is True


def test_legacy_package_does_not_eagerly_import_cli():
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import seed_agent,sys; "
            "assert 'media_agent.cli' not in sys.modules; "
            "from seed_agent.media_import import store; "
            "import media_agent.media_import.store as current; "
            "assert store is current",
        ],
        check=True,
    )
