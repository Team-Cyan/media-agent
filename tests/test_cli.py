from __future__ import annotations

import json

from media_agent.cli import main


def test_config_check_outputs_summary(capsys) -> None:
    exit_code = main(["config-check", "--config", "config/example.yaml"])

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["ok"] is True
    assert output["profiles"] == 3
    assert output["dry_run_default"] is True
