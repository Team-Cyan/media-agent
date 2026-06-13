from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


def test_unraid_template_has_required_runtime_wiring() -> None:
    template = Path("deploy/unraid/media-agent.xml")
    root = ET.parse(template).getroot()

    values = {child.tag: child.text or "" for child in root}
    configs = {item.attrib["Target"]: item for item in root.findall("Config")}

    assert values["Name"] == "media-agent"
    assert values["Repository"] == "ghcr.io/team-cyan/media-agent:latest"
    assert values["WebUI"] == "http://[IP]:[PORT:8775]"
    assert "media-agent healthcheck" in values["ExtraParams"]
    assert configs["/workspace"].attrib["Default"] == "/mnt/user/appdata/media-agent"
    assert configs["/downloads"].attrib["Default"] == "/mnt/user/downloads"
    assert configs["/media"].attrib["Default"] == "/mnt/user/media"
    assert configs["MEDIA_AGENT_MODE"].text == "import-schedule"
    assert configs["MEDIA_AGENT_WEB_ENABLED"].text == "true"
    assert configs["MEDIA_AGENT_CONFIG"].text == "/workspace/runtime/config/config.yaml"
    assert configs["MEDIA_AGENT_STATE_DIR"].text == "/workspace/runtime/.media-agent"
    assert configs["MEDIA_AGENT_HEARTBEAT_FILE"].text.endswith("media-agent-heartbeat.json")
    assert configs["8775"].attrib["Mode"] == "tcp"
    assert values["Icon"].endswith("docs/assets/media-agent-icon.svg")


def test_dockerignore_excludes_local_state_and_docs() -> None:
    dockerignore = Path(".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "local" in dockerignore
    assert ".media-agent" in dockerignore
    assert "docs" in dockerignore
    assert "tests" in dockerignore
