"""Lazy aliases preserving module and type identity for legacy integrations."""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys

from media_agent import __path__ as __path__
from media_agent import __version__

__all__ = ["__version__"]


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, canonical: str):
        self.canonical = canonical
        self.metadata = {}

    def create_module(self, spec):
        module = importlib.import_module(self.canonical)
        self.metadata = {
            key: module.__dict__.get(key)
            for key in ("__name__", "__package__", "__loader__", "__spec__")
        }
        return module

    def exec_module(self, module):
        # Import machinery assigns the alias spec even for an existing module.
        # Keep canonical metadata so relative imports and reload stay canonical.
        module.__dict__.update(self.metadata)


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith("seed_agent."):
            return None
        canonical = "media_agent." + fullname.removeprefix("seed_agent.")
        spec = importlib.util.find_spec(canonical)
        if spec is None:
            return None
        return importlib.util.spec_from_loader(
            fullname,
            _AliasLoader(canonical),
            is_package=spec.submodule_search_locations is not None,
        )


sys.meta_path.insert(0, _AliasFinder())
