from __future__ import annotations

import html
import json
import sqlite3
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from media_agent.config import load_config, parse_config
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
    header {{ background: #ffffff; border-bottom: 1px solid #d9dee7; padding: 18px 24px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    h1 {{ margin: 0; font-size: 22px; }}
    h2 {{ font-size: 16px; margin: 28px 0 12px; }}
    .toolbar {{ display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }}
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
  </style>
</head>
<body>
  <header>
    <h1>media-agent</h1>
    <div class="toolbar">
      <button class="primary" onclick="runImport(false)">Run dry scan</button>
      <button onclick="runImport(true)">Run execute</button>
      <button onclick="location.reload()">Refresh</button>
    </div>
  </header>
  <main>
    <section class="stats">
      <div class="stat">Planned<strong>{counts["planned"]}</strong></div>
      <div class="stat">Linked<strong>{counts["linked"]}</strong></div>
      <div class="stat">Failed<strong>{counts["failed"]}</strong></div>
      <div class="stat">Pending Review<strong>{counts["pending_review"]}</strong></div>
    </section>
    <h2>Pending Review</h2>
    {_table_or_empty(review_rows, "No pending review items.", "review")}
    <h2>Recent Actions</h2>
    {_table_or_empty(action_rows, "No import actions yet.", "actions")}
  </main>
  <script>
    async function runImport(execute) {{
      const path = execute ? "/api/import-run-once?execute=true" : "/api/import-run-once";
      await fetch(path, {{ method: "POST" }});
      location.reload();
    }}
  </script>
</body>
</html>"""


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
            if self.path == "/" or self.path.startswith("/?"):
                self._send_html(render_dashboard(build_status(state_dir)))
                return
            if self.path == "/api/status":
                self._send_json(build_status(state_dir))
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self.path.startswith("/api/import-run-once"):
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            execute = "execute=true" in self.path
            config = parse_config(load_config(config_path))
            summary = run_import_once(config, state_dir=state_dir, execute=execute)
            self._send_json(summary_to_dict(summary))

        def log_message(self, format: str, *args) -> None:
            return

        def _send_json(self, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html_body: str) -> None:
            body = html_body.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


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
