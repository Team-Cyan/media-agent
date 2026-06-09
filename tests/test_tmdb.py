from __future__ import annotations

import json

from media_agent.tmdb import TmdbClient, select_best_movie, select_best_tv


def test_search_movie_uses_api_key_without_exposing_secret() -> None:
    requests: list[str] = []

    def fetch(url: str, headers: dict[str, str]) -> bytes:
        requests.append(url)
        assert "Authorization" not in headers
        return json.dumps(
            {
                "results": [
                    {
                        "id": 329865,
                        "title": "Arrival",
                        "release_date": "2016-11-10",
                    }
                ]
            }
        ).encode()

    client = TmdbClient(api_key="secret-key", language="en-US", fetch=fetch)

    results = client.search_movie("Arrival", year=2016)

    assert results[0].id == 329865
    assert results[0].title == "Arrival"
    assert results[0].year == 2016
    assert "api_key=secret-key" in requests[0]
    assert "query=Arrival" in requests[0]
    assert "year=2016" in requests[0]


def test_search_tv_can_use_bearer_token() -> None:
    seen_headers: list[dict[str, str]] = []

    def fetch(url: str, headers: dict[str, str]) -> bytes:
        seen_headers.append(headers)
        assert "api_key=" not in url
        return json.dumps(
            {
                "results": [
                    {
                        "id": 1396,
                        "name": "Breaking Bad",
                        "first_air_date": "2008-01-20",
                    }
                ]
            }
        ).encode()

    client = TmdbClient(bearer_token="bearer-token", language="en-US", fetch=fetch)

    results = client.search_tv("Breaking Bad")

    assert results[0].id == 1396
    assert results[0].title == "Breaking Bad"
    assert seen_headers == [{"Authorization": "Bearer bearer-token"}]


def test_select_best_movie_prefers_year_match() -> None:
    best = select_best_movie(
        query_title="Arrival",
        query_year=2016,
        candidates=[
            ("Arrival", 1996, 1),
            ("Arrival", 2016, 2),
        ],
    )

    assert best == ("Arrival", 2016, 2)


def test_select_best_tv_prefers_title_match() -> None:
    best = select_best_tv(
        query_title="Breaking Bad",
        candidates=[
            ("Bad Break", 2008, 1),
            ("Breaking Bad", 2008, 2),
        ],
    )

    assert best == ("Breaking Bad", 2008, 2)
