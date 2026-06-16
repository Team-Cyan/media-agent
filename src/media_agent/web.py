from __future__ import annotations

import html
import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

from media_agent.config import ConfigError, load_config, parse_config, validate_config
from media_agent.import_runner import run_import_once, summary_to_dict


def build_status(state_dir: Path) -> dict[str, Any]:
    db_path = state_dir / "state.db"
    if not db_path.exists():
        return {
            "counts": {"planned": 0, "linked": 0, "failed": 0, "pending_review": 0},
            "recent_actions": [],
            "review_items": [],
        }

    with sqlite3.connect(db_path) as db:
        db.row_factory = sqlite3.Row
        action_counts = {
            str(row["status"]): int(row["count"])
            for row in db.execute(
                "select status, count(*) as count from import_actions group by status"
            )
        }
        pending_review = db.execute(
            "select count(*) from review_items where status = 'pending'"
        ).fetchone()[0]
        recent_actions = [
            dict(row)
            for row in db.execute(
                """
                select created_at, profile, media_type, source_path, target_path,
                       metadata_id, link_mode, confidence, dry_run, status
                from import_actions
                order by created_at desc, id desc
                limit 25
                """
            )
        ]
        review_items = [
            dict(row)
            for row in db.execute(
                """
                select id, created_at, source_path, media_type, reason, title, status
                from review_items
                where status = 'pending'
                order by created_at desc, id desc
                limit 25
                """
            )
        ]

    return {
        "counts": {
            "planned": action_counts.get("planned", 0),
            "linked": action_counts.get("linked", 0),
            "failed": sum(
                count for status, count in action_counts.items() if status.startswith("failed")
            ),
            "pending_review": pending_review,
        },
        "recent_actions": recent_actions,
        "review_items": review_items,
    }


def render_dashboard(status: dict[str, Any]) -> str:
    counts = {"planned": 0, "linked": 0, "failed": 0, "pending_review": 0}
    counts.update(status["counts"])
    review_rows = "\n".join(_render_review_row(row) for row in status["review_items"])
    action_rows = "\n".join(_render_action_row(row) for row in status["recent_actions"])
    body = f"""
    <section class="page-head">
      <div>
        <h2>Runtime Status</h2>
        <p>Current import state, review queue, and recent audit actions.</p>
      </div>
      <div class="toolbar inline">
        <button class="primary" onclick="runImport(false)">Run dry scan</button>
        <button onclick="runImport(true)">Run execute</button>
        <button onclick="location.reload()">Refresh</button>
      </div>
    </section>
    <section class="stats">
      <div class="stat">Planned<strong>{counts["planned"]}</strong></div>
      <div class="stat">Linked<strong>{counts["linked"]}</strong></div>
      <div class="stat">Failed<strong>{counts["failed"]}</strong></div>
      <div class="stat">Pending Review<strong>{counts["pending_review"]}</strong></div>
    </section>
    <div class="section-heading"><h2>Pending Review</h2></div>
    {_table_or_empty(review_rows, "No pending review items.", "review")}
    <div class="section-heading"><h2>Recent Actions</h2></div>
    {_table_or_empty(action_rows, "No import actions yet.", "actions")}
"""
    return _render_page("status", body)


def render_config_page(*, config_text: str = "") -> str:
    body = f"""
    <section class="page-head">
      <div>
        <h2>Configuration</h2>
        <p>Runtime YAML and local TMDB credential files.</p>
      </div>
    </section>
    <section class="config-grid">
      <div class="panel">
        <div class="panel-head">
          <div>
            <h2>Runtime Config</h2>
            <p>YAML profile, scheduler, naming, and library path settings.</p>
          </div>
          <span class="pill">config.yaml</span>
        </div>
        <textarea
          id="configText"
          class="editor"
          spellcheck="false"
        >{html.escape(config_text)}</textarea>
        <div class="panel-actions">
          <button onclick="validateConfig()">Validate</button>
          <button class="primary" onclick="saveConfig()">Save config</button>
          <span id="configStatus" class="status"></span>
        </div>
      </div>
      <div class="panel">
        <div class="panel-head">
          <div>
            <h2>TMDB API Access</h2>
            <p>Use the names shown on the TMDB API settings page.</p>
          </div>
          <span class="pill">local secrets</span>
        </div>
        <div class="field">
          <label for="tmdbBearer">API 读访问令牌 / Read Access Token</label>
          <input
            id="tmdbBearer"
            type="password"
            autocomplete="off"
            placeholder="Paste the long JWT token starting with eyJ..."
          >
          <small>Recommended. Sent as Authorization: Bearer &lt;token&gt;.</small>
        </div>
        <div class="field">
          <label for="tmdbApiKey">API 密钥 / API Key</label>
          <input
            id="tmdbApiKey"
            type="password"
            autocomplete="off"
            placeholder="Paste the short TMDB v3 API key"
          >
          <small>Fallback only. Sent as the v3 api_key query parameter.</small>
        </div>
        <div class="panel-actions">
          <button class="primary" onclick="saveSecrets()">Save secrets</button>
          <span id="secretStatus" class="status"></span>
        </div>
      </div>
    </section>
"""
    return _render_page("config", body)


def _render_page(active_page: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>media-agent</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    body {{ margin: 0; background: #f6f7f9; color: #1f2933; }}
    header {{ background: #ffffff; border-bottom: 1px solid #d9dee7; }}
    .header-inner {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 18px 24px 0;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 22px; }}
    h2 {{ font-size: 16px; margin: 0; }}
    .toolbar {{ display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }}
    .toolbar.inline {{ margin-top: 0; justify-content: flex-end; }}
    .page-head {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .page-head h2 {{ font-size: 20px; }}
    .page-head p {{
      margin: 6px 0 0;
      color: #667085;
      font-size: 13px;
    }}
    nav {{
      display: flex;
      gap: 4px;
      margin-top: 16px;
      overflow-x: auto;
    }}
    .nav-item {{
      display: inline-flex;
      align-items: center;
      border: 1px solid transparent;
      border-bottom: 0;
      border-radius: 7px 7px 0 0;
      color: #475467;
      font-size: 14px;
      padding: 9px 12px;
      text-decoration: none;
      white-space: nowrap;
    }}
    .nav-item:hover {{ background: #f6f7f9; }}
    .nav-item.active {{
      background: #f6f7f9;
      border-color: #d9dee7;
      color: #111827;
      font-weight: 600;
    }}
    button {{
      border: 1px solid #9aa6b2;
      background: #ffffff;
      border-radius: 6px;
      padding: 8px 12px;
      cursor: pointer;
    }}
    button.primary {{ background: #115e59; color: #ffffff; border-color: #115e59; }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
    }}
    .stat {{ background: #ffffff; border: 1px solid #d9dee7; border-radius: 8px; padding: 14px; }}
    .stat strong {{ display: block; font-size: 24px; margin-top: 4px; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      border: 1px solid #d9dee7;
    }}
    th, td {{
      text-align: left;
      padding: 9px 10px;
      border-bottom: 1px solid #edf0f4;
      font-size: 13px;
      vertical-align: top;
    }}
    th {{ background: #eef2f6; color: #344054; }}
    code {{ word-break: break-all; }}
    .empty {{
      color: #667085;
      background: #ffffff;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 14px;
    }}
    textarea {{
      width: 100%;
      min-height: 260px;
      box-sizing: border-box;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 13px;
      border: 1px solid #cbd5df;
      border-radius: 8px;
      padding: 12px;
    }}
    .form-row {{ display: flex; gap: 10px; margin: 8px 0; flex-wrap: wrap; }}
    input {{
      min-width: 260px;
      flex: 1;
      border: 1px solid #cbd5df;
      border-radius: 6px;
      padding: 8px 10px;
    }}
    .section-heading {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 28px 0 12px;
    }}
    .config-grid {{
      display: grid;
      grid-template-columns: minmax(0, 1.7fr) minmax(280px, 0.8fr);
      gap: 16px;
      align-items: start;
    }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 16px;
    }}
    .panel-head {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .panel-head p {{
      margin: 4px 0 0;
      color: #667085;
      font-size: 13px;
    }}
    .pill {{
      border: 1px solid #cbd5df;
      border-radius: 999px;
      color: #475467;
      font-size: 12px;
      padding: 4px 8px;
      white-space: nowrap;
    }}
    .editor {{
      min-height: 420px;
      resize: vertical;
      line-height: 1.45;
      tab-size: 2;
    }}
    .panel-actions {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-top: 12px;
      flex-wrap: wrap;
    }}
    .status {{
      color: #475467;
      font-size: 13px;
      min-height: 20px;
    }}
    .status.error {{ color: #b42318; }}
    .status.ok {{ color: #027a48; }}
    .field {{ margin-bottom: 12px; }}
    .field label {{
      display: block;
      color: #344054;
      font-size: 13px;
      font-weight: 600;
      margin-bottom: 6px;
    }}
    .field input {{
      width: 100%;
      min-width: 0;
      box-sizing: border-box;
    }}
    .field small {{
      display: block;
      color: #667085;
      font-size: 12px;
      margin-top: 5px;
    }}
    @media (max-width: 860px) {{
      main {{ padding: 16px; }}
      .header-inner {{ padding: 16px 16px 0; }}
      .page-head {{ display: block; }}
      .toolbar.inline {{ justify-content: flex-start; margin-top: 14px; }}
      .config-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="header-inner">
      <h1>media-agent</h1>
      <nav aria-label="Primary">
        <a class="nav-item {_active_class(active_page, "status")}" href="/status">Runtime Status</a>
        <a class="nav-item {_active_class(active_page, "config")}" href="/config">Configuration</a>
      </nav>
    </div>
  </header>
  <main>
{body}
  </main>
  <script>
    async function runImport(execute) {{
      const path = execute ? "/api/import-run-once?execute=true" : "/api/import-run-once";
      await fetch(path, {{ method: "POST" }});
      location.reload();
    }}
    function setStatus(id, message, ok) {{
      const node = document.getElementById(id);
      node.textContent = message;
      node.className = ok ? "status ok" : "status error";
    }}
    async function readJson(response) {{
      const payload = await response.json();
      if (!response.ok) {{
        throw new Error(payload.error || "Request failed");
      }}
      return payload;
    }}
    function formatConfigSummary(summary) {{
      const mode = summary.dry_run_default ? "dry-run default" : "execute default";
      return `${{summary.enabled_profiles}}/${{summary.profiles}} profiles enabled, ${{mode}}`;
    }}
    async function validateConfig() {{
      try {{
        const response = await fetch("/api/config/validate", {{
          method: "POST",
          headers: {{ "Content-Type": "application/x-yaml" }},
          body: document.getElementById("configText").value
        }});
        const payload = await readJson(response);
        setStatus("configStatus", `Valid: ${{formatConfigSummary(payload.summary)}}`, true);
      }} catch (error) {{
        setStatus("configStatus", error.message, false);
      }}
    }}
    async function saveConfig() {{
      try {{
        const response = await fetch("/api/config", {{
          method: "POST",
          headers: {{ "Content-Type": "application/x-yaml" }},
          body: document.getElementById("configText").value
        }});
        const payload = await readJson(response);
        setStatus("configStatus", `Saved: ${{formatConfigSummary(payload.summary)}}`, true);
      }} catch (error) {{
        setStatus("configStatus", error.message, false);
      }}
    }}
    async function saveSecrets() {{
      try {{
        const response = await fetch("/api/secrets", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{
            api_key: document.getElementById("tmdbApiKey").value,
            bearer_token: document.getElementById("tmdbBearer").value
          }})
        }});
        const payload = await readJson(response);
        document.getElementById("tmdbApiKey").value = "";
        document.getElementById("tmdbBearer").value = "";
        const labels = {{
          api_key: "API 密钥 / API Key",
          bearer_token: "API 读访问令牌 / Read Access Token"
        }};
        const names = payload.written.length
          ? payload.written.map((name) => labels[name] || name).join(", ")
          : "no credential fields";
        setStatus("secretStatus", `Saved: ${{names}}`, true);
      }} catch (error) {{
        setStatus("secretStatus", error.message, false);
      }}
    }}
  </script>
</body>
</html>"""


def _active_class(active_page: str, page: str) -> str:
    return "active" if active_page == page else ""


def run_web_server(
    *,
    config_path: Path,
    state_dir: Path,
    host: str,
    port: int,
    once: bool = False,
) -> ThreadingHTTPServer:
    handler = _make_handler(config_path=config_path, state_dir=state_dir)
    server = ThreadingHTTPServer((host, port), handler)
    if once:
        server.timeout = 0.1
    return server


def _make_handler(*, config_path: Path, state_dir: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/" or self.path == "/status" or self.path.startswith("/status?"):
                self._send_html(render_dashboard(build_status(state_dir)))
                return
            if self.path == "/config" or self.path.startswith("/config?"):
                self._send_html(render_config_page(config_text=_read_config_text(config_path)))
                return
            if self.path == "/api/status":
                self._send_json(build_status(state_dir))
                return
            if self.path == "/api/config":
                self._send_text(_read_config_text(config_path), content_type="application/x-yaml")
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path == "/api/config":
                self._save_config()
                return
            if self.path == "/api/config/validate":
                self._validate_config()
                return
            if self.path == "/api/secrets":
                self._save_secrets()
                return
            if not self.path.startswith("/api/import-run-once"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            execute = "execute=true" in self.path
            config = parse_config(load_config(config_path))
            summary = run_import_once(config, state_dir=state_dir, execute=execute)
            self._send_json(summary_to_dict(summary))

        def log_message(self, format: str, *args) -> None:
            return

        def _send_json(
            self,
            payload: dict[str, Any],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html_body: str) -> None:
            self._send_text(html_body, content_type="text/html; charset=utf-8")

        def _send_text(self, text: str, *, content_type: str) -> None:
            body = text.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _save_config(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            try:
                summary = _validate_config_text(body)
            except (ConfigError, yaml.YAMLError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(body, encoding="utf-8")
            self._send_json({"ok": True, "summary": summary})

        def _validate_config(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            try:
                summary = _validate_config_text(body)
            except (ConfigError, yaml.YAMLError) as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._send_json({"ok": True, "summary": summary})

        def _save_secrets(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            except json.JSONDecodeError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            config = parse_config(load_config(config_path))
            written: list[str] = []
            if payload.get("api_key"):
                _write_secret_ref(config.tmdb_api_key_ref, str(payload["api_key"]))
                written.append("api_key")
            if payload.get("bearer_token") and config.tmdb_bearer_token_ref:
                _write_secret_ref(config.tmdb_bearer_token_ref, str(payload["bearer_token"]))
                written.append("bearer_token")
            self._send_json({"ok": True, "written": written})

    return Handler


def _read_config_text(config_path: Path) -> str:
    if not config_path.exists():
        return ""
    return config_path.read_text(encoding="utf-8")


def _validate_config_text(config_text: str) -> dict[str, object]:
    loaded = yaml.safe_load(config_text) or {}
    if not isinstance(loaded, dict):
        raise ConfigError("config root must be a mapping")
    summary = validate_config(loaded)
    return {
        "profiles": summary.profile_count,
        "enabled_profiles": summary.enabled_profile_count,
        "dry_run_default": summary.dry_run_default,
    }


def _write_secret_ref(path_ref: str, value: str) -> None:
    path = Path(path_ref)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _table_or_empty(rows: str, empty_text: str, kind: str) -> str:
    if not rows:
        return f'<div class="empty">{html.escape(empty_text)}</div>'
    if kind == "review":
        header = "<tr><th>Title</th><th>Type</th><th>Reason</th><th>Source</th></tr>"
    else:
        header = (
            "<tr><th>Status</th><th>Type</th><th>Metadata</th><th>Source</th>"
            "<th>Target</th></tr>"
        )
    return f"<table><thead>{header}</thead><tbody>{rows}</tbody></table>"


def _render_review_row(row: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(row['title']))}</td>"
        f"<td>{html.escape(str(row['media_type']))}</td>"
        f"<td>{html.escape(str(row['reason']))}</td>"
        f"<td><code>{html.escape(str(row['source_path']))}</code></td>"
        "</tr>"
    )


def _render_action_row(row: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(row['status']))}</td>"
        f"<td>{html.escape(str(row['media_type']))}</td>"
        f"<td>{html.escape(str(row['metadata_id']))}</td>"
        f"<td><code>{html.escape(str(row['source_path']))}</code></td>"
        f"<td><code>{html.escape(str(row['target_path']))}</code></td>"
        "</tr>"
    )
