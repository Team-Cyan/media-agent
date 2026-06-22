# Product Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the product gaps found in the PM review: configurable matching thresholds, candidate-based review, safer Web UI execution, source/target health, and synchronized docs.

**Architecture:** Keep the current simple Python standard-library runtime. Add typed matching config, persist TMDB candidates and review decisions in SQLite, expose narrow HTTP endpoints from `src/media_agent/web.py`, and keep execution dry-run-first by requiring preview before link creation. Avoid broad framework changes.

**Tech Stack:** Python 3.14+ unless dependency verification finds a blocker, stdlib `sqlite3` and `http.server`, `pyyaml`, `pytest`, existing CLI/Web UI modules.

---

## File Structure

- Modify `src/media_agent/config.py`: add `MatchingConfig`, parse and validate matching thresholds, expose them through `AppConfig`.
- Modify `src/media_agent/import_runner.py`: use configured thresholds, store review candidates, store review decisions, skip execution for review-required actions.
- Modify `src/media_agent/web.py`: show richer review rows, add candidate selection endpoint, add execution preview and confirmation flow, add source/target health summary.
- Modify `src/media_agent/cli.py`: keep CLI behavior compatible while respecting configured matching thresholds.
- Modify `config/example.yaml`: keep matching keys but make comments clear if behavior is now active.
- Modify `README.md`, `docs/roadmap.md`, `docs/operations/session-handoff.md`, `docs/specs/2026-06-09-media-agent-product-boundary.md`, `docs/operations/docker-image-runtime.md`: align current state and operator safety.
- Modify `pyproject.toml`: raise the supported Python baseline to 3.14+ if dependency verification stays green.
- Modify tests:
  - `tests/test_config.py`
  - `tests/test_import_runner.py`
  - `tests/test_web.py`
  - `tests/test_runtime_status.py` if health payload shape changes

---

### Task 1: Raise Python Baseline To 3.14

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/operations/docker-image-runtime.md`

- [ ] **Step 1: Verify local Python and dependency tree**

Run:

```bash
uv run python -V
uv tree --depth 1
```

Expected:

```text
Python 3.14.x
media-agent v0.1.0
├── pyyaml ...
├── pytest ... (group: dev)
└── ruff ... (group: dev)
```

If `uv run python -V` is below 3.14, install or select a 3.14 interpreter before editing the baseline.

- [ ] **Step 2: Update project Python metadata**

In `pyproject.toml`, change:

```toml
requires-python = ">=3.12"
```

to:

```toml
requires-python = ">=3.14"
```

Change Ruff target:

```toml
target-version = "py312"
```

to:

```toml
target-version = "py314"
```

- [ ] **Step 3: Refresh lockfile if uv requires it**

Run:

```bash
uv lock
```

Expected: exits 0. If `uv.lock` changes, include it in the commit.

- [ ] **Step 4: Verify dependencies and tests on Python 3.14**

Run:

```bash
uv run python -V
uv run pytest
uv run ruff check .
```

Expected:

```text
Python 3.14.x
33+ passed
All checks passed!
```

- [ ] **Step 5: Update operator docs**

In `README.md` current scope or setup section, add:

```markdown
`media-agent` targets Python 3.14+ for local development and test runs.
The Docker image provides the runtime interpreter; operators normally do not
need Python on the host.
```

In `docs/operations/docker-image-runtime.md`, add:

```markdown
Local development and CI target Python 3.14+. Container operators should use
the published image unless they are developing the Python package directly.
```

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock README.md docs/operations/docker-image-runtime.md
git commit -m "chore: require python 3.14"
```

---

### Task 2: Wire Matching Config Into Runtime

**Files:**
- Modify: `src/media_agent/config.py`
- Modify: `src/media_agent/import_runner.py`
- Test: `tests/test_config.py`
- Test: `tests/test_import_runner.py`

- [ ] **Step 1: Add failing config parsing tests**

Add to `tests/test_config.py`:

```python
from media_agent.config import parse_config


def test_parses_matching_config() -> None:
    config = load_config(Path("config/example.yaml"))

    parsed = parse_config(config)

    assert parsed.matching.auto_plan_min_confidence == 0.85
    assert parsed.matching.review_min_confidence == 0.55
    assert parsed.matching.max_review_choices == 5


def test_rejects_invalid_matching_threshold_order() -> None:
    config = {
        "tmdb": {"api_key_ref": "local/secrets/tmdb.api-key"},
        "matching": {
            "auto_plan_min_confidence": 0.4,
            "review_min_confidence": 0.8,
            "max_review_choices": 5,
        },
        "profiles": [
            {
                "name": "movies",
                "type": "movie",
                "source": "/downloads/movies",
                "target": "/media/Movies",
            }
        ],
    }

    with pytest.raises(ConfigError, match="auto_plan_min_confidence"):
        validate_config(config)
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_config.py -q
```

Expected: fails because `AppConfig.matching` and validation do not exist.

- [ ] **Step 3: Implement config model**

In `src/media_agent/config.py`, add:

```python
@dataclass(frozen=True)
class MatchingConfig:
    auto_plan_min_confidence: float = 0.85
    review_min_confidence: float = 0.55
    max_review_choices: int = 5
```

Update `AppConfig`:

```python
@dataclass(frozen=True)
class AppConfig:
    mode: str
    tmdb_api_key_ref: str
    tmdb_bearer_token_ref: str | None
    tmdb_language: str
    matching: MatchingConfig
    scheduler: SchedulerConfig
    profiles: tuple[ProfileConfig, ...]
```

Add helper:

```python
def _parse_matching(config: dict[str, Any]) -> MatchingConfig:
    matching = _mapping(config, "matching", required=False)
    auto_plan = float(matching.get("auto_plan_min_confidence", 0.85))
    review_min = float(matching.get("review_min_confidence", 0.55))
    max_choices = int(matching.get("max_review_choices", 5))
    if not 0 <= review_min <= auto_plan <= 1:
        raise ConfigError(
            "matching.auto_plan_min_confidence must be between "
            "matching.review_min_confidence and 1"
        )
    if max_choices < 1:
        raise ConfigError("matching.max_review_choices must be at least 1")
    return MatchingConfig(
        auto_plan_min_confidence=auto_plan,
        review_min_confidence=review_min,
        max_review_choices=max_choices,
    )
```

Call `_parse_matching(config)` from `validate_config()` and set `matching=_parse_matching(config)` inside `parse_config()`.

- [ ] **Step 4: Replace hard-coded review threshold**

In `src/media_agent/import_runner.py`, replace:

```python
if guess.confidence < 0.55:
```

with:

```python
if guess.confidence < config.matching.auto_plan_min_confidence:
```

The product behavior should be conservative: anything below auto-plan confidence enters review.

- [ ] **Step 5: Add runtime threshold test**

Add to `tests/test_import_runner.py`:

```python
def test_import_run_once_uses_configured_review_threshold(tmp_path, capsys) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)
    text = config.read_text(encoding="utf-8")
    config.write_text(
        text.replace("scheduler:", "matching:\n  auto_plan_min_confidence: 0.95\n  review_min_confidence: 0.55\n  max_review_choices: 5\nscheduler:"),
        encoding="utf-8",
    )

    exit_code = main([
        "import-run-once",
        "--config",
        str(config),
        "--state-dir",
        str(state_dir),
        "--json",
    ])

    assert exit_code == 0
    with sqlite3.connect(state_dir / "state.db") as db:
        rows = db.execute("select title, status from review_items").fetchall()
    assert rows == [("Arrival", "pending")]
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest tests/test_config.py tests/test_import_runner.py -q
```

Expected: all selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/media_agent/config.py src/media_agent/import_runner.py tests/test_config.py tests/test_import_runner.py
git commit -m "feat: wire matching thresholds into import runtime"
```

---

### Task 3: Persist Review Candidates And Decisions

**Files:**
- Modify: `src/media_agent/import_runner.py`
- Test: `tests/test_import_runner.py`

- [ ] **Step 1: Add failing candidate persistence test**

Add to `tests/test_import_runner.py`:

```python
def test_import_run_once_records_tmdb_review_candidates(tmp_path, capsys) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    secret = tmp_path / "tmdb.key"
    movie = source / "Matrix.1999.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    secret.write_text("unused", encoding="utf-8")
    config = _write_config(tmp_path, source, target, tmdb_api_key_ref=secret)

    class FakeTmdb:
        def search_movie(self, title: str, *, year: int | None = None):
            return [
                ("The Matrix", 1999, 603),
                ("Matrix", 1993, 999),
            ]

    exit_code = main([
        "import-run-once",
        "--config",
        str(config),
        "--state-dir",
        str(state_dir),
        "--json",
    ], tmdb_client=FakeTmdb())

    assert exit_code == 0
    with sqlite3.connect(state_dir / "state.db") as db:
        candidates = db.execute(
            "select title, year, metadata_id, rank from review_candidates order by rank"
        ).fetchall()
    assert candidates == [
        ("The Matrix", 1999, "tmdb:movie:603", 1),
        ("Matrix", 1993, "tmdb:movie:999", 2),
    ]
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_import_runner.py::test_import_run_once_records_tmdb_review_candidates -q
```

Expected: fails because `review_candidates` does not exist.

- [ ] **Step 3: Add DB tables**

In `ImportState._init_db()`, add:

```python
db.execute(
    """
    create table if not exists review_candidates (
        id integer primary key autoincrement,
        review_item_id integer not null,
        rank integer not null,
        metadata_id text not null,
        title text not null,
        year integer,
        confidence real not null,
        raw_json text not null,
        unique(review_item_id, metadata_id)
    )
    """
)
db.execute(
    """
    create table if not exists review_decisions (
        id integer primary key autoincrement,
        created_at real not null,
        source_path text not null,
        selected_metadata_id text not null,
        title text not null,
        year integer,
        media_type text not null,
        unique(source_path)
    )
    """
)
```

- [ ] **Step 4: Make `record_review_item()` return the row id**

Change the method signature:

```python
def record_review_item(
    self,
    *,
    source_path: Path,
    media_type: str,
    reason: str,
    title: str,
) -> int:
```

After the upsert, fetch and return:

```python
row = db.execute(
    "select id from review_items where source_path = ? and reason = ?",
    (str(source_path), reason),
).fetchone()
return int(row[0])
```

- [ ] **Step 5: Add candidate recording method**

Add to `ImportState`:

```python
def record_review_candidates(
    self,
    *,
    review_item_id: int,
    candidates: list[dict[str, object]],
) -> None:
    with sqlite3.connect(self.db_path) as db:
        db.execute("delete from review_candidates where review_item_id = ?", (review_item_id,))
        for index, candidate in enumerate(candidates, start=1):
            db.execute(
                """
                insert into review_candidates (
                    review_item_id, rank, metadata_id, title, year, confidence, raw_json
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review_item_id,
                    index,
                    str(candidate["metadata_id"]),
                    str(candidate["title"]),
                    candidate.get("year"),
                    float(candidate["confidence"]),
                    json.dumps(candidate, sort_keys=True),
                ),
            )
```

- [ ] **Step 6: Return candidates from TMDB enrichment**

Change `_enrich_guess_with_tmdb()` to return:

```python
tuple[MediaGuess, bool, list[dict[str, object]]]
```

For movie results, build candidates:

```python
candidates = [
    {
        "metadata_id": f"tmdb:movie:{result_id(item)}",
        "title": result_title(item),
        "year": result_year(item),
        "confidence": 0.9 if item == best else 0.65,
    }
    for item in list(results)[:5]
]
```

For TV/anime, use `tmdb:{guess.media_type}:{id}` and candidate titles from `search_tv()`.

- [ ] **Step 7: Store candidates when item enters review**

In `run_import_once()`, capture `review_candidates` from enrichment. When the guess enters review, call:

```python
review_item_id = state.record_review_item(
    source_path=source_path,
    media_type=guess.media_type,
    reason="below_auto_plan_threshold",
    title=guess.title,
)
if review_candidates:
    state.record_review_candidates(
        review_item_id=review_item_id,
        candidates=review_candidates[: config.matching.max_review_choices],
    )
```

- [ ] **Step 8: Run focused tests**

Run:

```bash
uv run pytest tests/test_import_runner.py -q
```

Expected: all import runner tests pass.

- [ ] **Step 9: Commit**

```bash
git add src/media_agent/import_runner.py tests/test_import_runner.py
git commit -m "feat: persist review candidates"
```

---

### Task 4: Add Manual Review Selection API And Web UI

**Files:**
- Modify: `src/media_agent/import_runner.py`
- Modify: `src/media_agent/web.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Add failing Web API test**

Add to `tests/test_web.py`:

```python
def test_web_server_selects_review_candidate(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Unknown.Movie.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)
    assert main([
        "import-run-once",
        "--config",
        str(config),
        "--state-dir",
        str(state_dir),
        "--json",
    ]) == 0
    with sqlite3.connect(state_dir / "state.db") as db:
        review_id = db.execute("select id from review_items").fetchone()[0]
        db.execute(
            """
            insert into review_candidates (
                review_item_id, rank, metadata_id, title, year, confidence, raw_json
            ) values (?, 1, 'tmdb:movie:603', 'The Matrix', 1999, 0.9, '{}')
            """,
            (review_id,),
        )

    server = run_web_server(config_path=config, state_dir=state_dir, host="127.0.0.1", port=0, once=True)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/review-items/{review_id}/select",
            data=json.dumps({"metadata_id": "tmdb:movie:603"}).encode(),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["ok"] is True
        with sqlite3.connect(state_dir / "state.db") as db:
            item_status = db.execute("select status from review_items where id = ?", (review_id,)).fetchone()[0]
            decision = db.execute("select selected_metadata_id, title from review_decisions").fetchone()
        assert item_status == "selected"
        assert decision == ("tmdb:movie:603", "The Matrix")
    finally:
        server.shutdown()
        server.server_close()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_web.py::test_web_server_selects_review_candidate -q
```

Expected: fails with 404 for the new endpoint.

- [ ] **Step 3: Add decision method**

Add to `ImportState`:

```python
def select_review_candidate(self, *, review_item_id: int, metadata_id: str) -> None:
    with sqlite3.connect(self.db_path) as db:
        row = db.execute(
            """
            select ri.source_path, ri.media_type, rc.metadata_id, rc.title, rc.year
            from review_items ri
            join review_candidates rc on rc.review_item_id = ri.id
            where ri.id = ? and rc.metadata_id = ?
            """,
            (review_item_id, metadata_id),
        ).fetchone()
        if row is None:
            raise ValueError("review candidate not found")
        db.execute(
            """
            insert into review_decisions (
                created_at, source_path, selected_metadata_id, title, year, media_type
            ) values (?, ?, ?, ?, ?, ?)
            on conflict(source_path) do update set
                created_at = excluded.created_at,
                selected_metadata_id = excluded.selected_metadata_id,
                title = excluded.title,
                year = excluded.year,
                media_type = excluded.media_type
            """,
            (time.time(), row[0], row[2], row[3], row[4], row[1]),
        )
        db.execute("update review_items set status = 'selected' where id = ?", (review_item_id,))
```

- [ ] **Step 4: Add Web endpoint**

In `src/media_agent/web.py`, import `ImportState`.

In `do_POST()`, before import-run handling:

```python
if self.path.startswith("/api/review-items/") and self.path.endswith("/select"):
    self._select_review_candidate()
    return
```

Add handler method:

```python
def _select_review_candidate(self) -> None:
    parts = self.path.strip("/").split("/")
    review_item_id = int(parts[2])
    length = int(self.headers.get("Content-Length", "0"))
    payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
    metadata_id = str(payload.get("metadata_id") or "")
    if not metadata_id:
        self._send_json({"ok": False, "error": "metadata_id is required"}, status=HTTPStatus.BAD_REQUEST)
        return
    try:
        ImportState(state_dir).select_review_candidate(
            review_item_id=review_item_id,
            metadata_id=metadata_id,
        )
    except ValueError as exc:
        self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
        return
    self._send_json({"ok": True})
```

- [ ] **Step 5: Render candidates in dashboard**

Update `build_status()` to query candidate rows for pending review item ids and attach them as `candidates`.

Update `_render_review_row()` to render candidate buttons:

```python
buttons = " ".join(
    f'<button onclick="selectCandidate({int(row["id"])}, {json.dumps(candidate["metadata_id"])})">'
    f'{html.escape(str(candidate["title"]))} ({html.escape(str(candidate.get("year") or ""))})'
    "</button>"
    for candidate in row.get("candidates", [])
)
```

Add JS:

```javascript
async function selectCandidate(reviewId, metadataId) {
  const response = await fetch(`/api/review-items/${reviewId}/select`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ metadata_id: metadataId })
  });
  await readJson(response);
  location.reload();
}
```

- [ ] **Step 6: Run focused tests**

Run:

```bash
uv run pytest tests/test_web.py tests/test_import_runner.py -q
```

Expected: selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add src/media_agent/import_runner.py src/media_agent/web.py tests/test_web.py
git commit -m "feat: add manual review selection"
```

---

### Task 5: Make Web Execute Explicit And Preview-Based

**Files:**
- Modify: `src/media_agent/web.py`
- Test: `tests/test_web.py`

- [ ] **Step 1: Add failing tests for execute confirmation**

Add to `tests/test_web.py`:

```python
def test_web_execute_requires_confirmation_token(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    state_dir = tmp_path / "state"
    movie = source / "Arrival.2016.mkv"
    movie.parent.mkdir(parents=True)
    movie.write_bytes(b"movie")
    config = _write_config(tmp_path, source, target)
    server = run_web_server(config_path=config, state_dir=state_dir, host="127.0.0.1", port=0, once=True)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/import-run-once?execute=true",
            data=b"",
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            payload = json.loads(exc.read())
            assert exc.code == 400
            assert payload["error"] == "execute requires confirm=planned"
        else:
            raise AssertionError("execute without confirmation was accepted")
        assert not (target / "Arrival (2016)" / "Arrival (2016).mkv").exists()
    finally:
        server.shutdown()
        server.server_close()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_web.py::test_web_execute_requires_confirmation_token -q
```

Expected: fails because execute currently runs without confirmation.

- [ ] **Step 3: Require confirmation query**

In `do_POST()` import-run handling, replace:

```python
execute = "execute=true" in self.path
```

with:

```python
execute = "execute=true" in self.path
if execute and "confirm=planned" not in self.path:
    self._send_json(
        {"ok": False, "error": "execute requires confirm=planned"},
        status=HTTPStatus.BAD_REQUEST,
    )
    return
```

- [ ] **Step 4: Add UI confirmation and loading feedback**

Replace `runImport()` JavaScript with:

```javascript
async function runImport(execute) {
  const confirmed = !execute || window.confirm("Execute planned imports now? Run dry scan first if you need to review target paths.");
  if (!confirmed) return;
  const path = execute
    ? "/api/import-run-once?execute=true&confirm=planned"
    : "/api/import-run-once";
  const buttons = document.querySelectorAll("button");
  buttons.forEach((button) => button.disabled = true);
  try {
    const response = await fetch(path, { method: "POST" });
    await readJson(response);
    location.reload();
  } catch (error) {
    alert(error.message);
    buttons.forEach((button) => button.disabled = false);
  }
}
```

Change the execute button label to:

```html
<button onclick="runImport(true)">Execute planned links</button>
```

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_web.py -q
```

Expected: all Web tests pass after updating existing execute-trigger tests to include `confirm=planned` where they intentionally execute.

- [ ] **Step 6: Commit**

```bash
git add src/media_agent/web.py tests/test_web.py
git commit -m "fix: require explicit web execute confirmation"
```

---

### Task 6: Add Source/Target Health To Status

**Files:**
- Modify: `src/media_agent/web.py`
- Test: `tests/test_web.py`
- Test: `tests/test_runtime_status.py` if CLI status is extended

- [ ] **Step 1: Add failing health test**

Add to `tests/test_web.py`:

```python
def test_web_status_includes_profile_health(tmp_path) -> None:
    source = tmp_path / "downloads" / "movies"
    target = tmp_path / "media" / "Movies"
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    state_dir = tmp_path / "state"
    config = _write_config(tmp_path, source, target)

    server = run_web_server(config_path=config, state_dir=state_dir, host="127.0.0.1", port=0, once=True)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=5) as response:
            payload = json.loads(response.read())
        assert payload["profile_health"] == [
            {
                "name": "movies",
                "type": "movie",
                "enabled": True,
                "source_exists": True,
                "target_exists": True,
                "target_writable": True,
            }
        ]
    finally:
        server.shutdown()
        server.server_close()
```

- [ ] **Step 2: Run test and verify failure**

Run:

```bash
uv run pytest tests/test_web.py::test_web_status_includes_profile_health -q
```

Expected: fails because `profile_health` is missing.

- [ ] **Step 3: Add health builder**

In `src/media_agent/web.py`, add:

```python
def build_profile_health(config_path: Path) -> list[dict[str, object]]:
    config = parse_config(load_config(config_path))
    rows: list[dict[str, object]] = []
    for profile in config.profiles:
        source_exists = profile.source.exists()
        target_exists = profile.target.exists()
        rows.append(
            {
                "name": profile.name,
                "type": profile.type,
                "enabled": profile.enabled,
                "source_exists": source_exists,
                "target_exists": target_exists,
                "target_writable": target_exists and os.access(profile.target, os.W_OK),
            }
        )
    return rows
```

Import `os`.

Change `build_status()` signature to accept optional `config_path: Path | None = None`, and if supplied include:

```python
"profile_health": build_profile_health(config_path),
```

Update callers in Web handler to call `build_status(state_dir, config_path=config_path)`.

- [ ] **Step 4: Render health section**

Add a compact table under stats:

```html
<div class="section-heading"><h2>Profile Health</h2></div>
```

Columns: Profile, Type, Source, Target, Writable.

- [ ] **Step 5: Run focused tests**

Run:

```bash
uv run pytest tests/test_web.py -q
```

Expected: all Web tests pass after updating tests that call `build_status(state_dir)` to tolerate no `profile_health` or pass a config path.

- [ ] **Step 6: Commit**

```bash
git add src/media_agent/web.py tests/test_web.py tests/test_runtime_status.py
git commit -m "feat: show profile source and target health"
```

---

### Task 7: Synchronize Docs And Config Guidance

**Files:**
- Modify: `README.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/operations/session-handoff.md`
- Modify: `docs/specs/2026-06-09-media-agent-product-boundary.md`
- Modify: `docs/operations/docker-image-runtime.md`
- Modify: `config/example.yaml`

- [ ] **Step 1: Update README current scope**

In `README.md`, adjust the top feature bullets so they distinguish current and next capabilities:

```markdown
- Web UI status, configuration, dry-run scan, and explicit execute controls,
- pending review queue with manual TMDB candidate selection,
```

If manual selection is not fully implemented at the time this task runs, write:

```markdown
- pending review queue storage, with manual TMDB candidate selection in progress,
```

- [ ] **Step 2: Update safety docs for Web UI**

In `README.md` and `docs/operations/docker-image-runtime.md`, add:

```markdown
The Web UI can write runtime config and local TMDB secret files. Bind it only to
trusted interfaces, and put authentication in front of it before exposing it
beyond a private operator network.
```

- [ ] **Step 3: Fix stale session handoff**

Replace lines stating that `web` is placeholder/not implemented in `docs/operations/session-handoff.md` with:

```markdown
`import-schedule` loops over the same import pass. `web` serves the operational
status/config UI, including dry scan and explicitly confirmed execute triggers.
Manual candidate selection is the next key workflow if it has not already landed
in the current branch.
```

- [ ] **Step 4: Update roadmap checkboxes**

In `docs/roadmap.md`, set Review Queue items according to actual implementation state after Tasks 1-5:

```markdown
- [x] Store uncertain filename/TMDB matches as pending review items.
- [x] Expose candidate choices.
- [x] Allow manual selection.
- [ ] Re-run import planning after user selection.
```

Only mark the last item complete if Task 3 also re-plans selected choices.

- [ ] **Step 5: Clarify config example**

Add comments in `config/example.yaml`:

```yaml
matching:
  # Matches at or above this confidence can be planned without manual review.
  auto_plan_min_confidence: 0.85
  # Matches below auto-plan confidence enter review. This lower bound is kept
  # for future filtering of very weak candidates.
  review_min_confidence: 0.55
  # Maximum TMDB candidates stored for each review item.
  max_review_choices: 5
```

- [ ] **Step 6: Run doc/config validation**

Run:

```bash
uv run media-agent config-check --config config/example.yaml
uv run pytest tests/test_config.py tests/test_web.py -q
```

Expected: config check exits 0 and selected tests pass.

- [ ] **Step 7: Commit**

```bash
git add README.md docs/roadmap.md docs/operations/session-handoff.md docs/specs/2026-06-09-media-agent-product-boundary.md docs/operations/docker-image-runtime.md config/example.yaml
git commit -m "docs: align product review workflow guidance"
```

---

### Task 8: Full Regression And Product Acceptance

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run full test suite**

Run:

```bash
uv run pytest
```

Expected:

```text
33+ passed
```

The exact count may increase after new tests are added. There must be zero failures.

- [ ] **Step 2: Run lint**

Run:

```bash
uv run ruff check .
```

Expected:

```text
All checks passed!
```

- [ ] **Step 3: Verify example config**

Run:

```bash
uv run media-agent config-check --config config/example.yaml
```

Expected JSON includes:

```json
{"dry_run_default": true, "enabled_profiles": 3, "ok": true, "profiles": 3}
```

- [ ] **Step 4: Manual Web smoke test**

Run:

```bash
uv run media-agent web --config config/example.yaml --state-dir .media-agent --host 127.0.0.1 --port 8775
```

Open `http://127.0.0.1:8775/status` and confirm:

- Runtime Status renders.
- Profile Health renders.
- Run dry scan disables buttons while request is running.
- Execute button uses confirmation wording.
- Pending Review rows show candidates when candidate rows exist.
- Configuration page still validates config and writes only after clicking Save.

- [ ] **Step 5: Final commit if smoke-test fixes were needed**

If Step 4 required fixes:

```bash
git add src/media_agent tests README.md docs config
git commit -m "fix: polish product review workflow"
```

If no fixes were needed, do not create an empty commit.

---

## Self-Review

- Spec coverage: The plan covers matching thresholds, review candidates, manual selection, Web execution safety, profile health, and documentation drift.
- Deliberate gap: automatic re-planning from a selected review decision is acknowledged in docs and left as the next small task unless implemented during Task 3. This keeps the first fix set bounded.
- Placeholder scan: no step relies on an undefined broad instruction; tests and implementation entry points are named explicitly.
- Type consistency: `MatchingConfig`, `review_candidates`, `review_decisions`, `select_review_candidate()`, and `/api/review-items/{id}/select` are consistently named across tasks.
