"""Tests de la CLI du Control Plane."""

from __future__ import annotations

import json

from scc_control_plane.cli import main


def test_cli_health(capsys):
    rc = main(["health"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["overall"] == "ok"


def test_cli_diagnostics(capsys):
    rc = main(["diagnostics"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["ok"] is True


def test_cli_alerts(capsys):
    rc = main(["alerts"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert "by_severity" in out


def test_cli_dashboard(capsys):
    rc = main(["dashboard"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["dashboard"] == "SCC Control Plane"


def test_cli_snapshot(capsys):
    rc = main(["snapshot"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert out["health"]["overall"] == "ok"
