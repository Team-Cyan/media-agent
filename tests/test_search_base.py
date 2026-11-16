from typing import Protocol

from media_agent.search.base import SearchProvider


def test_search_provider_is_protocol() -> None:
    assert issubclass(SearchProvider, Protocol)
