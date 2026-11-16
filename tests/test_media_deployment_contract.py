"""Static deployment contracts; actual mounts and image require runtime acceptance."""

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_compose_unified_app_has_bounded_resources_and_one_media_mount():
    services = yaml.safe_load((ROOT / "deploy/docker-compose.example.yml").read_text())["services"]
    assert set(services) == {"media-agent"}
    app = services["media-agent"]
    assert app["environment"]["SEED_AGENT_MODE"] == "app"
    assert app["restart"] == "on-failure:5"
    assert all(app.get(key) for key in ["cpus", "mem_limit", "pids_limit"])
    assert app["read_only"] is True
    assert int(app["stop_grace_period"].removesuffix("s")) > 15
    mounts = app["volumes"]
    assert [m for m in mounts if ":/media" in m] == [
        "${MEDIA_PARENT_DIR:?Set the common source and library parent}:/media:rw"
    ]
    for path in [
        "../config:/app/config",
        "../local:/app/local",
        "../.seed-agent:/app/.seed-agent",
        "../.media-import:/app/.media-import",
        "../state:/state",
    ]:
        assert path in mounts
    assert all("docker.sock" not in m for m in mounts)
    assert app["healthcheck"]["test"] == ["CMD", "/app/docker/entrypoint.sh", "app-healthcheck"]


def test_unraid_templates_match_and_preserve_upgrade_root():
    new = ROOT / "deploy/unraid/media-agent.xml"
    assert new.read_text() == (ROOT / "deploy/unraid/seed-agent.xml").read_text()
    root = ET.parse(new).getroot()
    assert root.findtext("Privileged") == "false"
    extra = root.findtext("ExtraParams")
    for argument in [
        "--restart=on-failure:5",
        "--cpus=1.0",
        "--memory=1g",
        "--pids-limit=128",
        "--read-only",
        "--stop-timeout=45",
        "app-healthcheck",
    ]:
        assert argument in extra
    configs = {c.attrib["Target"]: c for c in root.findall("Config")}
    assert configs["SEED_AGENT_MODE"].text == "app"
    assert configs["/workspace"].text == "/mnt/user/appdata/seed-agent"
    mounts = {k: c.attrib["Mode"] for k, c in configs.items() if c.attrib["Type"] == "Path"}
    assert mounts["/media"] == "rw"
    assert not any(k.startswith("/media/") or "docker.sock" in k for k in mounts)
    assert "never run alongside" in ET.parse(
        ROOT / "deploy/unraid/media-worker.xml"
    ).getroot().findtext("Overview")


def test_environment_examples_and_guidance_cover_upgrade_safety():
    env = (ROOT / "deploy/media-agent.env.example").read_text()
    assert env == (ROOT / "deploy/seed-agent.env.example").read_text()
    assert "SEED_AGENT_IMAGE_DIGEST=" in env and "MEDIA_PARENT_DIR=" in env
    for name in ["docker-compose-user-guide.md", "unraid-dockerman.md"]:
        text = (ROOT / "docs/operations" / name).read_text()
        for required in ["media-state-init", "does not replay scans", "EXDEV", "credentials"]:
            assert required in text
