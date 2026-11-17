import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_web_settings import _request_json, _running_server, _write_minimal_config

from media_agent.web.schedules import preview_schedule


def test_preview_two_dates_timezone_and_disabled():
    now = datetime(2026, 11, 17, 0, tzinfo=UTC).timestamp()
    assert preview_schedule({"cron": "0 3 * * *", "timezone": "Asia/Shanghai"}, now=now)[
        "next_runs"
    ] == ["2026-11-18T03:00:00+08:00", "2026-11-19T03:00:00+08:00"]
    for expression in ["-", "", "not cron", "0 0 31 2 *", "0 0\n* * *"]:
        result = preview_schedule({"cron": expression}, now=now)
        assert result["enabled"] is False and result["next_runs"] == []
    with pytest.raises(ValueError, match="timezone"):
        preview_schedule({"cron": "* * * * *", "timezone": "Mars/Local"})


def test_preview_endpoint_does_not_modify_config(tmp_path):
    config = _write_minimal_config(tmp_path)
    before = config.read_bytes()
    with _running_server(config) as url:
        result = _request_json(
            url,
            "POST",
            "/api/schedules/preview",
            body={"kind": "media", "cron": "H 3 * * *", "timezone": "Asia/Shanghai"},
        )
    assert len(result["next_runs"]) == 2
    assert config.read_bytes() == before


def test_cron_form_preserves_untouched_legacy_fields_and_explicit_disable():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for form behavior tests")
    source = Path("src/media_agent/web/static/app.js").read_text()

    def piece(start, end):
        return source[source.index(start) : source.index(end)]

    script = "\n".join(
        [
            "const state = {configSections: {scheduler: {cron: null, intent_search_cron: null}}};",
            piece("function readSettingsPanelData(", "function readSearchTagScoreData("),
            piece("function coerceSettingValue(", "function getSettingValue("),
            piece("function setSettingValue(", "function parseMapValue("),
        ]
    )
    script += """
const fields = [
 {value:'',dataset:{settingField:'cron',settingType:'cron',originalNull:'true'}},
 {value:'-',dataset:{settingField:'intent_search_cron',settingType:'cron',originalNull:'false'}}
];
console.log(JSON.stringify(readSettingsPanelData({querySelectorAll:()=>fields},'scheduler')));
"""
    result = subprocess.run(
        [node, "-"], input=script, text=True, capture_output=True, check=True, timeout=10
    )
    assert json.loads(result.stdout) == {"cron": None, "intent_search_cron": "-"}


def test_five_schedule_preview_kinds_and_background_duration():
    from media_agent.cron_schedule import next_cron_slots
    from media_agent.web.schedules import HASH_IDS

    now = datetime(2026, 11, 17, 0, tzinfo=UTC).timestamp()
    assert set(HASH_IDS) == {"scheduler", "maintenance", "intent", "media", "background"}
    for kind, hash_id in HASH_IDS.items():
        result = preview_schedule(
            {"kind": kind, "cron": "H * * * *", "timezone": "UTC", "window_minutes": 45},
            now=now,
        )
        stamps = [datetime.fromisoformat(value).timestamp() for value in result["next_runs"]]
        assert stamps == next_cron_slots("H * * * *", "UTC", now, hash_id=hash_id)
        if kind == "background":
            assert result["window_minutes"] == 45
            assert [
                datetime.fromisoformat(value).timestamp() for value in result["window_ends"]
            ] == [stamp + 45 * 60 for stamp in stamps]
    with pytest.raises(ValueError, match="window_minutes"):
        preview_schedule({"kind": "background", "cron": "-", "window_minutes": True})


def test_background_and_maintenance_config_roundtrip(tmp_path):
    from media_agent.config import load_config
    from media_agent.media_import.config import MediaImportConfig

    config = _write_minimal_config(tmp_path)
    with _running_server(config) as url:
        current = _request_json(url, "GET", "/api/config")
        scheduler = current["sections"]["scheduler"]
        scheduler.update(cron="-", maintenance_cron="0 4 * * 0", intent_search_cron="0 6 * * *")
        saved = _request_json(
            url,
            "POST",
            "/api/config/sections",
            {
                "section": "scheduler",
                "data": scheduler,
                "revision": current["revision"],
            },
        )
        media = {
            "enabled": False,
            "scan_schedule": {"cron": "-", "timezone": "UTC"},
            "background_schedule": {
                "cron": "0 3 * * *",
                "timezone": "Asia/Shanghai",
                "window_minutes": 90,
            },
        }
        _request_json(
            url,
            "POST",
            "/api/config/sections",
            {
                "section": "media_import",
                "data": media,
                "revision": saved["revision"],
            },
        )
    loaded = load_config(config)
    assert loaded.scheduler.cron == "-"
    assert loaded.scheduler.maintenance_cron == "0 4 * * 0"
    assert loaded.scheduler.intent_search_cron == "0 6 * * *"
    assert (
        MediaImportConfig.model_validate(loaded._media_document).background_schedule.window_minutes
        == 90
    )
