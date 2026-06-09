from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen

Fetch = Callable[[str, dict[str, str]], bytes]


@dataclass(frozen=True)
class TmdbResult:
    title: str
    year: int | None
    id: int


class TmdbClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        bearer_token: str | None = None,
        language: str = "en-US",
        fetch: Fetch | None = None,
    ) -> None:
        self.api_key = api_key
        self.bearer_token = bearer_token
        self.language = language
        self.fetch = fetch or _fetch

    def search_movie(self, title: str, *, year: int | None = None) -> list[TmdbResult]:
        params: dict[str, str | int] = {"query": title, "language": self.language}
        if year is not None:
            params["year"] = year
        payload = self._get("/search/movie", params)
        return [
            TmdbResult(
                title=str(item.get("title") or item.get("original_title") or ""),
                year=_year_from_date(item.get("release_date")),
                id=int(item["id"]),
            )
            for item in payload.get("results", [])
            if item.get("id") and (item.get("title") or item.get("original_title"))
        ]

    def search_tv(self, title: str) -> list[TmdbResult]:
        payload = self._get("/search/tv", {"query": title, "language": self.language})
        return [
            TmdbResult(
                title=str(item.get("name") or item.get("original_name") or ""),
                year=_year_from_date(item.get("first_air_date")),
                id=int(item["id"]),
            )
            for item in payload.get("results", [])
            if item.get("id") and (item.get("name") or item.get("original_name"))
        ]

    def _get(self, path: str, params: dict[str, str | int]) -> dict:
        url_params = dict(params)
        headers: dict[str, str] = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            url_params["api_key"] = self.api_key

        url = f"https://api.themoviedb.org/3{path}?{urlencode(url_params)}"
        return json.loads(self.fetch(url, headers).decode("utf-8"))


def select_best_movie(
    *,
    query_title: str,
    query_year: int | None,
    candidates: Iterable[TmdbResult | tuple[str, int | None, int]],
) -> TmdbResult | tuple[str, int | None, int] | None:
    items = list(candidates)
    if not items:
        return None
    normalized_query = normalize_title(query_title)
    return max(
        items,
        key=lambda item: _movie_score(
            normalized_query,
            query_year,
            result_title(item),
            result_year(item),
        ),
    )


def select_best_tv(
    *,
    query_title: str,
    candidates: Iterable[TmdbResult | tuple[str, int | None, int]],
) -> TmdbResult | tuple[str, int | None, int] | None:
    items = list(candidates)
    if not items:
        return None
    normalized_query = normalize_title(query_title)
    return max(items, key=lambda item: _title_score(normalized_query, result_title(item)))


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def result_title(result: TmdbResult | tuple[str, int | None, int]) -> str:
    return result.title if isinstance(result, TmdbResult) else result[0]


def result_year(result: TmdbResult | tuple[str, int | None, int]) -> int | None:
    return result.year if isinstance(result, TmdbResult) else result[1]


def result_id(result: TmdbResult | tuple[str, int | None, int]) -> int:
    return result.id if isinstance(result, TmdbResult) else result[2]


def _movie_score(
    normalized_query: str,
    query_year: int | None,
    candidate_title: str,
    candidate_year: int | None,
) -> tuple[int, int]:
    title_score = _title_score(normalized_query, candidate_title)
    year_score = int(query_year is not None and query_year == candidate_year)
    return year_score, title_score


def _title_score(normalized_query: str, candidate_title: str) -> int:
    normalized_candidate = normalize_title(candidate_title)
    if normalized_query == normalized_candidate:
        return 2
    if normalized_query in normalized_candidate or normalized_candidate in normalized_query:
        return 1
    return 0


def _year_from_date(value: object) -> int | None:
    if not isinstance(value, str) or len(value) < 4:
        return None
    try:
        return int(value[:4])
    except ValueError:
        return None


def _fetch(url: str, headers: dict[str, str]) -> bytes:
    request = Request(url, headers=headers)
    with urlopen(request, timeout=20) as response:
        return response.read()
